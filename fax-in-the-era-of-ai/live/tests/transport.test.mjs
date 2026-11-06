import test from 'node:test';
import assert from 'node:assert/strict';
import {randomBytes} from 'node:crypto';
import {AdcClock, encodeDatagram, decodeDatagram} from '../src/transport.mjs';
import {modulate, Decoder, PCM_BYTES, MAX_BUFFER} from '../src/signal.mjs';

test('independent TX/ADC sample clocks change real waveform, receiver learns no ppm', () => {
  for (const [tx, rx] of [[200, -200], [-200, 200], [1000, -1000]]) {
    const payload = randomBytes(70), pcm = modulate(payload, {samplePpm: tx});
    const adc = new AdcClock(rx), decoder = new Decoder();
    const frames = [];
    for (let i = 0; i < pcm.length; i += PCM_BYTES) for (const chunk of adc.feed(pcm.subarray(i, i + PCM_BYTES))) frames.push(...decoder.feed(chunk));
    for (let i = 0; i < 20; i++) for (const chunk of adc.feed(Buffer.alloc(PCM_BYTES))) frames.push(...decoder.feed(chunk));
    assert.equal(frames.length, 1, `tx${tx}/rx${rx}`);
    assert.deepEqual(frames[0].payload, payload);
    assert.ok(adc.input.length < 2);
    assert.ok(adc.output.length < 160);
    assert.ok(decoder.maxBufferSamples <= MAX_BUFFER);
  }
});
test('transport header is only independent sequence/sample counters plus PCM', () => {
  const pcm = randomBytes(PCM_BYTES), packet = encodeDatagram(pcm, 0xffffffff, 18239);
  assert.equal(packet.length, 332);
  const decoded = decodeDatagram(packet);
  assert.equal(decoded.seq, 0xffffffff);
  assert.equal(decoded.sample, 18239);
  assert.deepEqual(decoded.pcm, pcm);
  assert.equal(decodeDatagram(packet.subarray(0, -1)), null);
  packet[0] ^= 1;
  assert.equal(decodeDatagram(packet), null);
});
