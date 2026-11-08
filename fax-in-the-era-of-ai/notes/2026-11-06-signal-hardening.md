# Live signal acquisition: development finding and correction

The implementation first passed a separate-process live exchange and the
initial independent clock/delay/fault matrix. A further physical-erasure test
then exposed a receiver confidence issue. This note preserves the finding;
the finalized matrix must be rerun after the correction.

## What actually happened

An 80 ms span inside an all-one payload was replaced with exact digital silence.
The sliding complex-correlator accumulators retain tiny floating-point roundoff
when their window moves into zeros. Taking only the sign of the difference of
two nearly-zero energies can consistently produce one. In this deliberately
chosen payload those guesses matched the original erased bits, so the original
CRC still validated. The detector consequently returned the correct bytes,
but with insufficient physical evidence for those particular symbols.

This was **not** a hidden-payload channel, known-fixture lookup, checksum bypass,
or authentication bypass. Erasing bits does not mathematically guarantee a
CRC failure: if the receiver happens to guess the same bits, the checksum is
unchanged. The issue was accepting unsupported low-energy bit decisions.

## Minimal correction

For every candidate packet body, inspect matched-tone energy at each recovered
symbol. Require its minimum energy to exceed both a small absolute floor and
4% of that candidate's peak energy. The relative gate is about −14 dB in power.
Near-zero numerical residuals are now erasures, not evidence for a bit. Such a
candidate is rejected, leaving the live state machine to perform bounded ARQ.

A second regression replaces the payload span with the opposite **real FSK
tone**, guaranteeing actual bit changes without erasing energy. That is rejected
by the CRC. Both controls are necessary to distinguish confidence rejection
from error-detection claims.

The wire format, oscillator model, HMAC/HKDF construction and protocol state
machine were unchanged. Counters `erasureRejections` and `crcRejections` count
**candidate timing hypotheses**, not distinct frames or packet-loss percentages.

## Trade-off and bounds

This conservative gate is not optimized for deep fading; more than about 14 dB
of within-packet energy collapse may be rejected even if another modem could
recover it. No FEC or adaptive equalizer is claimed. Transmitter and receiver
injectors accept independent ±2500 ppm values, but the acquisition clock bank
spans ±3000 ppm **relative symbol-period error**: opposed extreme injectors can
exceed it. Successful ±200 ppm independent-clock tests are not a guarantee for
all accepted simulator inputs.

Recorded initial smoke audio remains useful: blind replay with the hardened
receiver still recovered all seven actual frames. Its provenance explicitly
says it predates the final error-handling fixes; the independent final matrix
and Docker rerun validate the finalized code.
