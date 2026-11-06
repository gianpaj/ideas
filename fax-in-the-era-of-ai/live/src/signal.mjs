/** Experimental AIP-FSK2 PCM physical layer; not V.21/T.30/CP compatible. */
export const RATE = 8000;
export const CHUNK = 160;
export const PCM_BYTES = 320;
export const PERIOD_MS = 20;
export const BAUD = 250;
export const SPACE = 2250;
export const MARK = 1250;
export const MAX_PAYLOAD = 192;
export const MAX_BUFFER = RATE * 8;
const PREAMBLE = Array.from({length: 48}, (_, i) => i % 2);
const SYNC = 0xddaa96e7;
const CLOCKS = [0];
for (let n = 250; n <= 3000; n += 250) CLOCKS.push(n, -n);

export function crc16(bytes) {
  let crc = 0xffff;
  for (const byte of bytes) {
    crc ^= byte << 8;
    for (let i = 0; i < 8; i++) crc = ((crc << 1) ^ ((crc & 0x8000) ? 0x1021 : 0)) & 0xffff;
  }
  return crc;
}

export function packet(payload) {
  if (!Buffer.isBuffer(payload) || payload.length < 1 || payload.length > MAX_PAYLOAD) throw Error('invalid physical payload length');
  const raw = Buffer.alloc(payload.length + 4);
  raw[0] = 2;
  raw[1] = payload.length;
  payload.copy(raw, 2);
  raw.writeUInt16BE(crc16(raw.subarray(0, -2)), raw.length - 2);
  return raw;
}

export function modulate(payload, {samplePpm = 0, phase = 0} = {}) {
  if (!Number.isFinite(samplePpm) || Math.abs(samplePpm) > 2500) throw Error('TX oscillator injection limited to +/-2500 ppm');
  const raw = packet(payload);
  const bits = [...PREAMBLE];
  for (let bit = 31; bit >= 0; bit--) bits.push((SYNC >>> bit) & 1);
  for (const byte of raw) for (let bit = 7; bit >= 0; bit--) bits.push((byte >>> bit) & 1);
  const ratio = 1 + samplePpm / 1e6;
  const sps = RATE / BAUD / ratio;
  const n = Math.ceil(bits.length * sps);
  // Release and packet-alignment padding are ordinary audio, not metadata.
  const pcm = Buffer.alloc((Math.ceil(n / CHUNK) + 3) * PCM_BYTES);
  for (let i = 0; i < n; i++) {
    const bit = bits[Math.min(Math.floor(i / sps), bits.length - 1)];
    phase += 2 * Math.PI * (bit ? MARK : SPACE) * ratio / RATE;
    let gain = .34;
    if (i < 32) gain *= Math.sin(i / 31 * Math.PI / 2) ** 2;
    if (n - 1 - i < 32) gain *= Math.sin((n - 1 - i) / 31 * Math.PI / 2) ** 2;
    pcm.writeInt16LE(Math.round(gain * Math.sin(phase) * 32767), i * 2);
  }
  return pcm;
}

/** Causal, bounded receiver; input is only PCM and public physical constants.
 * Blind search of 32 phase x 25 clock-rate hypotheses, re-acquired each frame.
 * Preamble/sync/version/length/CRC16 establish frame lock. Bounded 8-second
 * sample history and 160ms analysis cadence. Not an unrestricted timing PLL.
 */
export class Decoder {
  constructor() {
    this.samples = new Float64Array(MAX_BUFFER + CHUNK);
    this.length = 0;
    this.base = 0;
    this.received = 0;
    this.nextAnalysis = 3520;
    this.deliveredUntil = -100;
    this.maxBufferSamples = 0;
    this.crcRejections = 0;
    this.erasureRejections = 0;
    this.basis = [SPACE, MARK].map(f => Array.from({length: 32}, (_, i) => [Math.cos(2 * Math.PI * f * i / RATE), Math.sin(2 * Math.PI * f * i / RATE)]));
  }

  feed(pcm) {
    if (pcm.length !== PCM_BYTES) throw Error('input must be exactly 320 bytes mono s16le PCM');
    if (this.length + CHUNK > MAX_BUFFER) {
      const drop = this.length + CHUNK - MAX_BUFFER;
      this.samples.copyWithin(0, drop, this.length);
      this.length -= drop;
      this.base += drop;
    }
    for (let i = 0; i < CHUNK; i++) this.samples[this.length + i] = pcm.readInt16LE(i * 2) / 32768;
    this.length += CHUNK;
    this.received += CHUNK;
    this.maxBufferSamples = Math.max(this.maxBufferSamples, this.length);
    if (this.received < this.nextAnalysis) return [];
    this.nextAnalysis = this.received + 1280;
    const found = this.scan();
    if (found.length) {
      const end = Math.max(...found.map(f => f.endSample));
      const trim = Math.max(0, end - this.base - 64);
      this.samples.copyWithin(0, trim, this.length);
      this.length -= trim;
      this.base += trim;
      this.deliveredUntil = end;
    }
    return found;
  }

  scan() {
    const n = this.length - 31;
    if (n < 3500) return [];
    // Sliding complex correlations over one exact nominal 32-sample symbol.
    // Frequencies have integer cycles/window. Absolute phase cancels in |z|².
    const energy = this.basis.map(basis => {
      const values = new Float64Array(n);
      let re = 0, im = 0;
      for (let i = 0; i < this.length; i++) {
        const b = basis[i % 32];
        re += this.samples[i] * b[0];
        im += this.samples[i] * b[1];
        if (i >= 32) {
          const old = basis[(i - 32) % 32];
          re -= this.samples[i - 32] * old[0];
          im -= this.samples[i - 32] * old[1];
        }
        if (i >= 31) values[i - 31] = re * re + im * im;
      }
      return values;
    });
    const soft = new Float64Array(n);
    for (let i = 0; i < n; i++) soft[i] = energy[1][i] - energy[0][i];
    const found = [];
    for (const ppm of CLOCKS) {
      const step = 32 * (1 + ppm / 1e6);
      const count = Math.floor((n - 32) / step);
      if (count < 110) continue;
      const bits = new Uint8Array(count);
      for (let phase = 0; phase < 32; phase++) {
        let sync = 0;
        for (let i = 0; i < count; i++) {
          bits[i] = soft[Math.round(phase + i * step)] > 0 ? 1 : 0;
          sync = ((sync << 1) | bits[i]) >>> 0;
          if (sync !== SYNC || i < 79) continue;
          const at = i - 31;
          let errors = 0;
          for (let j = 0; j < 48; j++) errors += bits[at - 48 + j] !== PREAMBLE[j] ? 1 : 0;
          if (errors > 4) continue;
          const bodyStart = i + 1;
          if (bodyStart + 16 > count) continue;
          const readByte = index => {
            let byte = 0;
            for (let b = 0; b < 8; b++) byte = (byte << 1) | (soft[Math.round(phase + (index + b) * step)] > 0 ? 1 : 0);
            return byte;
          };
          const version = readByte(bodyStart), length = readByte(bodyStart + 8);
          if (version !== 2 || length < 1 || length > MAX_PAYLOAD) continue;
          const endBit = bodyStart + (length + 4) * 8;
          if (endBit >= count) continue;
          const start = this.base + Math.round(phase + (at - 48) * step);
          const end = this.base + Math.round(phase + endBit * step);
          if (end <= this.deliveredUntil + 64 || found.some(f => Math.abs(f.startSample - start) < 64)) continue;
          // A CRC can accidentally confirm the original bytes when low-energy
          // erased bits happen to be guessed correctly. Numerical residual
          // correlator signs are not signal evidence: reject any low-energy
          // body symbol relative to this candidate's observed peak.
          let peakPower = 0, minPower = Infinity;
          for (let b = bodyStart; b < endBit; b++) {
            const pos = Math.round(phase + b * step);
            const power = energy[0][pos] + energy[1][pos];
            peakPower = Math.max(peakPower, power);
            minPower = Math.min(minPower, power);
          }
          if (peakPower < .01 || minPower < Math.max(.01, .04 * peakPower)) { this.erasureRejections++; continue; }
          const raw = Buffer.alloc(length + 4);
          for (let b = 0; b < raw.length; b++) raw[b] = readByte(bodyStart + b * 8);
          if (crc16(raw.subarray(0, -2)) !== raw.readUInt16BE(raw.length - 2)) { this.crcRejections++; continue; }
          // Reject digital silence/numerical cancellation as FSK even before MAC.
          if (energy[0][Math.round(phase + at * step)] + energy[1][Math.round(phase + at * step)] < .01) continue;
          found.push({payload: raw.subarray(2, -2), startSample: start, endSample: end, clockHypothesisPpm: ppm});
        }
      }
      if (found.length) break;
    }
    return found.sort((a, b) => a.startSample - b.startSample);
  }
}
