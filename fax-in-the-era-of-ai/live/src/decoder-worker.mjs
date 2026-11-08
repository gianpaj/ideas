import {parentPort} from 'node:worker_threads';
import {Decoder} from './signal.mjs';
const decoder = new Decoder();
let chunks = 0;
parentPort.on('message', message => {
  try {
    const frames = decoder.feed(Buffer.from(message.pcm));
    chunks++;
    for (const frame of frames) parentPort.postMessage({type: 'frame', ...frame});
    if (chunks % 16 === 0) parentPort.postMessage({type: 'progress', chunks, maxBufferSamples: decoder.maxBufferSamples, crcRejections: decoder.crcRejections, erasureRejections: decoder.erasureRejections});
  } catch {
    parentPort.postMessage({type: 'invalid-pcm'});
  }
});
