import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync, spawn} from 'node:child_process';
import {mkdtempSync, writeFileSync, rmSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {randomBytes} from 'node:crypto';
import dgram from 'node:dgram';
const cli = new URL('../src/cli.mjs', import.meta.url).pathname;
function state() {
  const directory = mkdtempSync(join(tmpdir(), 'phonepair-cli-'));
  const key = join(directory, 'key');
  writeFileSync(key, randomBytes(32), {mode: 0o600});
  return {directory, key};
}
test('negative numeric flags parse; invalid address exits promptly without DSP worker leak', () => {
  const {directory, key} = state();
  try {
    const result = spawnSync(process.execPath, [cli, 'endpoint', '--role', 'initiator', '--key', key, '--sample-ppm', '-200', '--wall-offset-ms', '-7200000', '--bind', 'bad'], {encoding: 'utf8', timeout: 2000});
    assert.equal(result.status, 2);
    assert.equal(result.error, undefined);
    const error = JSON.parse(result.stderr);
    assert.equal(error.event, 'error');
    assert.match(error.reason, /host:port/);
  } finally { rmSync(directory, {recursive: true}); }
});
test('already-used UDP port exits promptly and cleans up worker', async () => {
  const {directory, key} = state(), socket = dgram.createSocket('udp4');
  await new Promise(resolve => socket.bind(0, '127.0.0.1', resolve));
  try {
    const result = await new Promise((resolve, reject) => {
      const child = spawn(process.execPath, [cli, 'endpoint', '--role', 'initiator', '--key', key, '--bind', `127.0.0.1:${socket.address().port}`]);
      let stderr = '';
      child.stderr.on('data', data => { stderr += data; });
      const timer = setTimeout(() => { child.kill('SIGKILL'); reject(Error('worker cleanup hung')); }, 3000);
      child.on('exit', status => { clearTimeout(timer); resolve({status, stderr}); });
    });
    assert.equal(result.status, 2);
    assert.match(result.stderr, /EADDRINUSE/);
  } finally { socket.close(); rmSync(directory, {recursive: true}); }
});
