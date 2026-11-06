#!/usr/bin/env node
import {parseArgs} from 'node:util';
import {mkdirSync, writeFileSync, chmodSync} from 'node:fs';
import {randomBytes} from 'node:crypto';
import {resolve, join} from 'node:path';
import {runEndpoint} from './endpoint.mjs';
import {runLink} from './link.mjs';

const command = process.argv[2];
const optionNames = [
  'role', 'key', 'bind', 'peer', 'data', 'log', 'wall-offset-ms', 'sample-ppm', 'timeout-ms', 'retry-ms', 'retries', 'jitter-ms',
  'a', 'b', 'a-delay-ms', 'b-delay-ms', 'loss', 'noise-db', 'echo', 'duration-ms', 'mute', 'drop-a-burst', 'drop-b-burst', 'corrupt', 'capture', 'state', 'seed'
];
const numericOptions = new Set(['wall-offset-ms', 'sample-ppm', 'timeout-ms', 'retry-ms', 'retries', 'jitter-ms', 'a-delay-ms', 'b-delay-ms', 'loss', 'noise-db', 'echo', 'duration-ms', 'drop-a-burst', 'drop-b-burst', 'seed']);
try {
  // parseArgs intentionally treats '-200' as an ambiguous option. Numeric-only
  // normalization supports ordinary '--sample-ppm -200' safely; do not rewrite
  // arbitrary textual payloads or unknown flags.
  const input = process.argv.slice(3), args = [];
  for (let i = 0; i < input.length; i++) {
    if (numericOptions.has(input[i].slice(2)) && input[i].startsWith('--') && /^-(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(input[i + 1] ?? '')) args.push(`${input[i]}=${input[++i]}`);
    else args.push(input[i]);
  }
  const {values} = parseArgs({args, strict: true, options: Object.fromEntries(optionNames.map(key => [key, {type: 'string'}]))});
  if (Number(process.versions.node.split('.')[0]) < 24) throw Error('Node24 required');
  if (command === 'init') {
    const state = resolve(values.state ?? '.state');
    mkdirSync(state, {recursive: true, mode: 0o700});
    chmodSync(state, 0o700);
    const key = join(state, 'pair.key');
    writeFileSync(key, randomBytes(32), {flag: 'wx', mode: 0o600});
    process.stderr.write(JSON.stringify({event: 'provisioned', path: key, note: 'private single-user key; copy separately over trusted channel, never commit'}) + '\n');
  } else if (command === 'endpoint') {
    process.exitCode = await runEndpoint(values);
  } else if (command === 'link') {
    process.exitCode = await runLink(values);
  } else {
    process.stderr.write('Usage: node src/cli.mjs init --state .state\n       node src/cli.mjs link [--bind 127.0.0.1:31000 --a 127.0.0.1:31001 --b 127.0.0.1:31002]\n       node src/cli.mjs endpoint --role initiator|responder --key .state/pair.key [--bind 127.0.0.1:31001 --peer 127.0.0.1:31000]\nSee README.md for complete runnable commands.\n');
    process.exitCode = 1;
  }
} catch (error) {
  process.stderr.write(JSON.stringify({event: 'error', reason: error.message}) + '\n');
  process.exitCode = 2;
}
