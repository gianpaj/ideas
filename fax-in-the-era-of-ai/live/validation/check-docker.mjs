// Run after `docker compose -p NAME up -d`; inspect only this test's containers.
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {mkdir,writeFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const exec=promisify(execFile);
const project=process.argv[2]??'phonepair-parent-20261106';
assert.match(project,/^[a-z0-9][a-z0-9_-]*$/);
const name=role=>`${project}-${role}-1`;
const docker=async args=>exec('docker',args,{timeout:105000,maxBuffer:2e6});
const parse=text=>text.trim().split('\n').filter(Boolean).flatMap(line=>{
  try{return [JSON.parse(line)];}catch{return [];}
});
const wait=await docker(['wait',name('initiator'),name('responder')]);
assert.deepEqual(wait.stdout.trim().split('\n'),['0','0'],'both endpoints must exit successfully');
const evidence={scope:'Separate Docker endpoint containers plus a PCM-only userspace impairment link; no real telephone or physical audio-device test',project,endpoints:{}};
for(const role of ['initiator','responder']) {
  const logs=await docker(['logs',name(role)]);
  const rows=parse(logs.stdout+'\n'+logs.stderr);
  const result=rows.findLast(row=>row.event==='result');
  assert.equal(result?.success,true,JSON.stringify(result));
  if(role==='initiator')assert.equal(result.receiptVerified,true);
  else assert.equal(result.operationCount,1);
  const inspection=JSON.parse((await docker(['inspect',name(role)])).stdout)[0];
  assert.equal(inspection.HostConfig.Privileged,false);
  assert.equal(inspection.HostConfig.ReadonlyRootfs,true);
  assert.ok(inspection.HostConfig.CapDrop.includes('ALL'));
  assert.equal(Object.keys(inspection.HostConfig.PortBindings??{}).length,0);
  evidence.endpoints[role]={result,ready:rows.find(row=>row.event==='ready'),
    received:rows.filter(row=>row.event==='transition').map(row=>row.received),
    actualCommand:inspection.Config.Cmd,imageId:inspection.Image,
    privileged:inspection.HostConfig.Privileged,readOnly:inspection.HostConfig.ReadonlyRootfs,
    droppedCapabilities:inspection.HostConfig.CapDrop,hostPortsPublished:false};
}
const a=evidence.endpoints.initiator,b=evidence.endpoints.responder;
assert.equal(a.result.sessionFingerprint,b.result.sessionFingerprint);
assert.ok(Math.abs((Date.parse(a.ready.wallTime)-Date.parse(b.ready.wallTime))-10800000)<5000);
const link=await docker(['logs',name('link')]);
evidence.link=parse(link.stdout+'\n'+link.stderr).find(row=>row.event==='ready');
assert.deepEqual(evidence.link.delayMs,{a:300,b:650});
assert.equal(evidence.link.jitterMs,60);
evidence.status='passed';
await mkdir('validation/evidence',{recursive:true});
await writeFile('validation/evidence/docker.json',JSON.stringify(evidence,null,2)+'\n');
console.log(JSON.stringify({status:'passed',sessionFingerprint:a.result.sessionFingerprint,
  initiator:a.result.reason,responder:b.result.reason,parameters:evidence.link},null,2));
