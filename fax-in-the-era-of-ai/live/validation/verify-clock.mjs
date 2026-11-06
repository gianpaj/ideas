// Independent waveform measurement: the injected oscillator must affect
// carrier frequency AND symbol timing, with positive ppm meaning faster clock.
import assert from 'node:assert/strict';
import {modulate, RATE, SPACE} from '../src/signal.mjs';

function lastActive(pcm) {
  for (let i = pcm.length / 2 - 1; i >= 0; i--)
    if (pcm.readInt16LE(i * 2) !== 0) return i;
  throw Error('empty waveform');
}

function estimateCarrier(pcm) {
  // Middle of a long all-zero payload, away from header, CRC and edge ramps.
  const start = 6000, count = 8000;
  let best = {hz: 0, power: -Infinity};
  for (let tick = -120; tick <= 120; tick++) {
    const hz = SPACE + tick * .05;
    let re = 0, im = 0;
    for (let i = 0; i < count; i++) {
      const x = pcm.readInt16LE((start + i) * 2) / 32768;
      const phase = 2 * Math.PI * hz * i / RATE;
      re += x * Math.cos(phase);
      im += x * Math.sin(phase);
    }
    const power = re * re + im * im;
    if (power > best.power) best = {hz, power};
  }
  return best.hz;
}

const payload = Buffer.alloc(100);
const referenceEnd = lastActive(modulate(payload));
const measurements = [];
for (const ppm of [-1000, 0, 1000]) {
  const pcm = modulate(payload, {samplePpm: ppm});
  const end = lastActive(pcm);
  const carrierHz = estimateCarrier(pcm);
  const expectedHz = SPACE * (1 + ppm / 1e6);
  const durationDerivedPpm = (referenceEnd / end - 1) * 1e6;
  measurements.push({injectedPpm: ppm, measuredCarrierHz: carrierHz,
                     expectedCarrierHz: expectedHz, durationDerivedPpm,
                     finalNonzeroSample: end});
  assert.ok(Math.abs(carrierHz - expectedHz) <= .10,
            `oscillator ${ppm}ppm: measured carrier ${carrierHz}, expected ${expectedHz}`);
  assert.ok(Math.abs(durationDerivedPpm - ppm) < 80,
            `oscillator ${ppm}ppm: duration implies ${durationDerivedPpm}ppm`);
}
console.log(JSON.stringify({status: 'passed', method: 'waveform spectral scan and nonzero-burst duration; no decoder timing oracle',
                          measurements}, null, 2));
