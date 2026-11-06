// Independent separate-process acceptance runner. No endpoint imports, pairing
// state access, known nonces, or protocol injection; every exchange uses PCM.
import {spawn} from 'node:child_process';
import {mkdtemp, readFile, writeFile, mkdir, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join, resolve} from 'node:path';
import {once} from 'node:events';
import assert from 'node:assert/strict';

const cli = resolve('src/cli.mjs');
const out = resolve(process.argv[2] ?? 'validation/evidence/parent-matrix.json');
const pause = ms => new Promise(r => setTimeout(r, ms));
const cases = [
  {name:'baseline', expect:true, limit:45000, link:{'noise-db':24,echo:.1}},
  {name:'global-delay-independent-clocks', expect:true, limit:90000,
   a:{'sample-ppm':200,'wall-offset-ms':3600000},
   b:{'sample-ppm':-200,'wall-offset-ms':-7200000},
   link:{'a-delay-ms':300,'b-delay-ms':650,'jitter-ms':60,'noise-db':24,echo:.1}},
  {name:'drop-first-response-retry', expect:true, limit:60000,
   link:{'drop-b-burst':1,'noise-db':24,echo:.1}},
  {name:'wrong-key-rejected', expect:false, limit:14000, wrongKey:true,
   a:{'retry-ms':3500}, b:{'retry-ms':3500}, link:{'noise-db':24}},
  {name:'muted-return-cannot-succeed', expect:false, limit:14000,
   a:{'retry-ms':3500}, b:{'retry-ms':3500}, link:{mute:'b','noise-db':24}},
  {name:'cancel-releases-processes', expect:false, limit:14000, cancelAfter:1200,
   link:{'noise-db':24}},
  {name:'seeded-one-percent-pcm-loss', expect:true, limit:120000,
   a:{'retry-ms':5000,retries:6},b:{'retry-ms':5000,retries:6},
   link:{loss:.01,'jitter-ms':20,seed:20261106,'noise-db':24,echo:.1}},
];

function launch(command, options) {
  const args=[cli,command,...Object.entries(options).flatMap(([k,v])=>['--'+k,String(v)])];
  const child=spawn(process.execPath,args,{stdio:['ignore','ignore','pipe']});
  let stderr='';
  child.stderr.on('data',chunk=>{stderr+=chunk; if(stderr.length>2e6)child.kill('SIGTERM');});
  const exit=once(child,'exit').then(([code,signal])=>({code,signal}));
  return {child,exit,rows:()=>stderr.trim().split('\n').filter(Boolean).map(line=>{
    try{return JSON.parse(line);}catch{return {event:'non-json',length:line.length};}
  })};
}
async function boundedExit(process,limit) {
  let timer;
  try{return await Promise.race([process.exit,new Promise((_,reject)=>{
    timer=setTimeout(()=>reject(Error('process did not exit within bounded test deadline')),limit);
  })]);} finally {clearTimeout(timer);}
}

const results=[];
for(let index=0;index<cases.length;index++) {
  const config=cases[index], scratch=await mkdtemp(join(tmpdir(),'phonepair-parent-'));
  const port=32000+index*3, address=p=>'127.0.0.1:'+p;
  const processes=[];
  let cancelTimer;
  try {
    const init=launch('init',{state:scratch});processes.push(init);
    assert.equal((await boundedExit(init,5000)).code,0,'key provisioning');
    if(config.wrongKey) {
      const other=launch('init',{state:join(scratch,'other')});processes.push(other);
      assert.equal((await boundedExit(other,5000)).code,0);
    }
    const link=launch('link',{bind:address(port),a:address(port+1),b:address(port+2),
                    'duration-ms':config.limit+4000,...config.link});processes.push(link);
    await pause(250);
    const shared={key:join(scratch,'pair.key'),peer:address(port),'jitter-ms':200,'timeout-ms':config.limit};
    const b=launch('endpoint',{...shared,role:'responder',bind:address(port+2),...config.b});processes.push(b);
    await pause(250);
    const a=launch('endpoint',{...shared,role:'initiator',bind:address(port+1),
                    data:'independent '+config.name,...config.a,
                    ...(config.wrongKey?{key:join(scratch,'other','pair.key')}:{})});processes.push(a);
    if(config.cancelAfter)cancelTimer=setTimeout(()=>{
      a.child.kill('SIGINT');b.child.kill('SIGINT');
    },config.cancelAfter);
    const [ae,be]=await Promise.all([boundedExit(a,config.limit+5000),boundedExit(b,config.limit+5000)]);
    const ar=a.rows(),br=b.rows();
    const resultA=ar.findLast(r=>r.event==='result'),resultB=br.findLast(r=>r.event==='result');
    assert.ok(resultA&&resultB,'both endpoints must report an outcome');
    if(config.expect) {
      assert.equal(ae.code,0,JSON.stringify(resultA));
      assert.equal(be.code,0,JSON.stringify(resultB));
      assert.equal(resultA.success,true);
      assert.equal(resultA.receiptVerified,true);
      assert.equal(resultB.success,true);
      assert.equal(resultB.operationCount,1);
      assert.equal(resultA.sessionFingerprint,resultB.sessionFingerprint);
      assert.ok(resultA.decoder.maxBufferSamples <= 64000);
      assert.ok(resultB.decoder.maxBufferSamples <= 64000);
      assert.ok(resultA.transport.maxQueued <= 128);
      assert.ok(resultB.transport.maxQueued <= 128);
      if(config.name==='global-delay-independent-clocks') {
        const wallA=Date.parse(ar.find(r=>r.event==='ready').wallTime);
        const wallB=Date.parse(br.find(r=>r.event==='ready').wallTime);
        assert.ok(Math.abs((wallA-wallB)-10800000)<5000,
                  'actual application wall clocks must differ by approximately three hours');
      }
    } else {
      assert.equal(resultA.success,false,'broken audio or wrong key must never succeed');
      assert.equal(resultA.receiptVerified,false);
      if(config.cancelAfter) {
        assert.equal(resultA.reason,'cancelled');
        assert.equal(resultB.reason,'cancelled');
      }
    }
    const retries=[...ar,...br].filter(r=>r.event==='retry').length;
    if(config.name==='drop-first-response-retry')assert.ok(retries>0,'dropped response must exercise retry');
    results.push({name:config.name,status:'passed',expectedSuccess:config.expect,
                  parameters:{...config,wrongKey:!!config.wrongKey},
                  initiator:resultA,responder:resultB,retryEvents:retries,
                  causalReceivedA:ar.filter(r=>r.event==='transition').map(r=>r.received),
                  causalReceivedB:br.filter(r=>r.event==='transition').map(r=>r.received),
                  initiatorReadyWallTime:ar.find(r=>r.event==='ready')?.wallTime,
                  responderReadyWallTime:br.find(r=>r.event==='ready')?.wallTime,
                  localRoundTrip:ar.find(r=>r.event==='handshake-rtt')});
    console.log(JSON.stringify({case:config.name,status:'passed',retryEvents:retries}));
  } catch(error) {
    results.push({name:config.name,status:'failed',reason:error.message,
                  recentLogs:processes.flatMap(p=>p.rows().slice(-3))});
    console.log(JSON.stringify({case:config.name,status:'failed',reason:error.message}));
  } finally {
    clearTimeout(cancelTimer);
    for(const p of processes)if(p.child.exitCode===null&&p.child.signalCode===null)p.child.kill('SIGTERM');
    await Promise.all(processes.map(p=>boundedExit(p,3000).catch(()=>p.child.kill('SIGKILL'))));
    await rm(scratch,{recursive:true,force:true});
  }
  await mkdir(resolve(out,'..'),{recursive:true});
  await writeFile(out,JSON.stringify({scope:'Actual independent Node processes and UDP PCM; simulation parameters are not measured carrier properties',
                        cases:results},null,2)+'\n');
}
const fingerprints=results.filter(r=>r.status==='passed'&&r.expectedSuccess).map(r=>r.initiator.sessionFingerprint);
assert.equal(new Set(fingerprints).size,fingerprints.length,'fresh sessions must have distinct nonces');
process.exitCode=results.every(r=>r.status==='passed')?0:1;
