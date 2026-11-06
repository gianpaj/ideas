import test from 'node:test';
import assert from 'node:assert/strict';
import {randomBytes} from 'node:crypto';
import {Decoder, modulate, crc16, MAX_BUFFER, PCM_BYTES} from '../src/signal.mjs';

function decode(pcm) {
  const decoder = new Decoder(), frames = [];
  for (let i = 0; i < pcm.length; i += PCM_BYTES) frames.push(...decoder.feed(pcm.subarray(i, i + PCM_BYTES)));
  for (let i = 0; i < 10; i++) frames.push(...decoder.feed(Buffer.alloc(PCM_BYTES)));
  return {frames, decoder};
}
test('CRC known vector and blind arbitrary prefix, phase, random data', () => {
  assert.equal(crc16(Buffer.from('123456789')), 0x29b1);
  for (const ppm of [0, 200, -200, 750, -750]) {
    const payload = randomBytes(100);
    const signal = modulate(payload, {samplePpm: ppm, phase: 1.271});
    const arbitrary = Buffer.concat([Buffer.alloc(PCM_BYTES * 11 + 146), signal]);
    const padded = Buffer.concat([arbitrary, Buffer.alloc((-arbitrary.length % PCM_BYTES + PCM_BYTES) % PCM_BYTES)]);
    const {frames} = decode(padded);
    assert.equal(frames.length, 1, `ppm${ppm}`);
    assert.deepEqual(frames[0].payload, payload);
  }
});
test('truncated/malformed/noise has bounded memory and cannot invent packet', () => {
  const decoder = new Decoder();
  assert.throws(() => decoder.feed(Buffer.alloc(17)));
  let frames = [];
  for (let i = 0; i < 430; i++) frames.push(...decoder.feed(Buffer.alloc(PCM_BYTES)));
  assert.equal(frames.length, 0);
  assert.ok(decoder.maxBufferSamples <= MAX_BUFFER);
  const signal = modulate(randomBytes(90));
  assert.equal(decode(signal.subarray(0, PCM_BYTES * 20)).frames.length, 0);
  assert.equal(decode(randomBytes(PCM_BYTES * 100)).frames.length, 0);
});
test('a physical erasure is rejected by confidence even when bit guesses match original bytes', () => {
  const pcm = modulate(Buffer.alloc(80, 0xff));
  // Erase80ms inside the all-one payload, not the preamble or packet header.
  // The decoder knows neither this location nor what was originally sent.
  pcm.fill(0, 4000 * 2, 4640 * 2);
  const {frames, decoder} = decode(pcm);
  assert.equal(frames.length, 0);
  assert.ok(decoder.erasureRejections > 0);
});

test('actual opposite-tone bit changes are rejected by the CRC', () => {
  const pcm = modulate(Buffer.alloc(80, 0xff));
  const opposite = modulate(Buffer.alloc(80, 0));
  opposite.copy(pcm, 4000 * 2, 4000 * 2, 4640 * 2);
  const {frames, decoder} = decode(pcm);
  assert.equal(frames.length, 0);
  assert.ok(decoder.crcRejections > 0);
});
