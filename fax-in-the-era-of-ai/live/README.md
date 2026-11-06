# Live, tones-only audio protocol

Two independently running **Node.js 24** programs exchange actual PCM audio,
recover binary packets from received samples, authenticate a fresh session,
and perform a user-selected data round trip. No speech, LLM, STT/TTS, browser,
telephone call, HTTP rendezvous, prerecorded whole-call WAV, or hidden payload
channel is involved. The optional third program only impairs/forwards PCM.

This supersedes the [offline research sample](../prototype/README.md) as the
implementation prototype. The research sample remains useful signal research;
its simulated HTTP handoff is **not** what this application does.

## Listen to an actual live exchange

[15.94-second MP3](evidence/live-exchange-2026-11-06.mp3) ·
[original stereo PCM WAV](evidence/live-exchange-2026-11-06.wav) ·
[blindly decoded seven frames](evidence/live-exchange-decoded.json) ·
[provenance and actual endpoint results](evidence/live-exchange-manifest.json).

This audio was captured from the actual three independent programs during a
successful causal run. No spoken dialogue or fake success cue. Left channel is
initiator→responder; right channel is responder→initiator. Both sides verified
the session; the responder executed one protected echo operation. The sample
is an initial smoke, not a substitute for the finalized clock/fault matrix.

## Run it: three terminals

Requires **Node 24.x only**; no npm packages, build step, Python, GPU or root.
From this directory:

```sh
node --version
node src/cli.mjs init --state .state
npm test
```

Initialization creates a fresh 32-byte random key in `.state/pair.key`, mode
0600, inside a mode-0700 ignored directory. It refuses to overwrite an existing
key. Provision that same key to the two trusted parties over a separate trusted
channel. This is one-user pairing, not public identity discovery.

Terminal 1 — PCM-only link, with mild synthetic noise/echo, optional real capture:

```sh
node src/cli.mjs link \
  --bind 127.0.0.1:31000 \
  --a 127.0.0.1:31001 --b 127.0.0.1:31002 \
  --noise-db 24 --echo 0.10 --seed 12345 \
  --duration-ms 120000 --capture .state/live-exchange.wav \
  --log .state/link.jsonl
```

Terminal 2 — responder:

```sh
node src/cli.mjs endpoint --role responder \
  --key .state/pair.key --bind 127.0.0.1:31002 \
  --peer 127.0.0.1:31000 --log .state/responder.jsonl
```

Terminal 3 — initiator, **your own data**, at most 64 UTF-8 bytes:

```sh
node src/cli.mjs endpoint --role initiator \
  --key .state/pair.key --bind 127.0.0.1:31001 \
  --peer 127.0.0.1:31000 --data 'check capability: repair-scheduling' \
  --log .state/initiator.jsonl
```

Success means initiator's `result.success=true` **and** `receiptVerified=true`,
and responder's `result.success=true` **and** `operationCount=1`. The initiator
verified that the returned authenticated receipt contains precisely its actual
requested bytes and their digest. It cannot succeed just because playback ended.
The responder decoded and authenticated CONFIRM before opening the data action.

Each endpoint handles **one bounded session**, then exits (0 success, 2 failure).
Run a fresh responder and initiator for another session; no daemon manager or
zombie process is required. Stop the optional link with Ctrl-C after both have
finished: that finalizes its WAV. Endpoints clean up socket, timer and DSP worker
on Ctrl-C, SIGTERM, timeout or success. Logs are JSONL on stderr and optionally a
file; no PCM goes through console output.

### Direct audio transport, no relay

For an unimpaired test, point the responder's `--peer` at `127.0.0.1:31001` and
the initiator's at `127.0.0.1:31002`; omit the link. Across two machines, configure
reachable private IPv4 addresses and ports. UDP transport carries only PCM plus
sequence/sample counters, not protocol messages. It is not an exposed production
network service. The preprovisioned PSK authenticates **audio frames**, not the
underlying UDP source or network confidentiality.

## Clocks, delay, jitter and faults

The endpoint flags are independent:

- `--wall-offset-ms 3600000`: app reports a clock one hour ahead. Opposite
  endpoint can use `-7200000`. Deadlines still use local monotonic elapsed time.
- `--sample-ppm 200`: a **faster** local audio oscillator, applied to both DAC
  synthesis and ADC resampling. Use `-200` on the other endpoint. Carrier and
  baud really change; the DSP receiver is not given the peer's ppm value.
- `--jitter-ms 200`: bounded initial/local playout buffer. Missing PCM becomes
  silence, late packets are discarded, and counters report these separately.
- `--retry-ms 7000 --retries 4 --timeout-ms 90000`: per-phase retry interval,
  maximum retries per phase, and absolute local session lifetime. `totalRetries`
  counts the whole session, while `retries` is the current phase's count.

For the link, add:

```sh
--a-delay-ms 300 --b-delay-ms 650 --jitter-ms 60 --seed 12345
```

`a` is initiator→responder, `b` is responder→initiator. Those are **configured
simulation delays**, not measured telephone latency. Each datagram is actually
queued for an independently jittered delay; no remote clock is consulted.
RTT is measured at the initiator with its own monotonic clock, including audio
burst duration, buffering, guards and decoding. Do not call RTT/2 a measured
one-way delay on these asymmetric paths.

Additional faults (only the relay sees them):

- `--loss 0.01`: randomly discard 1% of PCM packets. There is no FEC: loss inside
  a burst can invalidate its CRC and require ARQ; this is not a guaranteed pass.
- `--drop-b-burst 1`: mute the first **audio-active burst** from responder,
  without decoding its type. In the usual exchange this loses CHALLENGE.
- `--drop-b-burst 2`: lose READY; initiator must not succeed without a later
  decoded peer acknowledgement.
- `--mute b` or `--corrupt b`: remove **all** responder modulation. Pairing must
  fail. A different private key at either endpoint must also fail.
- `--noise-db 24 --echo 0.10`: nominal hiss SNR relative to 0.24 RMS tone and a
  50 ms echo. Gentle causal high/lowpass coloration is not a measured carrier
  channel, exact telephone-band filter, G.711/Opus codec, or acoustic echo model.

`--seed` controls independent per-direction noncryptographic impairment streams.
It never controls keys/nonces, which always use OS cryptographic randomness.
Packet scheduling between processes is not deterministic; identical seeds do
not promise byte-identical captures under arbitrary OS scheduling.

## Docker: two endpoint containers plus a dumb audio link

The image is pinned by digest; no dependencies download during the build. Both
endpoints are isolated processes with separate waveform/DSP/clock state. Docker
itself shares the host clock; injected wall/audio clocks create the intended
differences. No SYS_TIME/NET_ADMIN capabilities, host time changes or published
ports. A third small container is only the PCM fault network, not a third agent.

```sh
node src/cli.mjs init --state .state  # only once; skip if already provisioned
export LOCAL_UID="$(id -u)" LOCAL_GID="$(id -g)"
docker compose up --build -d
# Wait for BOTH endpoints: stopping on initiator exit can truncate the delayed
# final CLOSE still travelling to the responder.
docker compose wait initiator responder
docker compose logs --no-color initiator responder
docker compose down
```

Compose injects +1 h/−2 h app clocks, +200/−200 ppm audio clocks, asymmetric
300/650 ms delay, 60 ms jitter and 24 dB nominal hiss. The key directory is mounted
read-only; the ignored directory and your UID preserve private key permissions.
The bridge network is internal. Do not run multiple Compose projects with the
same directory/name unless you understand their independent state.

## What travels through the sounds

```text
Initiator                              Responder
 HELLO(session/nonceA, MAC) --------audio---->
                    <----audio---- CHALLENGE(nonceB, MAC)
 CONFIRM(session-key MAC) -----------audio---->
                    <----audio---- READY(session-key MAC)
 DATA(your bytes, MAC) --------------audio---->
                    <----audio---- RECEIPT(digest + same bytes, MAC)
 CLOSE(MAC) ------------------------audio---->
```

All arrows contain modulated PCM, never out-of-band structured messages.
Fresh nonce A is also the 128-bit session identifier. A fresh 128-bit nonce B
and A salt HKDF-SHA256 with the privately shared 256-bit key. Protocol type,
sequence, session and payload are authenticated with a domain/role-separated
128-bit HMAC-SHA256 tag. Checksums catch channel errors; only the MAC establishes
membership in this single-user key domain. PSK peers are symmetric: this is not
a public signature or nonrepudiable receipt. **Payloads are not encrypted.**

`DATA` is a real but deliberately small idempotent echo operation, not booking.
It is only dispatched after audio-confirmed pairing. A duplicate authenticated
DATA frame returns the exact cached response without another operation. Bad
phase, wrong session, tampering, wrong key and stale-session replays do not open
that operation. Authenticated HELLO/CONFIRM retries reuse their cached responses.

## Physical framing and mathematical limits

The new **experimental AIP-FSK2** profile is not CP, V.21 or T.30 compatible.
It uses continuous-phase binary FSK, mark 1250 Hz, space 2250 Hz, 250 bit/s,
8 kHz mono s16le PCM. No artificial decorative dial-up sounds are added.

- 48 alternating preamble bits + 32-bit sync `ddaa96e7`.
- Version byte `02`, one-byte length (1…192), binary data, CRC16 big-endian.
- CRC16/CCITT-FALSE: polynomial `1021`, initial `ffff`, no reflection/xorout.
- At nominal 32 samples/bit, tones have 5 and 9 cycles. `Δf*T=4`; integer-cycle
  orthogonality motivates the nominal complex matched-correlator detector.
- Receiver blindly searches 32 sample phases × 25 symbol-period hypotheses
  spanning ±3000 ppm in 250 ppm steps and reacquires each bounded packet. This
  is a finite clock bank, not a general tracking PLL or arbitrary-skew promise.
- 8 seconds max sample history (64,000 samples), 160 ms analysis cadence; DSP
  runs in a worker so packet acquisition does not block the 20 ms audio pacer.
- Candidate body symbols must exceed a relative energy/erasure gate; near-zero
  floating-point correlator signs are not accepted as evidence of a real bit.
  `crcRejections`/`erasureRejections` count timing candidates, not lost packets.
- Bounded worker queue (128 chunks), TX frame queue (4), receive jitter queue
  (128 packets), relay pending delays (1024), local lifetime (at most 300 s).
  Overflow is reported/fails rather than growing forever.

At +200/−200 ppm hardware clocks, relative frequency error is approximately
+400.08 ppm in one direction. TX alters both carrier and baud; RX uses its own
persistent fractional linear ADC resampler. Decoder reports a selected **period**
hypothesis, not a calibrated ppm measurement. Each clock injector accepts ±2500
ppm, but opposed extremes can exceed the bank’s ±3000 ppm relative-period span;
accepted simulator settings are not a promise of successful recovery. See the
[clock/link review](../notes/2026-11-06-clock-and-link-review.md).

Physical packet duration before padding is `(112 + 8*payloadBytes)/250` seconds.
A minimal 35-byte authenticated HELLO thus needs about 1.568 s, plus release/
chunk padding and guards. This is intentionally conservative, not a claim of
optimal modem speed or secure-latency lower bound. Authentication overhead,
noise robustness and actual bit rate are exposed rather than disguised.

## Code, tests and evidence

- `src/signal.mjs`: actual waveform generator and bounded streaming acquisition.
- `src/protocol.mjs`: pure authenticated causal session/operation state machine.
- `src/transport.mjs`: PCM adapter, sequence/jitter handling and ADC clock model.
- `src/endpoint.mjs`: real-time scheduler, independent DSP worker and lifecycle.
- `src/link.mjs`: optional protocol-blind impairment relay and live WAV capture.
- `tests/`: waveform, independent ADC drift, crypto/phase/replay and bound tests.
- `validation/`: independent parent-owned process/clock verification.

A link capture is stereo actual **delivery-time PCM**: left a→b, right b→a.
With jitter, arrivals can overlap/gap; it is not falsely labelled reconstructed
receiver playout. The decoder receives each endpoint's local jitter-corrected
stream. WAVs contain short-lived nonces and public authenticated frames, never
the private key. Captured audio is research evidence, not a secret credential.
JSON evidence/logs omit nonces, keys, raw packets and user data.

[Implementation plan](../notes/2026-11-06-live-prototype-plan.md) ·
[Erasure-confidence development finding and correction](../notes/2026-11-06-signal-hardening.md).
No real acoustic hardware, telephone carrier, browser or hostile network has
been qualified. One run is not a reliability percentage. Retain failures and
reproduction settings when analyzing the matrix.
