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
