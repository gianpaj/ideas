# Independent acceptance evidence — 2026-11-06

These checks launch real endpoint processes, transfer PCM, and inspect their
actual outcomes. They do not manufacture a successful packet, share protocol
state between endpoints, or declare success because a sound file ended.

## Final outcomes

| Check | Observed result |
| --- | --- |
| Unit/UDP/relay/crypto/DSP regressions | 12/12 passed |
| Independent-process baseline | Passed; verified receipt in 15.88 s |
| Clock offset + oscillator drift + asymmetric path | Passed; verified receipt in 20.08 s |
| First responder audio burst erased | Passed; one retry, receipt in 25.58 s |
| Different pairing keys | Correctly failed; no protected operation |
| All return modulation muted | Correctly failed; no protected operation |
| Cancellation | Both endpoints reported cancellation and released processes |
| Predetermined 1% independent datagram loss | Passed with two copies; receipt in 17.12 s, no retry |
| Docker-isolated clock/delay exchange | Both endpoint containers exited 0 with authenticated completion |
| Independent oscillator waveform check | ±1000 ppm produced the expected carrier and burst-duration change |

Positive runs verified the exact user-selected echo payload and authenticated
receipt; responder operation count was one. Fresh sessions had different
fingerprints. Time above is initiator-local elapsed completion, including
the session's signal transmission and close sending, not pure network RTT.

Both the process and Docker clock cases inject +1 h/-2 h application wall
clocks, +200/-200 ppm audio clocks, 300/650 ms asymmetric one-way delays,
60 ms jitter, nominal 24 dB hiss and 0.10 echo gain. Docker shares host time;
the offsets are explicitly injected application clocks, without changing the
host. The 1% case instead uses 20 ms jitter, seed 20261106, 5 s retry interval,
six retries per phase and two identical PCM datagram copies. It does not also
claim the clock-case impairments.

## Reproduce

Requires Node 24; Docker/Compose only for the container check. Run from `live/`.
The process runner creates private temporary pairing keys and deletes its own
scratch directories and child processes. Ports 32000–32020 must be available.

```sh
npm test
node validation/verify-clock.mjs
node validation/parent-matrix.mjs
```

For Docker, provision the ignored private key once, then use an isolated project:

```sh
node src/cli.mjs init --state .state # skip if this key already exists
export LOCAL_UID="$(id -u)" LOCAL_GID="$(id -g)"
docker compose -p phonepair-parent-20261106 up --build -d
node validation/check-docker.mjs phonepair-parent-20261106
docker compose -p phonepair-parent-20261106 down
```

The Docker checker waits for both endpoints, checks their real logs and actual
commands, verifies a matching fresh session, and inspects read-only roots,
dropped capabilities, no privileged mode and no host-published ports.

## Saved reports

- [Source hashes, runtimes and evidence manifest](evidence/verification.json)
- [Final seven-scenario process matrix](evidence/parent-matrix.json)
- [Final Docker results and actual commands](evidence/docker.json)
- [Independent waveform frequency/duration measurements](evidence/clock-waveform.json)
- [Unit test runner output](evidence/unit-tests.log)
- [Earlier negative-number CLI failure](evidence/parent-matrix-development.json)
- [Earlier 1% loss failure before transport redundancy](evidence/parent-matrix-before-redundancy.json)

The initial [live recording](../evidence/live-exchange-manifest.json) uses
one-copy media and is labelled as an earlier causal smoke recording. It is not
presented as the recording of this later matrix. Its seven physical frames can
still be recovered from the WAV without the generator's timeline:

```sh
node evidence/decode-live-capture.mjs evidence/live-exchange-2026-11-06.wav
```

## Interpretation limits

One selected seed is not a measured reliability percentage. Independent-copy
loss is not correlated carrier loss. Immediate media duplication does not add
modem error correction. The relay is a mild synthetic PCM channel, not a real
G.711/Opus/carrier or microphone/speaker test. Checks authenticate a privately
provisioned symmetric-key domain; payloads are not encrypted and receipts are
not public signatures. The tiny application operation is an idempotent echo,
not a dealership booking backend. The final CLOSE is best effort: caller
receipt verification does not prove the responder received CLOSE.
