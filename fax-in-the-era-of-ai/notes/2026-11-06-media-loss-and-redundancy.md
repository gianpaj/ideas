# Actual UDP loss failure and bounded transport correction

## Observed failure, not a claimed success

The first six finalized independent-process scenarios and the isolated Docker
clock/delay case passed on the hardened decoder. A new predetermined stress
case used seed `20261106`, 1% independent UDP PCM packet loss, 20 ms jitter,
5 s retries and up to six retries per phase. It failed after roughly 109 s in
`WAIT_RECEIPT` with retry exhaustion. This evidence must remain in the research
record; the earlier six passes do not establish 1% packet-loss robustness.

The application authenticates complete modem packets, not partially guessed
messages. At 250 bit/s a long authenticated receipt occupies over 100 media
chunks. Even independent 1% loss can erase such a burst often. For a frame with
`N` chunks and chunk-erasure probability `p`, an idealized no-erasure chance is
`(1-p)^N`; at `N=200,p=.01`, this is about 13.4%. CRC/confidence rejection and
bounded ARQ are correct behavior, but this is a weak practical UDP default.

## Smallest deployment-focused correction

Default to **two identical UDP media datagrams** for each 20 ms PCM block,
with `--redundancy 1` available for raw/unprotected testing. Copies have exactly
the same 12-byte transport header and 320 bytes of PCM. No protocol fields,
nonce, challenge, expected data or success condition were added to metadata.
The modem waveform, physical frame, crypto and protocol machine are unchanged.

The receiver deduplicates by media sequence before queueing/planning playout,
and retains 256 recent sequence identifiers to recognize late copies. Unique
chunks advance the audio sample stream once. It reports logical media blocks,
network datagrams, duplicates, late duplicates, loss and bounds separately.

The relay must not apply its stateful channel twice to the same physical samples.
It caches 256 unique blocks per direction: coloring, hiss, 50 ms echo and active-
burst counting advance once per unique input. This happens even if all network
copies are later lost. Independent delay/jitter/loss then acts on each copy.
Stale evicted sequences and conflicting reuse of a sequence are rejected.
The first delivered copy is recorded once, avoiding artificial doubled volume.

Under **independent** copy losses the residual media-erasure probability becomes
`p²`. The same idealized `N=200,p=.01` frame then has no-erasure probability
`(1-.0001)^200≈98.0%`, before considering timing, noise, correlation and ARQ.
This is a mathematical model, **not a measured success percentage**. Immediate
copies share the same real path and can be lost together during a burst.

## Acceptance and limits

Meaningful regressions use actual UDP to prove identical copies retain one
sequence/sample position and are played only once, including a late duplicate.
Another test uses observable stateful processing to prove the relay does not
advance its channel twice, and checks bounded cache/stale/conflicting copies.

The independent parent runner must repeat the originally failing seeded loss
case, original six scenarios and Docker clock case on the corrected code.
Report actual outcomes separately. A successful selected seed does not prove
universal 1% reliability or any carrier/audio-modem FEC claim. This correction
helps the **packet transport**, not erased sound inside a real phone codec,
correlated outage, hardware dropout, hostile network or all-return mute.
