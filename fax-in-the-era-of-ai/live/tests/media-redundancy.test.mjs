import test from 'node:test';
import assert from 'node:assert/strict';
import dgram from 'node:dgram';
import {performance} from 'node:perf_hooks';
import {randomBytes} from 'node:crypto';
import {UdpAudio, encodeDatagram, decodeDatagram} from '../src/transport.mjs';
import {UniqueMedia} from '../src/link.mjs';
import {PCM_BYTES} from '../src/signal.mjs';
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
async function until(predicate) {
  const end = performance.now() + 1000;
  while (!predicate()) {
    if (performance.now() > end) throw Error('UDP condition timed out');
    await pause(5);
  }
}

test('actual UDP duplicate copies play once and retain identical transport metadata', async () => {
  const sender = dgram.createSocket('udp4');
  await new Promise(resolve => sender.bind(0, '127.0.0.1', resolve));
  const played = [], errors = [], outgoing = [];
  sender.on('message', message => outgoing.push(Buffer.from(message)));
  const audio = new UdpAudio({bind: {host: '127.0.0.1', port: 0}, peer: {host: '127.0.0.1', port: sender.address().port}, jitterMs: 0,
    onPcm: pcm => played.push(Buffer.from(pcm)), onError: error => errors.push(error)});
  await audio.open();
  try {
    const pcm = randomBytes(PCM_BYTES), wire = encodeDatagram(pcm, 500, 12345);
    const destination = audio.socket.address().port;
    sender.send(wire, destination, '127.0.0.1');
    sender.send(wire, destination, '127.0.0.1');
    await until(() => audio.stats.receivedDatagrams === 2);
    assert.equal(audio.queue.size, 1);
    assert.equal(audio.stats.received, 1);
    assert.equal(audio.stats.duplicates, 1);
    audio.playout(performance.now() + 100);
    assert.equal(played.length, 1);
    assert.deepEqual(played[0], pcm);
    assert.equal(audio.next, 501);
    sender.send(wire, destination, '127.0.0.1'); // Delayed redundant copy.
    await until(() => audio.stats.receivedDatagrams === 3);
    assert.equal(audio.queue.size, 0);
    assert.equal(played.length, 1);
    assert.equal(audio.stats.lateDuplicates, 1);
    assert.equal(audio.stats.lost, 0);
    const beforeSample = audio.sample, beforeSeq = audio.seq;
    audio.send(pcm);
    await until(() => outgoing.length === 2);
    assert.deepEqual(outgoing[0], outgoing[1]);
    assert.deepEqual(decodeDatagram(outgoing[0]).pcm, pcm);
    assert.equal(audio.seq, (beforeSeq + 1) >>> 0);
    assert.equal(audio.sample, (beforeSample + 160) >>> 0);
    assert.equal(audio.stats.sent, 1);
    assert.equal(audio.stats.sentDatagrams, 2);
    assert.equal(outgoing[0].length, 332); // No protocol plaintext metadata.
    assert.deepEqual(errors, []);
  } finally { audio.close(); sender.close(); }
});

test('relay stateful channel advances once per unique PCM; cache is bounded and rejects stale/colliding copies', () => {
  let processed = 0;
  const cache = new UniqueMedia(pcm => {
    processed++;
    const colored = Buffer.from(pcm);
    colored.writeInt16LE(processed, 0); // An observable stateful clock marker.
    return colored;
  }, 3);
  const one = {seq: 1, sample: 160, pcm: Buffer.alloc(PCM_BYTES)};
  const first = cache.accept(one), repeated = cache.accept(one);
  assert.equal(processed, 1);
  assert.equal(repeated.duplicate, true);
  assert.equal(first.entry, repeated.entry);
  assert.equal(first.entry.pcm.readInt16LE(), 1);
  assert.equal(cache.accept({...one, sample: 999}).invalid, true);
  const corruptedCopy = {...one, pcm: Buffer.alloc(PCM_BYTES, 1)};
  assert.equal(cache.accept(corruptedCopy).invalid, true);
  for (let seq = 2; seq < 20; seq++) cache.accept({seq, sample: seq * 160, pcm: Buffer.alloc(PCM_BYTES)});
  assert.equal(processed, 19);
  assert.equal(cache.entries.size, 3);
  assert.equal(cache.maxEntries, 3);
  assert.equal(cache.accept(one).invalid, true); // Evicted stale seq never advances channel again.
  assert.equal(processed, 19);
  assert.throws(() => new UniqueMedia(() => Buffer.alloc(PCM_BYTES), 0));
  assert.throws(() => new UniqueMedia(() => Buffer.alloc(PCM_BYTES), 1025));
  assert.throws(() => new UdpAudio({redundancy: 3}));
});
