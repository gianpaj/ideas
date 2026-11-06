# Clock and audio-link review

## Actual requirement

Two independently running, headless endpoints must generate and receive audio,
decode packets, and react causally to received protocol messages. The handshake
and a small application data round trip travel entirely through audio. No web
UI, carrier account, spoken dialogue, simulated HTTPS handoff, prearranged
success timeline, or shared expected payload is needed.

The implementation target is two Node.js 24 programs, with an optional
audio-only impairment relay and a Docker Compose reproduction. The relay is
not an agent and must not know the pairing secret or interpret protocol
messages. PCM packet sequence/sample counters are transport metadata, not a
shortcut for transferring decoded protocol messages.

## Three independent time problems

1. **Wall-clock offset:** one endpoint may report a different date/time. A
   clock model is `C_i(t) = theta_i + (1 + epsilon_i) t`. Arbitrary `theta_i`
   must not prevent pairing. Do not compare absolute timestamps from peers
   to decide whether a packet is timely.
2. **Local elapsed time:** retries, receive deadlines and idle expiry use a
   local monotonic clock. Differences such as `M_i(end) - M_i(start)` cancel
   the local clock's arbitrary origin. Wall-clock adjustment is not elapsed
   time. A wall-offset injection must actually affect the application clock,
   not merely appear as an unused configuration field.
3. **Audio oscillator error:** nominal 8 kHz devices may produce/consume
   samples at different physical rates. A correct drift model changes both
   tone frequencies and symbol duration. Changing a timestamp label or just
   sleeping longer between unchanged audio packets is not the same effect.

For transmitter error `epsilon_A` and receiver error `epsilon_B`, the relative
sample-rate error is

```text
(1 + epsilon_A) / (1 + epsilon_B) - 1
```

At +200 ppm versus -200 ppm, A→B error is approximately +400.08 ppm and B→A
approximately -399.92 ppm. At 8 kHz, 400 ppm corresponds to 3.2 samples/second:
32 samples after ten seconds, an entire nominal 250-baud symbol. A receiver
that acquires only the beginning of a long frame can still lose timing later.
Bounded frame sizes, timing recovery/clock hypotheses and reacquisition matter.

If an implementation injects transmitter-only error against an ideal receiver,
label that limitation rather than claim two physical device oscillators were
modeled. The decoder must not receive the transmitter's injected error value
as an oracle.

## Delay, jitter and loss are not clock offsets

Constant one-way propagation delay shifts arrival but does not itself change
the sampled waveform. Variable packet delay can distort playout unless the
receiver buffers and orders samples. A bounded jitter buffer should discard
late packets, insert explicit silence for missing media, and report those
events separately from successful decoding. Duplicates/reordered packets must
not create duplicate protocol actions.

Use sequence numbers and sample-position counters with independent starting
offsets. Do not require a shared wall clock to reconstruct each stream. Measure
actual request/reply elapsed time with one endpoint's monotonic clock. With
asymmetric paths, RTT/2 is not a measured one-way delay. The impairment harness
can report its configured one-way delays as simulation parameters, not claim
to have measured geographic telephone latency.

A useful matrix includes baseline; +1 h/-2 h application wall offsets;
independent positive/negative sample-clock error; asymmetric 300/650 ms
one-way delays; 60 ms jitter; a deliberately dropped first exchange; and
wrong-secret/muted-return negative controls. A success must mean verified
receipt of the application's requested bytes, not playback completion.

## Docker is isolation, not automatically a different clock

Ordinary Docker containers share the host's underlying time. Merely starting
two containers does not introduce the desired clock differences. Inject
application clock offsets and audio-clock resampling explicitly; do not grant
`CAP_SYS_TIME` or change the host clock. Linux time namespaces concern
monotonic/boot-time clocks, not ordinary independent `CLOCK_REALTIME` values.
No privileged network namespace or host `tc` configuration is necessary for a
userspace impairment relay.

## Protocol correctness checks

- Fresh random nonces and a privately provisioned single-user pairing key;
  no deterministic public demonstration identity.
- Validate frame length, CRC and keyed authentication before state changes.
- An initiator must receive authenticated peer confirmation, not declare
  success after transmitting its own final handshake message.
- Retries for the same nonce must reuse the responder's cached challenge;
  otherwise delayed duplicates can continually invalidate each other.
- Replay/duplicate data may trigger a cached response but not a repeated
  application action.
- Failure must be observable: muting all response audio or using the wrong
  key must prevent a successful data round trip.
- Stop/timeout must release timers, sockets and decoder workers. Buffers,
  pending packet queues and captures must have explicit bounds.

## Primary references

- [RFC 3550, section 5.1](https://www.rfc-editor.org/rfc/rfc3550.html#section-5.1): monotonically advancing media sample timestamps and independent stream origins. Its media timing principles inform this experiment; the custom audio transport is not presented as an RTP implementation.
- [RFC 3550, section 6.4.1](https://www.rfc-editor.org/rfc/rfc3550.html#section-6.4.1): interarrival jitter and relative transit-time differences.
- [Node.js 24 performance APIs](https://nodejs.org/docs/latest-v24.x/api/perf_hooks.html): local process-relative performance measurements.
- [Node.js 24 datagram APIs](https://nodejs.org/docs/latest-v24.x/api/dgram.html): UDP sockets used by the audio transport.
- [Linux time namespaces manual](https://man7.org/linux/man-pages/man7/time_namespaces.7.html): which clocks time namespaces virtualize and their restrictions.

These equations and the proposed matrix are review criteria, not completed
measurements. Actual commands and outcomes will be recorded with the live
implementation's validation evidence.

## Development findings and completed checks

Independent waveform inspection caught an initially reversed oscillator sign.
After correction, a -1000 ppm injection measured 2247.75 Hz for the nominal
2250 Hz tone, and +1000 ppm measured 2252.25 Hz. Burst-duration measurements
also agreed within the test's 80 ppm tolerance for integer-sample quantization.
The check measures samples, not the decoder's chosen clock hypothesis.

Separate-process testing caught negative CLI numeric values being rejected
before parsing entered the error handler, and invalid addresses leaving a
decoder worker alive. Those configuration/lifecycle bugs were corrected and
covered by regression tests. The initial report is preserved rather than
counted as successful clock testing.

On the erasure-hardened core, baseline, independent clocks plus asymmetric
delay/jitter, dropped-first-response retry, wrong-key rejection, muted return
and cancellation all passed. The separate Docker endpoints also completed
the actual authenticated data exchange with +1 h/-2 h application clocks,
+200/-200 ppm audio clocks, 300/650 ms delay and 60 ms jitter. Containers had
read-only roots, no privileged mode, all capabilities dropped, and no published
host ports. The test containers were stopped after inspection.

The predetermined 1% PCM-packet-loss trial (seed 20261106) failed at the
application receipt phase after exhausting retries. It is preserved in
`live/validation/evidence/parent-matrix-before-redundancy.json`; the six other
scenarios passed. This is not a reason to call the failed trial successful.

The mechanism is unsurprising: if a frame spans `N` packets and any erased
symbol makes the frame unusable, independent packet loss `p` gives clean-frame
probability `(1-p)^N`. At `p=0.01`, `N=120`, that is only 29.94%. A 1% packet
loss rate is therefore not a 1% frame error rate. Two independently delivered
copies of each media packet reduce the all-copies-lost probability to `p^2`;
under that model the same clean-frame probability becomes approximately
98.81%. These are model calculations, not measured carrier guarantees.

The bounded follow-up is media-datagram redundancy/deduplication, not another
signaling channel or an invented successful receipt. It cannot cure correlated
long outages, all-return muting, the wrong key, or analog waveform corruption.
Actual outcomes after that change must be recorded before adopting its claim.

## Final corrected-source rerun, 2026-11-06

The final parent-owned rerun on the media-redundancy correction passed all
seven independent-process scenarios. Initiator elapsed completion times were
15.88 s baseline, 20.08 s with independent clocks and asymmetric delay/jitter,
25.58 s with the first responder burst erased (one actual retry), and 17.12 s
for the originally failing seed-20261106 1% independent datagram-loss case.
Each positive run verified the exact authenticated response and executed the
responder operation once. Wrong-key and fully muted-return tests did not pair
or execute the operation; explicit cancellation shut down both processes.
All successful sessions had distinct fingerprints. Observed decoder history
and transport queues stayed within the declared bounds.

The Docker test was rebuilt and repeated against the corrected source, not
inherited from the earlier build: both isolated endpoints exited successfully
with actual application logs approximately three hours apart, +200/-200 ppm
sample clocks, 300/650 ms configured path delays and 60 ms jitter. Inspection
again verified read-only roots, dropped capabilities and no host ports. The
test project was taken down after evidence collection. All 12 unit tests also
passed. The independent waveform measurement remains separate from endpoint
decoder assertions.

Reproduction commands, immutable source hashes, final JSON evidence and the
earlier failures are indexed in [live validation](../live/validation/README.md).
Two-copy PCM is now the tested transport default; this is not modem FEC,
protection against correlated loss, synchronized clocks or a carrier guarantee.
