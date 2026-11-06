import {readFileSync, statSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {performance} from 'node:perf_hooks';
import {Worker} from 'node:worker_threads';
import {Session, NAMES} from './protocol.mjs';
import {modulate, PCM_BYTES, PERIOD_MS} from './signal.mjs';
import {UdpAudio, AdcClock, address} from './transport.mjs';
import {logger} from './log.mjs';

export async function runEndpoint(options) {
  const role = options.role;
  if (!['initiator', 'responder'].includes(role)) throw Error('--role must be initiator or responder');
  const keyPath = options.key;
  if (!keyPath) throw Error('--key required; provision the same private32byte key separately at both endpoints');
  const stat = statSync(keyPath);
  if (stat.mode & 0o077) throw Error('key file must not grant group/other permissions (chmod600)');
  const key = readFileSync(keyPath);
  if (key.length !== 32) throw Error('key must be exactly32raw bytes');
  const samplePpm = Number(options['sample-ppm'] ?? 0);
  const wallOffsetMs = Number(options['wall-offset-ms'] ?? 0);
  const timeoutMs = Number(options['timeout-ms'] ?? 90000);
  const retryMs = Number(options['retry-ms'] ?? 7000);
  const retryMax = Number(options.retries ?? 4);
  const jitterMs = Number(options['jitter-ms'] ?? 160);
  if (![samplePpm, wallOffsetMs, timeoutMs, retryMs, retryMax, jitterMs].every(Number.isFinite)
      || Math.abs(wallOffsetMs) > 7 * 86400000 || timeoutMs < 1000 || timeoutMs > 300000
      || retryMs < 1000 || retryMs > timeoutMs || retryMax < 0 || retryMax > 10 || jitterMs < 0 || jitterMs > 2000) throw Error('invalid timing limits');
  const bindAddress = address(options.bind ?? `127.0.0.1:${role === 'initiator' ? 31001 : 31002}`);
  const peerAddress = address(options.peer ?? '127.0.0.1:31000');
  const machine = new Session({role, key, data: Buffer.from(options.data ?? 'hello from a real audio link')});
  const adc = new AdcClock(samplePpm);
  const log = logger({role, file: options.log, wallOffsetMs});
  const worker = new Worker(new URL('./decoder-worker.mjs', import.meta.url));
  const start = performance.now();
  let stopped = false, tickTimer, retryAt = Infinity, retries = 0, totalRetries = 0;
  let lastIncomingActive = -Infinity, nextTick = start, startedHelloAt;
  let sending = null, txOffset = 0, txQueue = [], guardUntil = start + 200;
  let dspSent = 0, dspProcessed = 0;
  let decoderStats = {};
  const silence = Buffer.alloc(PCM_BYTES);
  let resolveDone;
  const done = new Promise(resolve => { resolveDone = resolve; });
  const transport = new UdpAudio({bind: bindAddress, peer: peerAddress, jitterMs,
    onError: error => {
      // ICMP port-unreachable can occur during independently started apps.
      if (error.code === 'ECONNREFUSED') {
        if (transport.stats.socketErrors === 1) log('transport-warning', {error: error.code});
      } else finish(false, 'transport-error', {error: error.code || 'socket'});
    },
    onPcm: pcm => {
      let power = 0;
      for (let i = 0; i < pcm.length; i += 2) power += (pcm.readInt16LE(i) / 32768) ** 2;
      if (Math.sqrt(power / 160) > .065) lastIncomingActive = performance.now();
      for (const chunk of adc.feed(pcm)) {
        if (++dspSent - dspProcessed > 128) { finish(false, 'decoder-backpressure'); return; }
        worker.postMessage({type: 'pcm', pcm: chunk});
      }
    }});

  function queue(raw, reason) {
    if (!raw || stopped) return;
    const fingerprint = createHash('sha256').update(raw).digest('hex');
    if ((sending && sending.fingerprint === fingerprint) || txQueue.some(item => item.fingerprint === fingerprint)) return;
    if (txQueue.length >= 4) { finish(false, 'tx-backpressure'); return; }
    txQueue.push({raw, fingerprint, reason});
    retryAt = Infinity;
  }
  async function finish(success, reason, extra = {}) {
    if (stopped) return;
    stopped = true;
    clearTimeout(tickTimer);
    process.off('SIGINT', cancel);
    process.off('SIGTERM', cancel);
    transport.close();
    await worker.terminate();
    log('result', {success, reason, state: machine.state, paired: machine.paired, receiptVerified: !!machine.receiptVerified,
      sessionFingerprint: machine.sessionFingerprint, operationCount: machine.operationCount, rejections: machine.rejections,
      retries, totalRetries, transport: transport.stats, decoder: decoderStats, ...extra});
    machine.close();
    txQueue = [];
    sending = null;
    resolveDone(success ? 0 : 2);
  }
  function cancel() { finish(false, 'cancelled'); }
  worker.on('error', () => finish(false, 'decoder-worker-error'));
  worker.on('message', message => {
    if (stopped) return;
    if (message.type === 'progress' || message.type === 'stats') {
      dspProcessed = message.chunks;
      decoderStats = {maxBufferSamples: message.maxBufferSamples, crcRejections: message.crcRejections, erasureRejections: message.erasureRejections};
      return;
    }
    if (message.type !== 'frame') return;
    const raw = Buffer.from(message.payload);
    log('audio-frame', {type: NAMES[raw[0]] || 'unknown', payloadBytes: raw.length,
      clockHypothesisPeriodPpm: message.clockHypothesisPpm, startSample: message.startSample, endSample: message.endSample});
    const result = machine.receive(raw);
    if (result.rejected) { log('rejected', {reason: result.rejected}); return; }
    log(result.duplicate ? 'duplicate' : 'transition', {received: result.received, state: machine.state, paired: machine.paired, sessionFingerprint: machine.sessionFingerprint});
    if (!result.duplicate) {
      retries = 0;
      retryAt = Infinity;
      // Do not transmit obsolete queued retries after a causally newer response.
      txQueue = [];
      if (role === 'initiator' && result.received === 'CHALLENGE') log('handshake-rtt', {roundTripMs: Math.round(performance.now() - startedHelloAt), note: 'local monotonic HELLO transmit-start to decoded CHALLENGE; includes both bursts, buffering and processing, not one-way latency'});
    }
    if (result.outbound) queue(result.outbound, result.duplicate ? 'cached-response' : 'received-audio');
    if (machine.completed && role === 'responder') finish(true, 'authenticated-data-and-close');
  });
  try {
    await transport.open();
  } catch (error) {
    await finish(false, 'transport-open', {error: error.code || 'socket'});
    return done;
  }
  process.on('SIGINT', cancel);
  process.on('SIGTERM', cancel);
  log('ready', {sampleClockPpm: samplePpm, wallOffsetMs, timeoutMs, retryMs, jitterMs,
    transport: 'UDP/8k-mono-s16le/20ms/PCM-only', profile: 'experimental-AIP-FSK2'});
  if (role === 'initiator') queue(machine.start(), 'initial');

  function tick() {
    if (stopped) return;
    const now = performance.now();
    if (now - start >= timeoutMs) { finish(false, 'session-expired'); return; }
    if (now - nextTick > 500) { finish(false, 'local-audio-scheduler-overrun'); return; }
    transport.playout(now);
    if (!sending && !txQueue.length && now >= retryAt && now - lastIncomingActive > 180) {
      if (retries >= retryMax || !machine.lastOutbound) { finish(false, 'retry-exhausted'); return; }
      retries++;
      totalRetries++;
      log('retry', {type: NAMES[machine.lastOutbound[0]], attempt: retries});
      queue(machine.lastOutbound, 'timeout-retry');
    }
    if (!sending && txQueue.length && now >= guardUntil && now - lastIncomingActive > 180) {
      const next = txQueue.shift();
      const pcm = modulate(next.raw, {samplePpm});
      sending = {...next, pcm};
      txOffset = 0;
      if (role === 'initiator' && next.raw[0] === 1 && startedHelloAt === undefined) startedHelloAt = now;
      log('tx-start', {type: NAMES[next.raw[0]], pcmSamples: pcm.length / 2, reason: next.reason});
    }
    let outgoing = silence;
    if (sending) {
      outgoing = sending.pcm.subarray(txOffset, txOffset + PCM_BYTES);
      txOffset += PCM_BYTES;
      if (txOffset >= sending.pcm.length) {
        log('tx-end', {type: NAMES[sending.raw[0]]});
        const closeSent = role === 'initiator' && machine.completed && sending.raw[0] === 7;
        sending = null;
        guardUntil = now + 180;
        retryAt = now + retryMs;
        transport.send(outgoing);
        if (closeSent) { finish(true, 'authenticated-receipt-verified'); return; }
        nextTick += PERIOD_MS;
        tickTimer = setTimeout(tick, Math.max(0, nextTick - performance.now()));
        return;
      }
    }
    transport.send(outgoing);
    nextTick += PERIOD_MS;
    tickTimer = setTimeout(tick, Math.max(0, nextTick - performance.now()));
  }
  tick();
  return done;
}
