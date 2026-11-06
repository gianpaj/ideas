/** PCM-only impairment relay. It neither imports nor interprets the protocol. */
import dgram from 'node:dgram';
import {performance} from 'node:perf_hooks';
import {writeFileSync} from 'node:fs';
import {lookup} from 'node:dns/promises';
import {randomBytes} from 'node:crypto';
import {address, decodeDatagram, encodeDatagram} from './transport.mjs';
import {logger} from './log.mjs';
import {PCM_BYTES, RATE, CHUNK} from './signal.mjs';

function wav(stereo) {
  const pcm = Buffer.alloc(stereo.length * 2), header = Buffer.alloc(44);
  for (let i = 0; i < stereo.length; i++) pcm.writeInt16LE(stereo[i], i * 2);
  header.write('RIFF'); header.writeUInt32LE(36 + pcm.length, 4); header.write('WAVEfmt ', 8);
  header.writeUInt32LE(16, 16); header.writeUInt16LE(1, 20); header.writeUInt16LE(2, 22);
  header.writeUInt32LE(RATE, 24); header.writeUInt32LE(RATE * 4, 28); header.writeUInt16LE(4, 32); header.writeUInt16LE(16, 34);
  header.write('data', 36); header.writeUInt32LE(pcm.length, 40);
  return Buffer.concat([header, pcm]);
}
function randomStream(seed) {
  let state = (seed >>> 0) || 0x9e3779b9;
  return () => { state ^= state << 13; state ^= state >>> 17; state ^= state << 5; return (state >>> 0) / 4294967296; };
}
/** Exactly-once physical processing for duplicate media packets. Sender input
 * reaches this local relay in sequence; delay/jitter/loss are applied AFTER
 * this cache. Stale evicted copies cannot advance the filter/echo clock again.
 */
export class UniqueMedia {
  constructor(process, capacity = 256) {
    if (!Number.isInteger(capacity) || capacity < 1 || capacity > 1024) throw Error('invalid media-cache capacity');
    this.process = process;
    this.capacity = capacity;
    this.entries = new Map();
    this.highest = null;
    this.maxEntries = 0;
  }
  accept(message) {
    const previous = this.entries.get(message.seq);
    if (previous) {
      if (previous.sample !== message.sample || !previous.source.equals(message.pcm)) return {invalid: true};
      return {entry: previous, duplicate: true};
    }
    if (this.highest !== null && ((message.seq - this.highest) | 0) <= 0) return {invalid: true};
    const entry = {sample: message.sample, source: Buffer.from(message.pcm), pcm: this.process(message.pcm), recorded: false};
    this.entries.set(message.seq, entry);
    this.highest = message.seq;
    if (this.entries.size > this.capacity) this.entries.delete(this.entries.keys().next().value);
    this.maxEntries = Math.max(this.maxEntries, this.entries.size);
    return {entry, duplicate: false};
  }
}
class Impairment {
  constructor({noiseDb, echo, random}) {
    this.random = random;
    this.noise = noiseDb === Infinity ? 0 : .24 * 10 ** (-noiseDb / 20);
    this.echo = echo;
    this.history = new Float64Array(400);
    this.cursor = 0;
    this.lowState = 0;
    this.highState = 0;
    this.previous = 0;
  }
  apply(pcm) {
    const out = Buffer.alloc(PCM_BYTES);
    for (let i = 0; i < CHUNK; i++) {
      const sample = pcm.readInt16LE(i * 2) / 32768;
      // Gentle causal high/lowpass coloration; NOT an exact telephone-band
      // filter or codec. The .9308 smoothing coefficient is deliberately mild.
      const hp = .7901 * (this.highState + sample - this.previous);
      this.previous = sample;
      this.highState = hp;
      this.lowState += .9308 * (hp - this.lowState);
      const delayed = this.history[this.cursor];
      this.history[this.cursor] = this.lowState;
      this.cursor = (this.cursor + 1) % 400;
      // Sum of12uniforms gives zero-mean approximately Gaussian variance1.
      let noise = -6;
      for (let j = 0; j < 12; j++) noise += this.random();
      const y = this.lowState + this.echo * delayed + this.noise * noise;
      out.writeInt16LE(Math.round(Math.max(-1, Math.min(1, y)) * 32767), i * 2);
    }
    return out;
  }
}
export async function runLink(options) {
  const bind = address(options.bind ?? '127.0.0.1:31000');
  const endpoints = {a: address(options.a ?? '127.0.0.1:31001'), b: address(options.b ?? '127.0.0.1:31002')};
  for (const endpoint of Object.values(endpoints)) endpoint.host = (await lookup(endpoint.host, {family: 4})).address;
  const number = (key, fallback) => Number(options[key] ?? fallback);
  const latency = {a: number('a-delay-ms', 0), b: number('b-delay-ms', 0)};
  const jitter = number('jitter-ms', 0), loss = number('loss', 0), noiseDb = number('noise-db', 24), echo = number('echo', .10);
  const maxMs = number('duration-ms', 120000);
  const seed = number('seed', randomBytes(4).readUInt32BE());
  if (!Number.isInteger(seed) || seed < 0 || seed > 0xffffffff) throw Error('--seed must be uint32');
  const randoms = {a: randomStream(seed ^ 0x91af3), b: randomStream(seed ^ 0xa23e1)};
  if ([...Object.values(latency), jitter, loss, echo, maxMs].some(v => !Number.isFinite(v))
      || Object.values(latency).some(v => v < 0 || v > 3000) || jitter < 0 || jitter > 2000
      || loss < 0 || loss > 1 || noiseDb < 0 || echo < 0 || echo > .5 || maxMs < 1000 || maxMs > 300000) throw Error('invalid link limits');
  const mute = options.mute ?? '';
  if (mute && !['a', 'b', 'both'].includes(mute)) throw Error('--mute a|b|both');
  const drop = {a: number('drop-a-burst', 0), b: number('drop-b-burst', 0)};
  const corrupt = options.corrupt ?? '';
  const log = logger({role: 'link', file: options.log});
  const channels = {a: new Impairment({noiseDb, echo, random: randomStream(seed ^ 0x1234)}), b: new Impairment({noiseDb, echo, random: randomStream(seed ^ 0x4567)})};
  const state = {a: {burst: 0, active: false, silence: 0}, b: {burst: 0, active: false, silence: 0}};
  const directionStats = () => ({received: 0, physicalProcessed: 0, duplicateDatagrams: 0, dropped: 0, delivered: 0, deliveredUnique: 0, bursts: 0, cacheMax: 0});
  const stats = {a: directionStats(), b: directionStats(), invalid: 0, pendingMax: 0, captureOverlaps: 0};
  const media = Object.fromEntries(['a', 'b'].map(side => [side, new UniqueMedia(pcm => {
    const s = state[side];
    let power = 0;
    for (let i = 0; i < PCM_BYTES; i += 2) power += pcm.readInt16LE(i) ** 2;
    const active = Math.sqrt(power / CHUNK) > 1000;
    if (active) {
      if (!s.active) { s.burst++; stats[side].bursts++; log('burst', {direction: side, ordinal: s.burst}); }
      s.active = true; s.silence = 0;
    } else if (++s.silence >= 5) s.active = false;
    const burstMuted = s.active && drop[side] === s.burst;
    // Stateful coloring/noise/50ms echo advance ONCE per unique physical20ms
    // sample block, even if all datagram copies are subsequently discarded.
    const muted = mute === 'both' || mute === side || burstMuted || corrupt === side || corrupt === 'both';
    return channels[side].apply(muted ? Buffer.alloc(PCM_BYTES) : pcm);
  })]));
  const socket = dgram.createSocket('udp4');
  const timers = new Set();
  // Bound recording to the configured maximum lifetime. Time is only LOCAL link
  // capture chronology; it never controls endpoint session state or decoding.
  const capture = options.capture ? new Int16Array(Math.ceil(maxMs / 1000 * RATE) * 2) : null;
  const occupied = options.capture ? [new Set(), new Set()] : null;
  let captureEnd = 0, stopped = false, endTimer;
  const start = performance.now();
  let resolveDone;
  const done = new Promise(resolve => { resolveDone = resolve; });
  const record = (pcm, side) => {
    if (!capture) return;
    const first = Math.round((performance.now() - start) * RATE / 1000);
    const channel = side === 'a' ? 0 : 1;
    const slot = Math.floor(first / CHUNK);
    if (occupied[channel].has(slot)) stats.captureOverlaps++;
    occupied[channel].add(slot);
    for (let i = 0; i < CHUNK; i++) {
      const index = (first + i) * 2 + channel;
      if (index >= capture.length) break;
      // Sum concurrent delivery fragments instead of silently overwriting them.
      capture[index] = Math.max(-32768, Math.min(32767, capture[index] + pcm.readInt16LE(i * 2)));
      captureEnd = Math.max(captureEnd, first + i + 1);
    }
  };
  async function stop() {
    if (stopped) return;
    stopped = true;
    for (const timer of timers) clearTimeout(timer);
    timers.clear();
    clearTimeout(endTimer);
    process.off('SIGINT', stop); process.off('SIGTERM', stop);
    socket.close();
    if (capture) writeFileSync(options.capture, wav(capture.subarray(0, captureEnd * 2)), {mode: 0o600});
    log('result', {stats, captureSamplesPerChannel: captureEnd, note: 'capture is first-delivered unique PCM only (media copies deduplicated), left a-to-b/right b-to-a; jitter can overlap delivery fragments; not a playout-corrected receiver recording'});
    resolveDone(0);
  }
  socket.on('message', (packet, info) => {
    if (stopped) return;
    const side = info.port === endpoints.a.port && info.address === endpoints.a.host ? 'a' : info.port === endpoints.b.port && info.address === endpoints.b.host ? 'b' : null;
    const message = decodeDatagram(packet);
    if (!side || !message) { stats.invalid++; return; }
    const peer = endpoints[side === 'a' ? 'b' : 'a'];
    stats[side].received++;
    const unique = media[side].accept(message);
    if (unique.invalid) { stats.invalid++; return; }
    if (unique.duplicate) stats[side].duplicateDatagrams++;
    else stats[side].physicalProcessed++;
    stats[side].cacheMax = media[side].maxEntries;
    if (randoms[side]() < loss) { stats[side].dropped++; return; }
    const {entry} = unique;
    const pcm = entry.pcm;
    if (timers.size >= 1024) { stats[side].dropped++; return; }
    const delay = Math.max(0, latency[side] + (randoms[side]() * 2 - 1) * jitter);
    const timer = setTimeout(() => {
      timers.delete(timer);
      if (stopped) return;
      const raw = encodeDatagram(pcm, message.seq, message.sample);
      socket.send(raw, peer.port, peer.host);
      stats[side].delivered++;
      if (!entry.recorded) {
        entry.recorded = true;
        stats[side].deliveredUnique++;
        record(pcm, side);
      }
    }, delay);
    timers.add(timer);
    stats.pendingMax = Math.max(stats.pendingMax, timers.size);
  });
  socket.on('error', error => { log('transport-error', {error: error.code || 'socket'}); stop(); });
  await new Promise((resolve, reject) => { socket.once('error', reject); socket.bind(bind.port, bind.host, resolve); });
  process.on('SIGINT', stop); process.on('SIGTERM', stop);
  endTimer = setTimeout(stop, maxMs);
  log('ready', {bind, endpoints, delayMs: latency, jitterMs: jitter, loss, noiseDb, echo, seed, mute, dropBursts: drop, maxMs});
  return done;
}
