import {appendFileSync} from 'node:fs';
import {performance} from 'node:perf_hooks';
export function logger({role, file, wallOffsetMs = 0}) {
  if (file) appendFileSync(file, '', {mode: 0o600});
  const start = performance.now();
  return (event, fields = {}) => {
    const row = {event, role, wallTime: new Date(Date.now() + wallOffsetMs).toISOString(), elapsedMs: Math.round((performance.now() - start) * 1000) / 1000, ...fields};
    const line = JSON.stringify(row) + '\n';
    process.stderr.write(line);
    if (file) appendFileSync(file, line, {mode: 0o600});
  };
}
