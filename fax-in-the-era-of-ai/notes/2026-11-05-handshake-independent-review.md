# Independent mathematical and signal review

Research date: 2026-11-05. This is an exploratory audio prototype, not a
carrier-qualified modem or deployed booking service. A second Codex researcher
reviewed the modulation choices independently of the prototype author; the
parent reviewer also checks the delivered waveform separately.

## The useful fax analogy

Reuse discovery, capability negotiation, synchronization, confirmation and
fallback. Do not reuse fax identification tones just for their sound: CNG,
CED and ANSam already have meanings to telephone equipment. The main demo
implements the idea's DTMF rendezvous followed by a simulated HTTPS handoff.
Its purpose is not to send an LLM conversation through a modem.

## Airtime accounting

For `n` symbols at 80 ms on / 60 ms off, the allocated budget is `0.14n`
seconds; first-tone onset to last-tone end is `0.14n - 0.06`.

| Frame | Symbols | Budget including final gap | First tone to last tone |
| --- | ---: | ---: | ---: |
| PROBE | 5 | 0.70 s | 0.64 s |
| OFFER | 16 | 2.24 s | 2.18 s |
| BIND | 11 | 1.54 s | 1.48 s |
| Sum | 32 | 4.48 s | 4.30 s |

There are 2.56 seconds of active tone. Speech, turn guards, registry/API round
trips and retries are additional. An approximately two-second OFFER is not an
approximately two-second complete handshake.

The 12-key alphabet has at most `log2(12) = 3.585` bits per symbol; decimal
payload digits have `log2(10) = 3.322`. A checksum contributes error detection,
not additional secret entropy. At this cadence the decimal-payload ceiling
before framing is approximately 23.73 bits/s; framing lowers useful throughput.

## Alternative physical layers

### V.21-like BFSK

The V.21 caller uses 980/1180 Hz; the answering channel uses 1650/1850 Hz,
at up to 300 bit/s. The frequencies fit a narrowband phone path. However,
`T = 1/300 s` and `delta_f = 200 Hz` give `delta_f * T = 2/3`.
The textbook orthogonal, noncoherent, one-symbol BFSK error expression therefore
cannot simply be assigned to a naive V.21 tone-energy detector.

For rectangular complex tones the normalized correlation magnitude is
`abs(sin(pi * delta_f * T) / (pi * delta_f * T))`. Integer, nonzero
`delta_f * T` gives orthogonality for that model. Phase assumptions differ for
coherent real-sinusoid detection; actual modem timing recovery also matters.

If both ends control PCM and DTMF event transport provides no benefit, an
interesting **unimplemented alternative** is 1200/1800 Hz at 300 bit/s:
`delta_f * T = 2`. A hypothetical 96-bit OFFER (version 4, type 4, registry 4,
nonce 64, CRC 16, reserved 4), plus 200 ms acquisition, 32-bit sync and 80 ms
guard, takes `0.2 + (32 + 96)/300 + 0.08 = 0.707 s`.
That is calculated airtime, not a measured performance result, a V.21-compliant
profile, or a carrier-interoperability claim.

### MFSK and chirps

Four orthogonal tones at 800/1000/1200/1400 Hz with 10 ms symbols have
`delta_f * T = 2` and carry two bits/symbol: 200 raw bit/s. Extra tones trade
bandwidth and detection complexity for throughput; framing and error protection
still cost airtime.

A chirp spanning 2400 Hz for 40 ms has `BT = 96`, or `10 log10(BT) = 19.82 dB`.
This is a time-bandwidth ratio, **not free AWGN link gain**. Matched-filter
performance still depends on transmitted energy, noise, timing and channel
distortion. Chirps may help acquisition around narrowband interferers, but need
their own implementation and codec tests.

The documented default audible ggwave grid runs from 1875 to 6328.125 Hz.
It does not fit wholly inside a 300–3400 Hz telephone channel. This finding
concerns that profile, not the impossibility of adapting data-over-sound.

## Reliability math: assumptions matter

For orthogonal, noncoherent BFSK in AWGN with ideal synchronization and equally
likely bits, `P_b = 0.5 exp(-E_b/(2N_0))`. At linear `E_b/N_0 = 10`, BER is
approximately 0.00337. Under an independent-bit approximation a 96-bit packet
has `1 - (1 - P_b)^96`, approximately 27.7%, probability of at least one error.
These are theoretical model values, not predictions for speech codecs.

Similarly, independent 1% DTMF symbol errors give `0.99^32 = 72.50%` probability
that all three frames arrive without a symbol error. Real errors can be bursty;
timeouts, retries, checksums and voice fallback belong in the protocol budget.

Shannon's ideal AWGN bound, `C = B log2(1 + S/N)`, gives about 20.64 kbit/s for
3100 Hz bandwidth and 20 dB SNR. It does not guarantee a modem rate through a
speech codec, echo canceller, packet loss or voice activity detector.

## Pairing is not identity authentication

- A ten-digit rendezvous locator has at most 33.22 bits of entropy. With `N`
  active locators, a random lookup finds *any* active locator with probability
  `N / 10^10`, not `1 / 10^10`. It must not grant authority by itself.
- Allocation must check live-code uniqueness. With 100,000 unchecked random
  allocations, the birthday approximation `1 - exp(-N(N-1)/(2*10^10))` gives
  approximately 39.35% probability of at least one collision.
- A uniform six-digit BIND has 19.93 bits. At most three guesses against the
  correctly scoped current-call challenge give targeted success probability
  approximately `3e-6`, assuming no observation, leak or active injection.
- Luhn and CRC are not authentication. A random uniform check-digit guess
  passes Luhn with probability 1/10; a uniform random CRC-16 remainder matches
  with probability 1/65536. Neither protects against intentional modification.
- BIND demonstrates ability to return the HTTPS challenge on the selected call
  media leg. It is not proof of human identity, telephone ownership, or resistance
  to active relays/conference injection.
- Verify a registry-signed record against a pretrusted key, expiry and the number
  originally dialed. API authorization/mandates are separate from tone detection.

## Reviewer findings during development

The first 50 ms echo simulation extended weak DTMF tails into 60 ms interdigit
gaps. Initial noisy decoding failed despite clean decoding passing. This was a
real receiver/channel interaction, not a reason to describe the first generated
file as successful. The implementer added local relative-power echo rejection;
the sensitivity results must retain the detector's limitations.

Review also caught integer stereo input being averaged before normalization;
that path was corrected. Delivered files are tested again from disk, including
MP3 round-trip decoding.

## Independent delivered-waveform validation

The separate [FFT review script](../prototype/review_signal.py) reads the saved
WAV alone. It uses 40 ms Hann windows at 5 ms steps, FFT-band energy rather than
the main receiver's 30 ms direct projections, plus a documented local-energy
echo gate. It does not accept expected frames or generator timestamps. Its
initial absolute-energy-only version also split weak echo tails; that was fixed
before the final review. It is another research detector, not a certified
reference receiver or evidence of implementation independence under every fault.

The 23.75-second noisy file yielded exactly 32 symbols:

```text
*#26#  *#1048151623426#  *#32718280#
```

Measured peak: -5.307 dBFS; clipped samples: zero. The
[spectrogram](../assets/phone-handshake-2026-11-05/spectrogram.png) is computed
from this actual noisy file, with symbol annotations obtained by the FFT
detector. [Raw review results](../prototype/results/independent-fft.json).

The main receiver also recovered all three exact frames after adding an
unannounced 0.731-second silent prefix, a 0.331-second suffix and 0.2x gain
(-13.98 dB). A separate integer-stereo file with channel gains 0.2x and 0.12x
also passed. Those tests use saved WAV input, not timeline metadata:
[transformation evidence](../prototype/results/parent-robustness.json).

As additional negative controls, the main receiver processed three existing
public recordings from the fax-history research: a 10.310-second fax answer,
5.400-second ANSam tone and 21.345-second V.92 modem handshake. All yielded
zero detected digits and zero accepted CP frames. Source URLs and original-file
hashes are saved in [fax-negative evidence](../prototype/results/parent-fax-negatives.json);
the source recordings are not republished in this prototype. This supplements,
but does not replace, the synthetic controls or a proper speech talk-off study.

Reproduce the independent check (NumPy, SciPy; Matplotlib only for `--plot`):

```sh
python3 fax-in-the-era-of-ai/prototype/review_signal.py \
  fax-in-the-era-of-ai/assets/phone-handshake-2026-11-05/call-phone-noise.wav \
  --plot /tmp/phone-handshake-review.png
```

## Completion check, 2026-11-06

The parent reviewer inspected the additional `fsk_comparator.py` receiver.
Acquisition searches nominal symbol phases and protocol sync; the decoder
does not consult `EXPECTED`, generation timestamps or a payload template.
CRC, version and length checks validate candidate packets. Re-decoding the
saved noisy WAV recovered all three exact payload strings with valid CRCs.
This is a functional experimental packet modem, not V.21/T.30 compliance or
a complete live pairing/authentication service. The speech-free DTMF and FSK
MP3s were delivered to the user on 2026-11-06; the user clarified that speech
should not be the default machine-handshake demonstration.

## Primary references

- [Counter Protocol experimental handshake specification](https://github.com/viva-lee/agent-handshake/blob/main/spec/handshake.md): framing, cadence and HTTPS binding.
- [RFC 4733](https://www.rfc-editor.org/rfc/rfc4733.html): named DTMF event transport and the limits of passing tones through speech codecs. Separate RTP event payloads are not an authenticated side channel.
- [ITU-T V.21](https://www.itu.int/rec/T-REC-V.21-198811-I/en): modem rates and frequency allocation.
- [ITU-T Q.23](https://www.itu.int/rec/T-REC-Q.23/en) and [Q.24](https://www.itu.int/rec/T-REC-Q.24/en): DTMF frequency pairs and reception considerations; this prototype is not a conformance test.
- [ITU-T T.30](https://www.itu.int/rec/T-REC-T.30-200509-I/en): fax discovery/control procedure and identification tones.
- [ggwave author documentation](https://github.com/ggerganov/ggwave#technical-details): modulation grid and error correction.
- [RFC 3551, section 4.5.14](https://www.rfc-editor.org/rfc/rfc3551.html#section-4.5.14): PCMU/PCMA G.711 companding.

The alternative modulation calculations and probability derivations above are
our analysis under the stated assumptions, not measurements asserted by those
sources.
