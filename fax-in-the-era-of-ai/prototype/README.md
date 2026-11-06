# Agent phone-handshake audio experiment

Research artifact, 2026-11-05. No real calls, bookings, or live registry.

## Listen

- **[Primary demo: tones only — MP3, 6.18 s](../assets/phone-handshake-2026-11-05/tones-only-phone-noise.mp3)**: the real, decodable DTMF PROBE → OFFER → BIND exchange with phone noise. No speech is needed for the machine handshake.
- [Optional spoken-context version — MP3, 23.75 s](../assets/phone-handshake-2026-11-05/call-phone-noise.mp3): two synthetic voices illustrate a shared human/agent reception line around the same tone exchange. The dialogue is not protocol data or a requirement.
- [Noisy 8 kHz PCM WAV](../assets/phone-handshake-2026-11-05/call-phone-noise.wav) and [clean reference WAV](../assets/phone-handshake-2026-11-05/call-clean.wav).
- **[Fax-like FSK alternative — MP3, 3.83 s](../assets/phone-handshake-2026-11-05/fsk-experimental-phone-noise.mp3)**: a separate, experimentally defined binary packet profile, not CP/V.21/T.30 compatible. Its CRC-checked packets carry the same three frame strings, and are genuinely decoded from the WAV/MP3. This one makes the familiar modem-like warble.

The recommended design sounds like a short keypad exchange, **not a fax screech**. The audio is data, not sound effects. A decoder recovers every frame from the delivered WAVs and from the MP3s after decoding back to PCM; it does not read the timeline or expected frame positions.

The fax-like FSK alternative is the closer *sound* to a modem. It carries the
same messages using a different experimental physical layer. Neither demo
requires an LLM, speech recognition or speech synthesis for the handshake;
Flite is used only to generate the optional narrated scenario. Pairing can be
all tones even when subsequent authentication and transactions use HTTPS.

Read the [research notebook](../notes/2026-11-05-phone-handshake-research.md) for alternatives, mathematical budget, security assumptions, measurements, and limitations. The [manifest](results/manifest.json) records hashes and conditions; the [timeline](results/timeline.json) labels the voices and phases.

[Independent review](../notes/2026-11-05-handshake-independent-review.md) includes a separately implemented FFT receiver, blind prefix/gain/stereo checks, historical fax/modem negative controls, and an annotated [spectrogram](../assets/phone-handshake-2026-11-05/spectrogram.png). `prototype/review_signal.py` uses optional Matplotlib to regenerate that plot; the core audio build/decoder does not need it.

## What is actually implemented

- Exact **CP-Handshake draft v0.1 frame syntax**, 12-key DTMF, 80 ms tones + 60 ms gaps, local-test registry `0`.
- Dual-sine tone generation, 4 ms edge ramps, 8 kHz PCM.
- Causal 300–3400 Hz channel filter, 50 ms / 0.12-amplitude echo, 20 dB active-signal SNR bandlimited hiss, low receive-side 60 Hz hum, and an actual FFmpeg G.711 μ-law encode/decode roundtrip.
- Blind spectral DTMF detector and Luhn/length frame parser with observed timestamps.
- Offline Ed25519 signed-rendezvous verification and a small call-scoped BIND state example, with tampering/expiry/wrong-number/wrong-call/replay negative checks.
- 159 synthetic sensitivity trials and 365.6 seconds of closed-set negative controls.

**Not implemented:** live TLS/HTTP, a registry service, CP mandates/proof-of-possession, real identity verification, a booking backend, signed receipts, telephony APIs, SIP/RFC 4733 events, full CP state/deadline/retry handling, or carrier qualification. The 650 ms silence in the sample represents a *simulated* HTTPS exchange; the cryptography fixture is a separate offline test. The spoken “connected” line describes that scenario, not a real authenticated call.

## Run

Requires Python 3, NumPy, SciPy, cryptography, and FFmpeg built with `flite` and `libmp3lame`. Tested with Python 3.14.4, NumPy 2.3.5, SciPy 1.16.3, cryptography 46.0.5. No downloaded model, GPU, network, microphone, or voice-agent service is used.

```sh
# Optional isolated environment; do not modify a production voice-agent venv.
python3 -m venv .venv-handshake
.venv-handshake/bin/pip install -r fax-in-the-era-of-ai/prototype/requirements.txt

OPENBLAS_NUM_THREADS=1 python3 fax-in-the-era-of-ai/prototype/phone_handshake.py selftest
OPENBLAS_NUM_THREADS=1 python3 fax-in-the-era-of-ai/prototype/phone_handshake.py build

# WAV alone: no sidecar/timeline/session fixture required.
OPENBLAS_NUM_THREADS=1 python3 fax-in-the-era-of-ai/prototype/phone_handshake.py decode \
  fax-in-the-era-of-ai/assets/phone-handshake-2026-11-05/call-phone-noise.wav

# Optional fax-like comparison: run after the main build.
OPENBLAS_NUM_THREADS=1 python3 fax-in-the-era-of-ai/prototype/fsk_comparator.py build
OPENBLAS_NUM_THREADS=1 python3 fax-in-the-era-of-ai/prototype/fsk_comparator.py decode \
  fax-in-the-era-of-ai/assets/phone-handshake-2026-11-05/fsk-experimental-phone-noise.wav
```

If using the optional environment, replace `python3` with `.venv-handshake/bin/python`. `OPENBLAS_NUM_THREADS=1` avoids unnecessary BLAS thread overhead for these small matrices. Audio synthesis uses local FFmpeg/Flite; versions/builds of that synthesizer or the MP3 encoder can change the exact file hashes on rebuild. The fixed random seed and saved outputs preserve this run's evidence.

The signed fixture uses a **deliberately public deterministic test key**, fixed timestamp, `example.invalid`, fictional clinic, and reserved fictional `+1 202-555-0123` number. It is not a usable identity or credential.

## Evidence

- [Manifest](results/manifest.json)
- [Decoded noisy WAV](results/call-phone-noise-decoded.json)
- [Decoded noisy MP3](results/call-phone-noise-mp3-decoded.json)
- [All sensitivity cases](results/sensitivity.json)
- [Negative controls](results/negative-controls.json)
- [Offline signed fixture and checks](results/offline-security-fixture.json)
- [Experimental FSK format, decoded payloads, and measurements](results/fsk-manifest.json)

All pass/fail counts refer to **synthetic tests under the stated conditions**, not real telephone network reliability.
