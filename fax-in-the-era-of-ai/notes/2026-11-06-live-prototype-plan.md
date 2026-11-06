# Live prototype — intent, design and implementation plan

2026-11-06. The previous artifact had real encoders/decoders but rendered a
scenario with simulated HTTP success. The user clarified: **build two real
headless audio-I/O parties**, no browser, telephone call, or speech. The user
suggested Node/Go and separate containers, explicitly including independent
computer clocks and international-call-like delay. The protocol itself and a
small useful data operation must be carried through audio, not a hidden HTTP
channel. This supersedes the initial HTTP/DTMF plan written earlier today.

## Selected architecture

`live/` is a dependency-free Node.js 24 ESM package, separate from prior research
and the running local voice app. Two endpoint programs each have their own
UDP socket, PCM generator, decoder worker, clock model and protocol machine.
An optional third PCM-only relay adds actual queued propagation delay, jitter,
loss, noise and echo; it has no key and imports no protocol parser.

Audio is mono 8 kHz s16le in 20 ms chunks. UDP includes only a 12-byte transport
header (magic, independent sequence and sample-position counters). A bounded
local jitter buffer reconstructs the stream and inserts silence on losses.
Protocol payloads are **only transmitted by modulation into PCM**, never by
JSON, socket metadata, shared in-memory state or prewritten exchange timelines.

### Physical layer: experimental AIP-FSK2

250-baud CPFSK, mark 1250/space 2250 Hz. At 32 samples/bit these are 5 and 9 cycles;
`Δf*T=4`, so the complex tones are orthogonal at ideal timing. Each packet has
48 alternating preamble bits, 32-bit sync, version 2/length, binary protocol data,
and CRC16/CCITT-FALSE. Max 192 physical payload bytes and 8 s RX history bound all
acquisition state. Blind 32-sample-phase × 25-clock-rate hypotheses span ±3000 ppm
symbol-period error in 250 ppm steps; packet reacquisition happens independently.
This is bounded clock-bank acquisition, **not** an unrestricted tracking PLL.

### Protocol: authenticated session, then actual data echo

- HELLO: fresh random 128-bit initiator nonce/session identifier, HMAC.
- CHALLENGE: fresh random 128-bit responder nonce, echoing session, HMAC.
- Both derive a session key with HKDF-SHA256 over privately provisioned 32-byte
  PSK and the two nonces; role/domain-separated 128-bit HMAC tags protect frames.
- CONFIRM → READY: initiator cannot claim pairing after merely sending CONFIRM;
  it must decode and verify READY, proving responder actually received it.
- DATA → RECEIPT: actual user-selected bytes (max 64 UTF-8 bytes), authenticated
  echo plus request digest. Operation executes once; duplicate data yields the
  cached receipt. CLOSE is also audio. No booking/calendar/model/API fiction.

Local monotonic deadlines and bounded retries expire failed sessions. Phase,
sequence, fresh nonces and authentication gate state transitions. Cached
challenges avoid duplicate-HELLO liveness bugs. Old-session/tampered/wrong-key
frames cannot complete a fresh handshake. PSK provisioning is an explicit
single-user trust model, **not** identity discovery, public enrollment, CP
mandates, encryption or a production security certification.

## Clock semantics and transport limits

`--wall-offset-ms` changes the app's reported time but never protocol elapsed
checks. `--sample-ppm` means a **faster sample clock when positive**: TX alters
both baud and carrier, and RX independently resamples incoming PCM with a
persistent fractional ADC clock. No endpoint is told the peer's clock value.
At A +200 ppm/B −200 ppm relative frequency error is +400.08 ppm A→B. Decoder
reports its selected **symbol-period** hypothesis, opposite frequency-error sign.
Wall-clock offsets, sample clocks, network delay and jitter are separate.

Containerization does not inherently create clock error; Compose injects it
explicitly. No SYS_TIME/NET_ADMIN/host changes, carrier account or public service.
Transport is a controlled PCM laboratory link, not an acoustic device driver,
telephony stack or RTP/codec/carrier qualification. Direct UDP works without relay;
future adapters must preserve the PCM-I/O contract rather than bypass decoding.

## Implementation chunks and acceptance

1. Node package, causal FSK DSP, authenticated state machine, PCM transport,
   independent ADC/TX clocks, paced live endpoints and bounded fault relay.
2. Real CLI/Docker reproduction and usage/deployment docs; waveform-level tests,
   causal session/security/duplicate tests, loss/noise/truncation/buffer checks.
3. Parent independently runs separate-process matrix, clock-waveform review and
   container validation; record metadata and actual causal audio captures.

Two fresh sessions must have distinct nonces/session fingerprints and verified
arbitrary data receipts. Wrong PSK or muted return must fail. A dropped first
burst/READY must recover by retries. Asymmetric 300/650 ms delay, 60 ms jitter and
independent ±200 ppm oscillators are tested, not assumed. Cancellation followed
by a fresh run must leave no workers/sockets/timers. Noise/loss beyond measured
conditions may fail; do not promote simulation results to carrier guarantees.
