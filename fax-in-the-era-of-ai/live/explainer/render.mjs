#!/usr/bin/env node
/** Re-render the explainer from the actual capture and its blindly decoded frames. */
import {readFileSync, writeFileSync, mkdirSync, statSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
const source = path.resolve(here, '../evidence');
const temp = path.join(here, '.render');
mkdirSync(temp, {recursive: true});
const wav = path.join(source, 'live-exchange-2026-11-06.wav');
const metadataPath = path.join(source, 'live-exchange-decoded.json');
const captureManifestPath = path.join(source, 'live-exchange-manifest.json');
const decoded = JSON.parse(readFileSync(metadataPath, 'utf8'));
const capture = JSON.parse(readFileSync(captureManifestPath, 'utf8'));
const sha = file => createHash('sha256').update(readFileSync(file)).digest('hex');
if (sha(wav) !== decoded.artifactSha256) throw Error('Decoded timings do not match the WAV hash');
const duration = decoded.durationSeconds;
const messages = [
  ['HELLO', 'Start a fresh session', 'PAIRING · A sends a fresh random session ID'],
  ['CHALLENGE', 'Add a fresh challenge', 'PAIRING · B returns its own fresh challenge'],
  ['CONFIRM', 'Prove the derived key', 'PAIRING · A proves knowledge of the session key'],
  ['READY', 'Confirm the pairing', 'PAIRING · B confirms; A can now send data'],
  ['DATA', "Send the user’s bytes", 'TRANSFER · A sends its real application bytes'],
  ['RECEIPT', 'Echo bytes + digest', 'VERIFY · B returns the bytes and their digest'],
  ['CLOSE', 'Finish (best effort)', 'CLOSE · A has verified the reply; no final ACK'],
];
if (decoded.frames.length !== messages.length) throw Error('Expected the seven-frame live exchange');
let previousEnd = 0;
for (const [i, frame] of decoded.frames.entries()) {
  const channel = i % 2 ? 'responder-to-initiator' : 'initiator-to-responder';
  if (frame.type !== messages[i][0] || frame.channel !== channel ||
      !(frame.startSeconds >= previousEnd && frame.endSeconds > frame.startSeconds && frame.endSeconds <= duration)) {
    throw Error(`Unexpected frame or overlapping timings at ${i}`);
  }
  previousEnd = frame.endSeconds;
}

const C = {background: '#0b1322', panel: '#111e31', text: '#f1f5fc', muted: '#a4b4cc',
  quiet: '#647792', cyan: '#63deef', amber: '#ffc977', line: '#33455f'};
const xml = str => String(str).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;'}[c]));
const text = (x, y, label, size = 22, color = C.text, extra = '') =>
  `<text x="${x}" y="${y}" font-size="${size}" fill="${color}" ${extra}>${xml(label)}</text>`;

/** The overview and every animated frame use exactly the same SVG layout. */
function svg(active = null, moment = null) {
  const overview = moment === null;
  let body = `<rect width="1280" height="720" fill="${C.background}"/>
  <path d="M0 0H1280V110H0Z" fill="#0e1a2c"/>
  ${text(64, 59, 'Two apps, talking in tones', 40, C.text, 'font-weight="700"')}
  ${text(64, 97, 'Actual live audio. Each reply is triggered by the frame it decodes.', 22, C.muted)}
  <rect x="1003" y="30" width="213" height="34" rx="17" fill="#1c2b40"/>
  ${text(1109.5, 53, '15.94 s · REAL CAPTURE', 16, C.text, 'text-anchor="middle" font-weight="700"')}
  <rect x="66" y="127" width="284" height="63" rx="15" fill="#123546" stroke="${C.cyan}" stroke-width="1.5"/>
  ${text(208, 155, 'A · INITIATOR', 25, C.cyan, 'text-anchor="middle" font-weight="700"')}
  ${text(208, 178, 'Independent Node.js app', 17, C.text, 'text-anchor="middle"')}
  <rect x="930" y="127" width="284" height="63" rx="15" fill="#3a2e23" stroke="${C.amber}" stroke-width="1.5"/>
  ${text(1072, 155, 'B · RESPONDER', 25, C.amber, 'text-anchor="middle" font-weight="700"')}
  ${text(1072, 178, 'Independent Node.js app', 17, C.text, 'text-anchor="middle"')}
  ${text(640, 150, 'Same private key', 23, C.text, 'text-anchor="middle" font-weight="600"')}
  ${text(640, 177, 'provisioned before the exchange', 18, C.muted, 'text-anchor="middle"')}
  <path d="M208 199V550M1072 199V550" fill="none" stroke="${C.line}" stroke-width="2"/>`;
  for (const [i, [name, description]] of messages.entries()) {
    const y = 228 + i * 50;
    const highlighted = active === i;
    const done = !overview && moment >= decoded.frames[i].endSeconds;
    const color = i % 2 ? C.amber : C.cyan;
    const opacity = overview || highlighted ? 1 : done ? 0.63 : 0.34;
    const from = i % 2 ? 1058 : 222;
    const to = i % 2 ? 222 : 1058;
    const arrow = i % 2 ? `M${to + 12} ${y - 7}L${to} ${y}L${to + 12} ${y + 7}` : `M${to - 12} ${y - 7}L${to} ${y}L${to - 12} ${y + 7}`;
    const fill = highlighted ? (i % 2 ? '#372d24' : '#12313f') : C.background;
    body += `<g opacity="${opacity}">
      ${highlighted ? `<rect x="64" y="${y - 22}" width="1152" height="44" rx="10" fill="${fill}" stroke="${color}" stroke-width="1"/>` : ''}
      <circle cx="92" cy="${y}" r="14" fill="${highlighted ? color : C.panel}" stroke="${color}"/>
      ${text(92, y + 6, i + 1, 17, highlighted ? C.background : color, 'text-anchor="middle" font-weight="700"')}
      <line x1="${from}" y1="${y}" x2="${to}" y2="${y}" stroke="${color}" stroke-width="2.5"/>
      <path d="${arrow}" fill="none" stroke="${color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
      <rect x="332" y="${y - 19}" width="616" height="38" rx="7" fill="${fill}"/>
      ${text(350, y + 8, name, 24, color, 'font-weight="700"')}
      ${text(555, y + 8, description, 23, C.text)}
    </g>`;
  }
  let status;
  if (overview) status = 'PAIR → SEND DATA → VERIFY THE REPLY → CLOSE';
  else if (active !== null) status = messages[active][2];
  else if (moment < decoded.frames[0].startSeconds) status = 'LISTENING · The first audio frame is about to arrive';
  else if (moment >= decoded.frames.at(-1).endSeconds) status = 'FINISHED · All seven audio frames were decoded';
  else status = 'LISTENING · A short gap while the peer decodes and replies';
  body += `${text(640, 580, status, 23, active === null ? C.muted : C.text, 'text-anchor="middle" font-weight="600"')}
    ${text(64, 607, 'Original recording', 16, C.muted)}
    ${text(1216, 607, 'Normal speed · no speech added', 16, C.muted, 'text-anchor="end"')}
    <rect x="64" y="620" width="1152" height="10" rx="5" fill="#27364c"/>`;
  for (const [i, frame] of decoded.frames.entries()) {
    const x = 64 + 1152 * frame.startSeconds / duration;
    const w = 1152 * (frame.endSeconds - frame.startSeconds) / duration;
    body += `<rect x="${x.toFixed(4)}" y="620" width="${w.toFixed(4)}" height="10" rx="3" fill="${i % 2 ? C.amber : C.cyan}" opacity="${overview || active === i ? 1 : 0.45}"/>`;
  }
  body += `${text(640, 665, 'Shared-secret authentication. Data is NOT encrypted.', 23, C.text, 'text-anchor="middle"')}
    ${text(640, 699, 'CUSTOM AIP-FSK2 · NOT A FAX STANDARD · NO PHONE OR WEB CONNECTION', 17, C.muted, 'text-anchor="middle"')}`;
  return `<?xml version="1.0" encoding="UTF-8"?>
<!-- Actual capture SHA-256: ${decoded.artifactSha256}. Timing source: ../evidence/live-exchange-decoded.json. -->
<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720" role="img" aria-labelledby="title desc">
<title id="title">Two Node.js apps exchange authenticated data through audio</title>
<desc id="desc">Seven audio frames: initiator HELLO, responder CHALLENGE, initiator CONFIRM, responder READY, initiator DATA, responder RECEIPT, initiator CLOSE. A shared private key is provisioned beforehand. The receipt echoes the data and a digest; CLOSE is best effort. Data is authenticated but not encrypted. This is the custom experimental AIP-FSK2 protocol, not a fax standard.</desc>
<g font-family="DejaVu Sans, sans-serif">${body}</g></svg>
`.replace(/[ \t]+$/gm, '');
}

function run(program, args) {
  const result = spawnSync(program, args, {encoding: 'utf8', maxBuffer: 8 * 1024 * 1024});
  if (result.error || result.status !== 0) throw Error(`${program}: ${result.error?.message || result.stderr}`);
  return result.stdout;
}
function rasterize(svgPath, pngPath) {
  run('ffmpeg', ['-nostdin', '-v', 'error', '-y', '-c:v', 'librsvg', '-i', svgPath, '-frames:v', '1', '-threads', '1', pngPath]);
}

writeFileSync(path.join(here, 'overview.svg'), svg());
rasterize(path.join(here, 'overview.svg'), path.join(temp, 'overview.png'));
// Segment boundaries are the exact decoded audio start/end times, not a hand-timed script.
const boundaries = [0, ...decoded.frames.flatMap(f => [f.startSeconds, f.endSeconds]), duration];
const segments = [];
for (let i = 0; i < boundaries.length - 1; i++) {
  const start = boundaries[i], end = boundaries[i + 1], midpoint = (start + end) / 2;
  if (!(end > start)) continue;
  const activeIndex = decoded.frames.findIndex(f => midpoint >= f.startSeconds && midpoint < f.endSeconds);
  const active = activeIndex < 0 ? null : activeIndex;
  const stem = `segment-${String(i).padStart(2, '0')}`;
  const svgPath = path.join(temp, `${stem}.svg`), pngPath = path.join(temp, `${stem}.png`);
  writeFileSync(svgPath, svg(active, midpoint));
  rasterize(svgPath, pngPath);
  segments.push({startSeconds: start, endSeconds: end, activeFrame: active === null ? null : messages[active][0], file: pngPath});
}
const concatPath = path.join(temp, 'frames.ffconcat');
// The option gives the concat demuxer millisecond precision before CFR quantization.
const quote = value => `'${value.replaceAll("'", "'\\''")}'`;
writeFileSync(concatPath, 'ffconcat version 1.0\n' + segments.map(s =>
  `file ${quote(s.file)}\noption framerate 1000\nduration ${(s.endSeconds - s.startSeconds).toFixed(9)}\n`).join('') +
  `file ${quote(segments.at(-1).file)}\noption framerate 1000\n`);
const cursorSvg = path.join(temp, 'cursor.svg'), cursorPng = path.join(temp, 'cursor.png');
writeFileSync(cursorSvg, '<svg xmlns="http://www.w3.org/2000/svg" width="4" height="24"><rect width="4" height="24" rx="2" fill="#ffffff"/></svg>');
rasterize(cursorSvg, cursorPng);
const output = path.join(here, 'audio-handshake-explained.mp4');
run('ffmpeg', ['-nostdin', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', concatPath,
  '-i', wav, '-loop', '1', '-framerate', '30', '-i', cursorPng,
  '-filter_complex', `[0:v]fps=30[diagram];[diagram][2:v]overlay=x='62+${1152 / duration}*t':y=613:shortest=1,format=yuv420p[out]`,
  '-map', '[out]', '-map', '1:a:0', '-t', String(duration), '-c:v', 'libx264', '-preset', 'medium', '-crf', '22',
  '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2', '-movflags', '+faststart',
  '-movie_timescale', '48000', '-video_track_timescale', '30000',
  '-map_metadata', '-1', '-metadata', 'title=Two apps, talking in tones — actual live AIP-FSK2 exchange',
  '-metadata', 'comment=Original WAV, untrimmed and normal speed; only the explanatory SVG is animated.', output]);
const preview = path.join(temp, 'preview-receipt.png');
run('ffmpeg', ['-nostdin', '-v', 'error', '-y', '-ss', '12.0', '-i', output, '-frames:v', '1', '-threads', '1', preview]);
const probe = JSON.parse(run('ffprobe', ['-v', 'error', '-show_entries',
  'format=duration,size:stream=index,codec_name,width,height,pix_fmt,r_frame_rate,sample_rate,channels,duration', '-of', 'json', output]));
// A video export must preserve the modem data, not only sound approximately right.
// The blind receiver gets only the exported audio. Expected hashes are compared AFTER decoding.
const roundtripWav = path.join(temp, 'roundtrip.wav');
run('ffmpeg', ['-nostdin', '-v', 'error', '-y', '-i', output, '-ar', '8000', '-ac', '2', '-c:a', 'pcm_s16le', roundtripWav]);
const roundtrip = JSON.parse(run(process.execPath, [path.join(source, 'decode-live-capture.mjs'), roundtripWav]));
if (roundtrip.frames.length !== decoded.frames.length || roundtrip.frames.some((f, i) =>
  f.type !== decoded.frames[i].type || f.channel !== decoded.frames[i].channel || f.packetSha256 !== decoded.frames[i].packetSha256)) {
  throw Error('MP4 audio did not preserve all seven original modem packets');
}
const videoStream = probe.streams.find(s => s.codec_name === 'h264');
const audioStream = probe.streams.find(s => s.codec_name === 'aac');
if (videoStream?.width !== 1280 || videoStream?.height !== 720 || audioStream?.channels !== 2 ||
    Math.abs(Number(probe.format.duration) - duration) > 1 / 48000) throw Error('Unexpected exported streams or duration');
const manifest = {
  purpose: 'Explanatory SVG animation synchronized to an actual causal two-endpoint audio capture, not a protocol simulation.',
  sourceRevision: '17eb26cd1eb97a2fda24ff90124fa4851b4a77e6',
  sourceRevisionNote: 'Repository revision containing the retained capture and finalized validation, before adding this explainer.',
  protocol: 'custom experimental AIP-FSK2; authenticated with a provisioned PSK, not encrypted or fax-compatible',
  audio: {file: '../evidence/live-exchange-2026-11-06.wav', sha256: sha(wav), durationSeconds: duration,
    processing: 'Untrimmed, unchanged speed, original stereo channel order; AAC encoding and 8 kHz to 48 kHz resampling only. No speech, normalization, added tones or soundtrack.'},
  timing: {file: '../evidence/live-exchange-decoded.json', sha256: sha(metadataPath),
    basis: decoded.note, animationFramesPerSecond: 30, boundaryQuantization: 'Exact metadata boundaries rendered on a 30 fps grid (within one frame). The recording timestamps are link-delivery chronology, not endpoint authentication-event timestamps.'},
  captureManifest: {file: '../evidence/live-exchange-manifest.json', sha256: sha(captureManifestPath), conditions: capture.conditions},
  exportValidation: {method: 'Extract MP4 audio to stereo 8 kHz PCM; blindly decode without timings or expected messages; then compare all decoded packet hashes/channels/types to the original.',
    originalPackets: decoded.frames.length, matchedPackets: roundtrip.frames.length, aacTargetBitrate: 192000,
    note: 'The initial 80 kbit/s export recovered only six packet CRCs and was discarded. The retained export preserves all seven exact packet hashes. This validates this export, not arbitrary codecs or carrier paths.'},
  frames: decoded.frames.map(({type, channel, startSeconds, endSeconds}) => ({type, channel, startSeconds, endSeconds})),
  artifacts: ['overview.svg', 'audio-handshake-explained.mp4'].map(file => ({file, sha256: sha(path.join(here, file)), bytes: statSync(path.join(here, file)).size})),
  toolchain: {node: process.version, ffmpeg: run('ffmpeg', ['-version']).split('\n')[0], font: 'DejaVu Sans', renderer: 'FFmpeg librsvg decoder'},
  ffprobe: probe,
};
writeFileSync(path.join(here, 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
console.log(JSON.stringify({output, overview: path.join(here, 'overview.svg'), preview, probe}, null, 2));
