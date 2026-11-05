# Research notebook: when two agents meet on a telephone call

Date: 2026-11-05. Scope: a reproducible, audible research prototype, not a new production telephony subsystem. The user asked for first-principles reasoning, alternative ideas, mathematical care, and a realistic noisy audio implementation of the [idea](../README.md), informed by the separate `gian.cool/research/fax-history` research.

## 1. Design brief and first-principles decomposition

We need two agents that have already reached each other by telephone to discover a shared machine interface, locate it, and tie the resulting data session to that particular call. We do **not** necessarily need to move the booking itself through the voice channel.

These are different tasks:

1. **Discovery:** is the other party protocol-capable, rather than human?
2. **Rendezvous:** which endpoint and short-lived session does this call mean?
3. **Authentication:** do I trust that business/operator/key and its authorization?
4. **Call binding:** can the party that accepted over HTTPS return a fresh challenge on this particular media leg?
5. **Transaction:** structured availability/hold/book operations and a verifiable receipt.

Tones alone do not solve all five. A good design assigns only the first two and a small part of the fourth to the constrained phone channel. Keep identity, authorization, large payloads, and transactional guarantees on an authenticated data channel. Discovery is not authentication, and a checksum is not a signature.

Assumptions for this experiment: both agents have internet access; the number has already answered; the caller discloses it is an AI; the receiver can observe in-band audio; only 12-key DTMF is assumed. The final production transport may instead expose DTMF events. No real person, call, or booking is involved in the samples.

## 2. The candidates

| Candidate | What travels over audio | Benefit | Core difficulty | Decision |
| --- | --- | --- | --- | --- |
| **12-key DTMF rendezvous + HTTPS** | Small version/type/code/checksum frames and returned challenge | Familiar telephony primitive; may be delivered as native DTMF events; exact existing experimental CP framing | Several seconds of keypad-like tones; events vs waveform differ; registry/trust/session design remains necessary | **Implement this first** |
| **Narrowband 2-FSK, V.21-inspired** | Binary sync, version/capabilities, nonce/locator, CRC; optionally a whole transaction | Truly fax-like warble; hundreds of raw bits/s in the voice band; no HTTPS required in principle | Need timing acquisition, framing, CRC/retries, real codec/echo testing, and authentication; no automatic carrier support | Also implemented as a short audible comparator, not interchangeable with CP |
| **ggwave / GibberLink** | Library-framed data over multi-tone audio | Existing error correction and a working agent demo | Default audible ggwave frequency profile occupies about 4.5 kHz and reaches ~6.33 kHz: not a narrowband-PSTN drop-in | Useful on controlled full-band audio; retuning requires actual new tests |
| **Native SIP/data metadata only** | No audio; endpoint/capability in signaling | Fast and quiet on controlled paths | Intermediaries can strip it; does not cover arbitrary PSTN legs | Optional fast path, retain a fallback |

### Why not simply sound like a fax?

Fax did not choose its sound aesthetically. CNG/CED classify the endpoint; the control modem negotiates capabilities; training checks whether a chosen fast data mode survives; the page modem then carries bulk data. We should copy that *division of responsibilities*, not blindly copy every signal.

An 1100 Hz fax calling tone or a long 2100 Hz answer tone can invite fax routing, echo-control changes, or other legacy handling. These are not harmless new “AI identifiers.” This sample emits **neither**. A modern agent with HTTPS does not need a page modem merely to discover a 10-digit rendezvous.

Important nuance: even “300 baud FSK” is not sufficient to claim V.21 conformance. V.21 has defined frequencies/channel behavior, and T.30 adds HDLC, identification/control frames, timing, fallback, and other state. A home-made binary packet is a new experimental profile, even if it uses the familiar 1650/1850 Hz pair.

### Why ggwave needs qualification

The official ggwave technical section gives `F0=1875 Hz`, `dF=46.875 Hz`, and 96 frequency slots for its example audible profile. Thus its highest slot is

`1875 + 95 × 46.875 = 6328.125 Hz`.

The occupied slot span is 4453.125 Hz (~4.5 kHz), beyond a conventional ~300–3400 Hz narrowband phone path. Resampling that waveform to 8 kHz is not enough: anti-alias filtering necessarily removes content above 4 kHz, and the phone band removes more. ggwave can be useful with other profiles or controlled wideband media, but the default demo's success over laptop speakers says little about PSTN transcoding. This was an analytical comparison, not a ggwave benchmark.

## 3. Exact frame choice: CP-Handshake draft v0.1

Read both the upstream draft and its TypeScript encoder/decoder, pinned to commit `a965c167faa59bc52738b90dee6d57b8a68cd864`. Upstream labels the draft experimental, not production-ready. The audio prototype matches its **in-band frame syntax and nominal tone/gap profile**; it is not a complete CP implementation.

```text
frame = "*#" + type + payload + Luhn(type + payload) + "#"

Caller   PROBE = *#26#                 (5 symbols)
Business OFFER = *#1048151623426#      (16 symbols)
Caller   BIND  = *#32718280#           (11 symbols)
```

The OFFER means type `1`, local test registry `0`, rendezvous code `4815162342`, Luhn check `6`. The BIND means type `3`, challenge `271828`, check `0`. All values are fictional deterministic test fixtures. Luhn is computed over the type and decimal payload, not over `*#` or the final `#`.

Only the 12 keys `0–9`, `*`, and `#` are used; no A–D keys. The DTMF row frequencies are `697, 770, 852, 941 Hz`; columns are `1209, 1336, 1477 Hz`. Each symbol is the sum of one row and one column sinusoid. Although classic DTMF also defines a fourth 1633 Hz column, the restricted profile avoids relying on telephony APIs supporting its A–D keys.

### Timeline actually heard

The full sample is **23.750 s**. The voices are local synthetic Flite voices, not recordings of people.

| Time (s) | Party | What happens |
| --- | --- | --- |
| 0.000–0.350 | Channel | Already answered; short quiet interval, not dial tone |
| 0.350 onward | Business | Greets and discloses automated receptionist |
| Before 9.855 | Caller | Discloses AI agency and asks to connect directly |
| 9.855–10.555 | Caller | PROBE `*#26#` |
| 10.775 onward | Business | “Agent connect is available on this line.” |
| 13.665–15.905 | Business | OFFER `*#1048151623426#` |
| 15.905–16.555 | Silent data-channel placeholder | **Simulated**, not measured: resolve/verify/accept and receive bind challenge |
| 16.555–18.095 | Caller | BIND `*#32718280#` |
| 18.315 onward | Business | Says this is a demonstration and no booking was made |

The [saved timeline](../prototype/results/timeline.json) has the complete generation schedule. The [WAV decoder result](../prototype/results/call-phone-noise-decoded.json) gives independently observed digit/frame times; those are window-center estimates rather than a copy of the schedule.

### Timing and information budget

With an 80 ms tone and a 60 ms gap, one cell takes 140 ms:

`symbol rate = 1 / 0.140 = 7.142857 symbols/s`.

| Quantity | Result | Interpretation |
| --- | --- | --- |
| PROBE | `5 × .14 = .70 s` | Includes its trailing gap |
| OFFER | `16 × .14 = 2.24 s` | The often-cited “about two seconds” is **only OFFER** |
| BIND | `11 × .14 = 1.54 s` | Includes its trailing gap |
| All three complete cell budgets | **4.48 s** | `32 × .14`; excludes voice and internet round trips |
| Sum of first-tone to last-tone spans | **4.30 s** | Omits three final 60 ms gaps |
| Total actual tone-on time | **2.56 s** | `32 × .080`; not overall elapsed time |
| 12-key alphabet bound | `log2(12) = 3.585 bits/symbol` | At most ~25.61 raw bits/s at this cadence |
| Decimal payload symbol | `log2(10) = 3.322 bits` | A hypothetical 16-key alphabet would give 4 bits/symbol, not this profile |
| 10-digit rendezvous | **33.219 bits** | Only if chosen independently and uniformly |
| 6-digit bind challenge | **19.932 bits** | Only if uniform, fresh, and rate-limited |

The check digit provides **zero secret entropy**. It costs one whole cell per frame. It catches common accidental digit errors but not intentional forgery, and it is not a CRC or cryptographic MAC. A random alteration that still has the right syntax/length has roughly a 1/10 chance of passing Luhn under a uniform-error model; speech-triggered false positives are not uniformly random digits.

More throughput is technically possible, but the rendezvous path is dominated by discovery latency and round trips, not bulk payload bandwidth. Compressing a few dozen bits while retaining human disclosure and network validation does not justify immediately building a modem.

### Channel capacity is not a codec guarantee

For an ideal additive white Gaussian noise channel, Shannon's bound is

`C = B log2(1 + S/N)`.

At `B = 3100 Hz` and `S/N = 100` (20 dB), this is ~20.64 kbit/s. Our ~25.6 bit/s DTMF alphabet bound is tiny relative to that *idealized* capacity. There is no contradiction: DTMF buys legacy interoperability and conservative symbol detection, not spectral efficiency.

The Shannon calculation does **not** imply that a low-rate speech codec preserves modem tones. Voice activity detection, echo cancellation, nonlinear denoising, transcoding, comfort noise, packet-loss concealment, and event extraction can violate the AWGN assumptions. RFC 4733 exists partly because voice encoding cannot guarantee faithful DTMF waveforms.

For the 300 baud 1650/1850 Hz FSK idea, `T = 1/300 s` and `Δf × T = 200/300 = 2/3`. Do **not** apply the textbook orthogonal noncoherent BFSK BER expression as though these tones were orthogonal over a single symbol. A real receiver needs properly designed demodulation/timing and measured error results.

## 4. Pairing, trust, and attacks

The signed rendezvous record must be verified with an independently trusted registry key, must be unexpired, and must match the **originally dialed E.164 number**, not a number merely spoken on the call. The 10-digit code only locates the record. It does not authenticate it.

The expected flow is:

1. Resolve OFFER over HTTPS and validate the signed record, number, endpoint policy, and expiry.
2. Caller proves possession of its agent key and presents an appropriately scoped mandate; business validates both. **Not implemented in this prototype.**
3. Business returns a fresh 6-digit challenge over that authenticated data session, scoped to this call/session, with a short deadline.
4. Caller emits BIND on the same phone media leg. Business rejects state changes until the expected challenge is received on the expected call.
5. Consume/revoke the session as appropriate; do not allow replay, unlimited guesses, or silent reassociation to a different call.

This proves a limited statement under assumptions: the data-session party can cause the fresh challenge to appear on that media leg. It does **not** prove human identity, user consent, ownership of a phone number, or protection against an active media relay, conferencing adversary, compromised carrier, or attacker able to both observe/inject on the call and race the data channel. It can also be susceptible to denial of service through early acceptance if reservation/recovery policy is weak. Do not repeat upstream's “prevents impersonation” prose as an unconditional security proof; formal channel-binding analysis is still listed as an open issue upstream.

### Guessing and collision math

For a uniform 6-digit challenge and at most three independent online guesses, success is at most approximately `3/10^6 = 3×10^-6` **per targeted session**. This is not a global abuse bound: many sessions, weak randomness, missing rate limits, or challenge reuse change it. The challenge must not be derived from caller ID or a timestamp.

A targeted uniform 10-digit rendezvous guess has probability `1/10^10`; guessing *any* of `N` active sessions is approximately `N/10^10` per attempt when occupancy is small. For `N` independently sampled codes, the pre-deduplication collision approximation is `N(N−1)/(2×10^10)`. At `N=10,000`, that is ~0.005 (~0.5% chance of at least one collision via the birthday approximation). The registry should enforce uniqueness among active sessions and regenerate on collision. A large-looking decimal code is not a reason to omit rate limits or collision handling.

The script includes a pinned-key Ed25519/JWS subset and illustrative call-scoped BIND gate. Tests reject signature tampering, expiry, the wrong dialed number, the wrong challenge, the wrong call, and replay. **These are offline unit-like fixture checks**, not a deployed authentication system. The demonstration key's seed is intentionally public and deterministic; no real credential is stored.

The upstream timing policy includes an 8 s OFFER→accept fallback and a bind deadline no more than 15 s after accept, plus revocation after three wrong codes. The sample's 650 ms placeholder fits those budgets, but the prototype does **not** implement the complete deadline/retry/fallback state machine or claim to measure internet latency. If decoding fails in a deployed system, return to normal voice rather than drop the call.

## 5. Noise model and receiver

The “phone noise” sample is synthetic, not an actual telephone recording:

- Mono 8 kHz PCM, 16-bit delivery WAV.
- Causal fifth-order Butterworth bandpass, 300–3400 Hz.
- One delayed echo copy: 50 ms delay, amplitude 0.12 (~−18.4 dB relative to the direct signal), not a feedback comb of endless echoes.
- Bandlimited Gaussian hiss at **20 dB relative to active-signal RMS**, measured before companding. The active mask is `abs(filtered audio) > .015`; this is a defined synthetic reference, not a carrier SNR measurement.
- Receive-side 60 Hz hum at −43 dBFS peak, added *after* the channel filter to mimic local electrical pickup. Consequently the final file is not mathematically confined to 300–3400 Hz.
- Real FFmpeg G.711 μ-law encode/decode quantization, implemented as a reusable lookup over every possible signed 16-bit PCM input value. The resulting WAV is decoded PCM, not an 8-bit μ-law container.
- MP3 is only a convenience listening format, not part of the proposed protocol. Both delivered MP3s were decoded back to PCM and successfully parsed.

The research detector analyzes 30 ms Hann windows every 5 ms and measures spectral power at the seven nominal row/column frequencies. It requires row and column dominance, balanced-enough power (“twist”), concentration in the candidate pair, and stable dwell time; then it scans for the prefix/type/length/checksum. It never receives the generation schedule.

An early run exposed a real receiver bug: the weak echo extended a digit into the silent gap, causing the receiver's release logic to swallow the next digit. The fix was **signal-based**, not timeline-based: reject windows below 16% of the local 125 ms peak power, and apply repeated-digit release logic only to repeated digits. This relative threshold corresponds to about −8 dB amplitude relative to the local peak and rejects the −18.4 dB echo tail. It trades tolerance of abrupt level changes for echo robustness; it is documented and measured rather than presented as a general solution to echo cancellation.

Adjacent DTMF rows are only 73 Hz apart at the closest pair; a 30 ms analysis window has a scale `1/T ≈ 33.3 Hz`. That is enough separation for this nominal-frequency experiment, but it leaves limited frequency-offset margin with the conservative gates. A production receiver needs a qualified frequency-search/tolerance and talk-off design, not just more optimistic thresholds.

## 6. What the tests actually show

The delivered full call, clean WAV, noisy WAV, noisy tones-only WAV, and both noisy MP3s all recover the exact sequence:

`*#26#` → `*#1048151623426#` → `*#32718280#`.

The script performs **159 synthetic trials**, varying one impairment at a time while holding the others fixed. Random seeds are logged; shared seeds/fixtures mean we do not assume these are statistically independent observations. The detector was developed against the nominal 20 dB/50 ms echo fixture, then held fixed throughout the reported sweep. Success means **all three frames, in order, exact payloads**, not merely “some tones detected.”

| Sweep | Result | Honest interpretation |
| --- | --- | --- |
| SNR 30, 24, 20, 16, 12, 8 dB | 10/10 complete sequences at **each** point | Works across these synthetic seeded noise conditions |
| SNR 4, 0, −4 dB | 0/10 complete sequences at each point | Clear failure region; no universal SNR threshold claimed |
| High-vs-low tone power twist −6, −3, 0, +3, +6 dB | 3/3 at each point | Tolerates those tested imbalance values |
| Twist ±8, ±10 dB | 0/3 at each point | Conservative detector gate intentionally rejects them |
| Common frequency shift −1%, 0, +1% | 3/3 at each point | Limited nominal-frequency tolerance |
| Common shift ±1.5%, ±2%, ±3% | 0/3 at each point | **Not a Q.24-compliant receiver claim** |
| One OFFER-digit erasure 10, 20, 40 ms | 3/3 at each point | Enough usable dwell remains under this exact model |
| Erasure 60, 80 ms | 0/3 at each point | Whole-frame retry/fallback would be needed |

Negative controls: **365.6 s total**, comprising 120 s synthetic speech from two Flite voices, 120 s noise, 120 s fax/call-progress single tones, and 5.6 s unframed DTMF plus a corrupted checksum. **Zero accepted protocol frames.** The unframed control correctly still produces detected *digits*: the protocol parser must reject them. This is a small closed-set synthetic check, **not** a real-human talk-off estimate or a claim of a particular false-positive probability.

The Monte Carlo denominator is deliberately small. A 10/10 result is encouraging evidence for that fixed test design, not a claim of 100% reliability. Conditions are not independent samples of the real telephone network, and no speech codec, mobile carrier, packet network, AGC, or RFC 4733 implementation was exercised.

### The fax-like alternative: also genuinely decoded

To let us hear the alternative rather than only describe it, `prototype/fsk_comparator.py` implements a deliberately new experimental profile called **AIP-FSK1**. The [noisy MP3](../assets/phone-handshake-2026-11-05/fsk-experimental-phone-noise.mp3) lasts **3.833375 s** and carries the same three CP ASCII frame strings in caller/business/caller order, with half-second turn-taking gaps. The [WAV](../assets/phone-handshake-2026-11-05/fsk-experimental-phone-noise.wav), [decoder evidence](../prototype/results/fsk-experimental-phone-noise-decoded.json), and [format/measurements](../prototype/results/fsk-manifest.json) are saved.

This is **not CP's in-band transport**, **not a V.21 modem**, and **not fax/T.30**. Reusing two familiar carrier frequencies does not grant compatibility. It has no independent authenticated pairing; it is an alternative *transport demonstration*, not another secure handshake protocol.

Exact format:

```text
Continuous-phase binary FSK, 300 baud:
  1 = 1650 Hz; 0 = 1850 Hz
  preamble = 01 repeated 32 times (64 bits)
  sync = dd aa 96 e7 (32 bits)
  version = 01 (1 byte)
  payload length = 1 byte
  payload = ASCII CP frame (5, 16, or 11 bytes)
  CRC = 2 bytes, big-endian, over version + length + payload
        CRC-16/CCITT-FALSE: polynomial 0x1021, init 0xffff,
        refin=false, refout=false, xorout=0; check("123456789")=0x29b1
  all byte bits are sent MSB-first
```

At 8 kHz, one 300-baud symbol lasts `8000/300 = 26⅔` samples. The generator uses fractional clock boundaries and continuous carrier phase, not a fixed 27-sample symbol that would drift. The receiver searches all 27 integer-sample timing phases, independently fits sine/cosine models for each tone, compares residual energies, then verifies preamble/sync/version/length/CRC. It uses no timeline or expected payload input. It is intentionally simple: no baud-offset tracking, adaptive equalization, FEC, or retry.

The packet budgets are `168 + 256 + 216 = 640 bits`, hence **2.133333 s of bursts** at 300 bit/s, versus the DTMF sample's **4.48 s of complete symbol cells**. This comparison includes each design's demonstrated framing, not an optimal binary redesign: carrying ASCII CP strings inside FSK repeats some prefix/checksum overhead that a purpose-designed binary protocol could remove. It also excludes greetings and simulated HTTPS. Faster audio does not remove authentication, human disclosure, or network round trips.

All payloads decode exactly from clean/noisy WAVs and the delivered MP3. An arbitrary 0.731 s leading pad and −13.98 dB gain still decode. A synthesized packet with one flipped payload bit is rejected by CRC, and the main speech/DTMF call is not accepted as FSK. There are **25 additional synthetic SNR trials**: 5/5 complete sequences at each of 24, 16, 8, and 4 dB; 0/5 at 0 dB. These small, differently designed receiver tests are **not** evidence that this new profile is universally more reliable than qualified DTMF transport. A CRC is error detection, not authentication: an adversary can simply recompute it.

## 7. In-band audio versus native DTMF events

This artifact demonstrates the **in-band waveform**. A real SIP/telephony stack may detect DTMF locally and carry it as RFC 4733 `telephone-event` RTP packets, possibly removing the original tone, regenerating it elsewhere, or exposing only a digit event to the app. The receiver should then parse that event stream directly instead of running this WAV decoder.

Do not assume a call recording contains every digit merely because the receiving app got DTMF events, or that a clean in-band WAV proves RFC 4733/SIP support. Qualify each route separately: pure G.711 in-band, DTMF-event transport, and any speech-codec fallback. The API should normalize complete digit events into one frame parser without double-counting a digit received both as an event and as regenerated audio.

## 8. Execution / learning journal

1. Inspected the local concept, fax modem/handshake research, repository conventions, and the upstream CP draft/encoder/tests. Chose a research prototype rather than a deployed service.
2. Compared hybrid DTMF, narrowband FSK, ggwave, and pure metadata against the actual task. Selected the existing CP frame layout for the primary implementation, no unsolicited fax classification tones.
3. Computed exact frame/check digits and timing/entropy budget. Separated OFFER duration from the three-message total, and code discovery from authentication.
4. Synthesized local two-voice disclosure/greeting around true DTMF symbols. Applied fixed-seed narrowband noise, echo, local hum, and PCMU companding.
5. First noisy build **failed**, revealing echo-tail/release interaction. Recorded the mechanism, fixed only signal-based detector behavior, and reran the complete file decode rather than hide the failure behind metadata.
6. Re-read actual saved WAVs, encoded delivery MP3s and decoded those again, and verified every frame. Recorded immutable hashes of the delivered files.
7. Ran sensitivity and negative controls. Preserved the failures as well as passes, especially ±1.5% frequency offset, weak SNR, and long erasures.
8. Ran signed-record/binding negative fixtures offline. Kept all fake identities, timestamps, and insecure demo key provenance explicit.
9. [Independent parent review](2026-11-05-handshake-independent-review.md) checked source math, waveform spectra, blind prefix/gain transformations, channel semantics, and evidence wording. It recovered the 32 symbols with a separate FFT implementation, verified arbitrary leading/trailing padding and reduced gain/stereo, and rejected three real historical fax/modem recordings. See the [spectrogram](../assets/phone-handshake-2026-11-05/spectrogram.png).
10. Added the bounded FSK comparator so the fax analogy is audible. Kept its invented format, lack of authentication, receiver limitations, exact packet bytes/CRC, additional 25 synthetic trials, and separate compatibility status explicit.

## 9. Follow-up experiments that would change a deployment decision

1. Native event transport and in-band dual-path tests over actual intended SIP provider routes, with duplicate-event handling.
2. Real recorded human speech/talk-off corpus, more levels, echo delays, clipping, AGC, packet loss, telephone transcoding, and mobile speech codecs.
3. Full deadline/retry/fallback state machine; arbitrary/repeated-digit fixtures; robust clock/frequency tolerance and symbol timing, rather than more hand-tuned thresholds.
4. A formal channel-binding threat model and full mandate/proof verification, including race/relay/conference scenarios.
5. If there is a real offline-only requirement, a defined FSK packet format with sync, version/capabilities, strong CRC, sequence numbers, ARQ or FEC, and signed identity/authorization. Do not silently call that CP or fax.

## 10. Primary source trail

Access/research date 2026-11-05. Source claims and our measured results are intentionally separated.

- [CP-Handshake draft v0.1, pinned source](https://github.com/viva-lee/agent-handshake/blob/a965c167faa59bc52738b90dee6d57b8a68cd864/spec/handshake.md): frame format, profile timing, OFFER gating, signed registry checks, BIND, fallback/deadlines, security assumptions/open issues. Explicitly experimental.
- [CP TypeScript DTMF encoder/decoder](https://github.com/viva-lee/agent-handshake/blob/a965c167faa59bc52738b90dee6d57b8a68cd864/src/protocol/dtmf.ts): exact Luhn orientation, 12-key subset, payload lengths, 80/60 ms constants.
- [CP JWS reference](https://github.com/viva-lee/agent-handshake/blob/a965c167faa59bc52738b90dee6d57b8a68cd864/src/crypto/jws.ts): compact EdDSA/Ed25519 and JWK thumbprint conventions.
- [ITU-T Q.23](https://www.itu.int/rec/T-REC-Q.23-198811-I/en): multifrequency push-button signaling frequency basis.
- [ITU-T Q.24](https://www.itu.int/rec/T-REC-Q.24-198811-I/en): receiver considerations and timing/tolerance context; this research detector has **not** been tested for conformance.
- [ITU-T G.711](https://www.itu.int/rec/T-REC-G.711-198811-I/en): PCM companding; this artifact uses FFmpeg PCMU roundtrip, not a smooth logarithmic approximation.
- [RFC 4733](https://www.rfc-editor.org/rfc/rfc4733.html): DTMF and named telephone events over RTP; why tone/event handling differs from ordinary speech encoding.
- [ITU-T V.21](https://www.itu.int/rec/T-REC-V.21-198811-I/en) and [ITU-T T.30](https://www.itu.int/rec/T-REC-T.30-200509-I/en): distinguish modem signaling from fax session procedures.
- [ggwave technical details](https://github.com/ggerganov/ggwave#technical-details): default profile's frequency layout and framing/error-correction design.
- [GibberLink source/demo](https://github.com/PennyroyalTea/gibberlink): agent data-over-sound inspiration, not evidence of PSTN support.
- [RFC 7515](https://www.rfc-editor.org/rfc/rfc7515.html), [RFC 8037](https://www.rfc-editor.org/rfc/rfc8037.html), [RFC 7638](https://www.rfc-editor.org/rfc/rfc7638.html): compact JWS, Ed25519/OKP JWKs, and JWK thumbprints used in the offline illustrative fixture.

No third-party audio or copied standards text is included. Speech is generated locally with FFmpeg/Flite. The tone encoder, detector, synthetic channel, and research notes were written for this experiment.
