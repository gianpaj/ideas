/** Adapter contract: send(Buffer320), PCM callback, close(). No protocol fields. */
import dgram from 'node:dgram';
import {randomBytes} from 'node:crypto';
import {performance} from 'node:perf_hooks';
import {PCM_BYTES, CHUNK} from './signal.mjs';

export const HEADER = 12;
const MAGIC = Buffer.from('APC2');
export function encodeDatagram(pcm, seq, sample) {
  const packet = Buffer.alloc(HEADER + PCM_BYTES);
  MAGIC.copy(packet);
  packet.writeUInt32BE(seq >>> 0, 4);
  packet.writeUInt32BE(sample >>> 0, 8);
  pcm.copy(packet, HEADER);
  return packet;
}
export function decodeDatagram(packet) {
  if (packet.length !== HEADER + PCM_BYTES || !packet.subarray(0, 4).equals(MAGIC)) return null;
  return {seq: packet.readUInt32BE(4), sample: packet.readUInt32BE(8), pcm: packet.subarray(HEADER)};
}
const distance = (a, b) => (a - b) | 0;
export function address(text) {
  const at = text.lastIndexOf(':');
  if (at < 1) throw Error('expected host:port (IPv4/hostname)');
  const host = text.slice(0, at), port = Number(text.slice(at + 1));
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw Error('invalid port');
  return {host, port};
}

export class UdpAudio {
  constructor({bind, peer, jitterMs = 100, redundancy = 2, onPcm, onError}) {
    if (![1, 2].includes(redundancy)) throw Error('media redundancy must be1or2');
    this.redundancy = redundancy;
    this.bind = bind;
    this.peer = peer;
    this.jitterMs = jitterMs;
    this.onPcm = onPcm;
    this.onError = onError;
    this.socket = dgram.createSocket('udp4');
    this.queue = new Map();
    this.seen = new Set();
    this.seq = randomBytes(4).readUInt32BE();
    this.sample = randomBytes(4).readUInt32BE();
    this.next = null;
    this.playAt = null;
    this.stats = {redundancy, sent: 0, sentDatagrams: 0, received: 0, receivedDatagrams: 0, duplicates: 0, lateDuplicates: 0, lost: 0, late: 0, invalid: 0, maxQueued: 0, maxSeen: 0, socketErrors: 0};
    this.closed = false;
  }
  async open() {
    this.socket.on('error', error => { this.stats.socketErrors++; this.onError?.(error); });
    this.socket.on('message', packet => {
      const message = decodeDatagram(packet);
      if (!message) { this.stats.invalid++; return; }
      this.stats.receivedDatagrams++;
      if (this.seen.has(message.seq)) {
        this.stats.duplicates++;
        if (this.next !== null && distance(message.seq, this.next) < 0) this.stats.lateDuplicates++;
        return;
      }
      if (this.next === null) {
        this.next = message.seq;
        this.playAt = performance.now() + this.jitterMs;
      }
      const ahead = distance(message.seq, this.next);
      if (ahead < 0) {
        if (performance.now() < this.playAt && ahead >= -127) this.next = message.seq;
        else { this.stats.late++; return; }
      }
      if (ahead > 127 || this.queue.size >= 128) { this.stats.invalid++; return; }
      this.queue.set(message.seq, Buffer.from(message.pcm));
      this.seen.add(message.seq);
      if (this.seen.size > 256) this.seen.delete(this.seen.values().next().value);
      this.stats.maxSeen = Math.max(this.stats.maxSeen, this.seen.size);
      this.stats.received++;
      this.stats.maxQueued = Math.max(this.stats.maxQueued, this.queue.size);
    });
    await new Promise((resolve, reject) => {
      this.socket.once('error', reject);
      this.socket.bind(this.bind.port, this.bind.host, () => {
        this.socket.connect(this.peer.port, this.peer.host, () => {
          this.socket.off('error', reject);
          resolve();
        });
      });
    });
    return this;
  }
  send(pcm) {
    if (this.closed || pcm.length !== PCM_BYTES) return;
    const packet = encodeDatagram(pcm, this.seq++, this.sample);
    for (let copy = 0; copy < this.redundancy; copy++) {
      this.socket.send(packet);
      this.stats.sentDatagrams++;
    }
    this.seq >>>= 0;
    this.sample = (this.sample + CHUNK) >>> 0;
    this.stats.sent++;
  }
  playout(now) {
    if (this.next === null || now < this.playAt) return;
    // One local20ms playout unit per tick. Bounded buffering, no remote wall time.
    const pcm = this.queue.get(this.next);
    this.queue.delete(this.next);
    this.next = (this.next + 1) >>> 0;
    this.playAt += 20;
    if (!pcm) this.stats.lost++;
    this.onPcm(pcm || Buffer.alloc(PCM_BYTES));
  }
  close() {
    if (this.closed) return;
    this.closed = true;
    this.queue.clear();
    this.seen.clear();
    try { this.socket.close(); } catch (error) {
      if (error.code !== 'ERR_SOCKET_DGRAM_NOT_RUNNING') throw error;
    }
  }
}

/** ADC clock simulation, independent of TX and OS wall clock.
 * Positive sample-clock ppm means a faster local ADC (shorter sample period).
 * Incoming nominal8k physical audio is sampled at t=n/(1+ppm/1e6).
 * Fractional cursor+interpolation persist across every20ms packet boundary.
 */
export class AdcClock {
  constructor(ppm = 0) {
    if (!Number.isFinite(ppm) || Math.abs(ppm) > 2500) throw Error('ADC ppm outside supported range');
    this.ratio = 1 / (1 + ppm / 1e6);
    this.input = [];
    this.cursor = 0;
    this.output = [];
  }
  feed(pcm) {
    if (this.ratio === 1) return [pcm];
    for (let i = 0; i < CHUNK; i++) this.input.push(pcm.readInt16LE(i * 2));
    while (this.cursor + 1 < this.input.length) {
      const low = Math.floor(this.cursor), fraction = this.cursor - low;
      this.output.push(Math.round(this.input[low] * (1 - fraction) + this.input[low + 1] * fraction));
      this.cursor += this.ratio;
    }
    const used = Math.floor(this.cursor);
    this.input.splice(0, used);
    this.cursor -= used;
    const chunks = [];
    while (this.output.length >= CHUNK) {
      const next = Buffer.alloc(PCM_BYTES), values = this.output.splice(0, CHUNK);
      for (let i = 0; i < CHUNK; i++) next.writeInt16LE(values[i], i * 2);
      chunks.push(next);
    }
    return chunks;
  }
}
