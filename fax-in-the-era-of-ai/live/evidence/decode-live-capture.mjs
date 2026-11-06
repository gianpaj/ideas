/** Independent replay of a captured live stereo WAV through the actual blind
 * receiver, with no expected protocol payloads/phase positions/timeline inputs.
 * Writes only packet hashes/types/times, never nonce/key/raw packet fields.
 */
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {Decoder, PCM_BYTES, RATE} from '../src/signal.mjs';
import {NAMES} from '../src/protocol.mjs';
const path = process.argv[2];
if (!path) throw Error('usage: node evidence/decode-live-capture.mjs capture.wav');
const wav = readFileSync(path);
if (wav.toString('ascii', 0, 4) !== 'RIFF' || wav.toString('ascii', 8, 12) !== 'WAVE') throw Error('not RIFF WAV');
let channels, rate, bits, pcm;
for (let i = 12; i + 8 <= wav.length;) {
  const name = wav.toString('ascii', i, i + 4), length = wav.readUInt32LE(i + 4);
  if (name === 'fmt ') {
    if (wav.readUInt16LE(i + 8) !== 1) throw Error('requires integer PCM');
    channels = wav.readUInt16LE(i + 10); rate = wav.readUInt32LE(i + 12); bits = wav.readUInt16LE(i + 22);
  } else if (name === 'data') pcm = wav.subarray(i + 8, i + 8 + length);
  i += 8 + length + (length % 2);
}
if (channels !== 2 || rate !== RATE || bits !== 16 || !pcm) throw Error('requires stereo8k16bit PCM');
const results = [];
for (let channel = 0; channel < channels; channel++) {
  const decoder = new Decoder(), frames = [];
  for (let first = 0; first < pcm.length / 4; first += 160) {
    const chunk = Buffer.alloc(PCM_BYTES);
    for (let i = 0; i < 160 && (first + i) * 4 + channel * 2 < pcm.length; i++) chunk.writeInt16LE(pcm.readInt16LE((first + i) * 4 + channel * 2), i * 2);
    frames.push(...decoder.feed(chunk));
  }
  for (let i = 0; i < 10; i++) frames.push(...decoder.feed(Buffer.alloc(PCM_BYTES)));
  for (const frame of frames) results.push({channel: channel === 0 ? 'initiator-to-responder' : 'responder-to-initiator', type: NAMES[frame.payload[0]] || 'unknown',
    payloadBytes: frame.payload.length, startSeconds: frame.startSample / RATE, endSeconds: frame.endSample / RATE,
    packetSha256: createHash('sha256').update(frame.payload).digest('hex'), clockHypothesisPeriodPpm: frame.clockHypothesisPpm});
}
console.log(JSON.stringify({artifactSha256: createHash('sha256').update(wav).digest('hex'), durationSeconds: pcm.length / 4 / RATE,
  note: 'Blind CRC-confirmed replay from actual live link-delivery recording; MAC verified separately by live endpoint results. No key or expected payload input.',
  frames: results.sort((a, b) => a.startSeconds - b.startSeconds)}, null, 2));
