#!/usr/bin/env python3
"""Experimental fax-like comparator, NOT V.21/T.30 or CP wire compatibility.

Continuous-phase1650/1850Hz FSK at300baud. New packet wrapper with alternating
preamble, sync, version, length, and CRC16; payloads are ASCII CP frames merely
to compare transporting identical content. No authentication or live network.
"""
from __future__ import annotations

import argparse
import binascii
import json
import math
import subprocess
import tempfile
from pathlib import Path

import numpy as np

import phone_handshake as base

BAUD = 300
F_ONE, F_ZERO = 1650, 1850
PREAMBLE = np.tile([0, 1], 32).astype(np.uint8)
SYNC = np.unpackbits(np.frombuffer(bytes.fromhex("ddaa96e7"), dtype=np.uint8))
VERSION = 1
SYMBOL_PERIOD = base.FS / BAUD  #26.666..., never round to a fixed27samples/bit.


def packet(payload: str) -> tuple[np.ndarray, bytes]:
    encoded = payload.encode("ascii")
    body = bytes([VERSION, len(encoded)]) + encoded
    crc = binascii.crc_hqx(body, 0xFFFF).to_bytes(2, "big")
    bits = np.concatenate([PREAMBLE, SYNC, np.unpackbits(np.frombuffer(body + crc, dtype=np.uint8))])
    return bits, body + crc


def modulate(bits: np.ndarray) -> np.ndarray:
    # Fractional baud clock: adjacent symbols have26or27samples; no cumulative drift.
    n = math.ceil(len(bits) * base.FS / BAUD)
    which = np.minimum(np.floor(np.arange(n) * BAUD / base.FS).astype(int), len(bits) - 1)
    frequencies = np.where(bits[which], F_ONE, F_ZERO)
    phase = 2 * math.pi * np.cumsum(frequencies) / base.FS
    x = .34 * np.sin(phase)
    ramp_n = 32
    envelope = np.sin(np.linspace(0, math.pi / 2, ramp_n)) ** 2
    x[:ramp_n] *= envelope
    x[-ramp_n:] *= envelope[::-1]
    return x


def demodulate(samples: np.ndarray) -> dict:
    """WAV-only acquisition: search every integer-sample baud phase, then sync.

    Fits sine+cosine for each candidate frequency independently per symbol,
    compares residual variance. No orthogonal-BFSK assumption; these tones are
    NOT orthogonal over1/300s. No timeline, frame count, expected text, or sidecar.
    CRC/preamble/version/length reject candidate false locks. Nominal baud and
    frequencies are shared protocol constants, not inferred/adapted here.
    """
    found = []
    for offset in range(math.ceil(SYMBOL_PERIOD)):
        starts = offset + np.round(np.arange(max(0, int((len(samples) - offset) / SYMBOL_PERIOD) - 1)) * SYMBOL_PERIOD).astype(int)
        if len(starts) < 128:
            continue
        #26samples fits every symbol; leave fractional end sample for acquisition tolerance.
        positions = starts[:, None] + np.arange(26)[None, :]
        windows = samples[positions]
        windows = windows - windows.mean(axis=1, keepdims=True)
        fitted = []
        t = np.arange(26) / base.FS
        for frequency in [F_ZERO, F_ONE]:
            design = np.column_stack([np.sin(2 * math.pi * frequency * t), np.cos(2 * math.pi * frequency * t)])
            design = design - design.mean(axis=0, keepdims=True)
            coefficient = windows @ np.linalg.pinv(design).T
            reconstruction = coefficient @ design.T
            fitted.append(np.sum((windows - reconstruction) ** 2, axis=1))
        bits = (fitted[1] < fitted[0]).astype(np.uint8)
        matches = np.lib.stride_tricks.sliding_window_view(bits, len(SYNC))
        sync_indices = np.flatnonzero(np.all(matches == SYNC, axis=1))
        for index in sync_indices:
            if index < len(PREAMBLE):
                continue
            preamble_errors = int(np.count_nonzero(bits[index - len(PREAMBLE):index] != PREAMBLE))
            if preamble_errors > 4:
                continue
            body_start = index + len(SYNC)
            if body_start + 16 > len(bits):
                continue
            header = np.packbits(bits[body_start:body_start + 16]).tobytes()
            if header[0] != VERSION or not 1 <= header[1] <= 64:
                continue
            count = 2 + header[1] + 2
            end = body_start + count * 8
            if end > len(bits):
                continue
            raw = np.packbits(bits[body_start:end]).tobytes()
            expected_crc = int.from_bytes(raw[-2:], "big")
            if binascii.crc_hqx(raw[:-2], 0xFFFF) != expected_crc:
                continue
            try:
                payload = raw[2:-2].decode("ascii")
            except UnicodeDecodeError:
                continue
            start_s = starts[index - len(PREAMBLE)] / base.FS
            end_s = (offset + end * SYMBOL_PERIOD) / base.FS
            if any(abs(v["start_s"] - start_s) < .05 for v in found):
                continue  # Same physical packet can pass at multiple adjacent phase hypotheses.
            found.append({"start_s": round(start_s, 5), "end_s": round(end_s, 5),
                          "payload_ascii": payload, "packet_hex": raw.hex(), "crc16_valid": True,
                          "preamble_bit_errors": preamble_errors, "sample_phase": offset})
    return {"profile": "EXPERIMENTAL AIP-FSK1; NOT V.21, T.30, or CP modulation",
            "sample_rate_hz": base.FS, "baud": BAUD, "frames": sorted(found, key=lambda v: v["start_s"])}


def build() -> None:
    assert binascii.crc_hqx(b"123456789", 0xFFFF) == 0x29B1
    chunks, timeline = [np.zeros(1600)], []
    cursor = 1600
    for role, text in zip(["caller", "business", "caller"], base.EXPECTED):
        bits, raw = packet(text)
        x = modulate(bits)
        timeline.append({"role": role, "payload_ascii": text, "packet_hex": raw.hex(),
                         "bits_including_preamble_and_sync": len(bits), "start_s": cursor / base.FS,
                         "end_s": (cursor + len(x)) / base.FS})
        chunks += [x, np.zeros(4000)]
        cursor += len(x) + 4000
    clean = np.concatenate(chunks)
    noisy = base.phone_channel(clean, snr_db=20)
    outputs = {}
    for name, data in [("fsk-experimental-clean", clean), ("fsk-experimental-phone-noise", noisy)]:
        path = base.ASSETS / f"{name}.wav"
        base.write_wav(path, data)
        decoded = demodulate(base.read_wav(path))
        actual = [v["payload_ascii"] for v in decoded["frames"]]
        if actual != base.EXPECTED:
            raise AssertionError((name, decoded))
        base.json_write(base.RESULTS / f"{name}-decoded.json", decoded)
        outputs[name] = {"wav": str(path.relative_to(base.ROOT)), "sha256": base.sha256(path),
                         "duration_s": len(data) / base.FS, "decoded_exact_payloads": True}
    mp3 = base.ASSETS / "fsk-experimental-phone-noise.mp3"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(base.ASSETS / "fsk-experimental-phone-noise.wav"),
                    "-ar", "24000", "-codec:a", "libmp3lame", "-b:a", "64k", str(mp3)], check=True)
    with tempfile.TemporaryDirectory(prefix="fsk-handshake-") as tmp:
        wav = Path(tmp) / "decoded.wav"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(mp3), "-ar", str(base.FS),
                        "-ac", "1", str(wav)], check=True)
        decoded = demodulate(base.read_wav(wav))
    assert [v["payload_ascii"] for v in decoded["frames"]] == base.EXPECTED
    base.json_write(base.RESULTS / "fsk-experimental-mp3-decoded.json", decoded)
    outputs["mp3"] = {"path": str(mp3.relative_to(base.ROOT)), "sha256": base.sha256(mp3), "decoded_exact_payloads": True}
    # Limited single-axis check; not a directly comparable channel BER benchmark.
    trials = []
    for snr in [24, 16, 8, 4, 0]:
        for seed in range(5):
            result = demodulate(base.phone_channel(clean, snr_db=snr, seed=seed))
            trials.append({"snr_db": snr, "seed": seed,
                           "exact_sequence": [v["payload_ascii"] for v in result["frames"]] == base.EXPECTED,
                           "frames_received": len(result["frames"])})
    # Blind arbitrary prefix/attenuation, unknown to receiver.
    transformed = np.concatenate([np.zeros(5848), .2 * noisy, np.zeros(2648)])
    blind = demodulate(transformed)
    assert [v["payload_ascii"] for v in blind["frames"]] == base.EXPECTED
    base.json_write(base.RESULTS / "fsk-blind-transform-decoded.json", blind)
    # Payload bit corruption: tone synthesis remains valid, CRC must reject the entire packet.
    damaged_bits, _ = packet(base.EXPECTED[1])
    damaged_bits[len(PREAMBLE) + len(SYNC) + 16 + 12] ^= 1
    corrupted = demodulate(np.concatenate([np.zeros(1600), modulate(damaged_bits), np.zeros(4000)]))
    assert not corrupted["frames"]
    # Independent format negative: the actual speech+DTMF call must not become FSK packets.
    negative = demodulate(base.read_wav(base.ASSETS / "call-phone-noise.wav"))
    assert not negative["frames"]
    manifest = {"profile": "EXPERIMENTAL AIP-FSK1, locally invented research packet wrapper",
                "not_compatible_with": ["V.21 complete modem", "T.30 fax", "CP in-band DTMF transport"],
                "baud": BAUD, "one_hz": F_ONE, "zero_hz": F_ZERO, "sample_rate_hz": base.FS,
                "bits_order": "MSB first", "preamble": "01 repeated32times (64bits)", "sync_hex": "ddaa96e7",
                "body_format": "version(1byte)=01 | payload_length(1byte) | ASCII_payload | CRC16(2bytes,big-endian)",
                "crc": {"name": "CRC-16/CCITT-FALSE", "polynomial_hex": "1021", "init_hex": "ffff",
                        "refin": False, "refout": False, "xorout_hex": "0000", "covers": "version+length+payload"},
                "authentication": "NONE: CRC and CP Luhn detect errors, not identity or tampering",
                "audio": outputs, "timeline": timeline, "raw_burst_duration_s": sum(v["bits_including_preamble_and_sync"] for v in timeline) / BAUD,
                "synthetic_snr_trials": trials,
                "summary": [{"snr_db": s, "exact_sequence_passes": sum(v["exact_sequence"] for v in trials if v["snr_db"] == s),
                             "trials": 5} for s in [24, 16, 8, 4, 0]],
                "checks": {"clean_and_noisy_WAV_payloads_exact": True, "MP3_payloads_exact": True,
                           "unknown_prefix_and_minus14dB_gain": True, "corrupted_payload_rejected_by_CRC": not corrupted["frames"],
                           "speech_DTMF_call_rejected_as_FSK": not negative["frames"]},
                "limitations": ["No trained timing/clock/frequency tracking or adaptive equalizer.",
                                "No ARQ, FEC, capabilities, discovery, signature, or live binding state.",
                                "Known nominal300baud; scan integer sample timing phases only.",
                                "25seeded trials are synthetic; cannot rank real carrier reliability against DTMF."]}
    base.json_write(base.RESULTS / "fsk-manifest.json", manifest)
    print(json.dumps({"audio": outputs, "summary": manifest["summary"], "checks": manifest["checks"]}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build")
    dec = sub.add_parser("decode")
    dec.add_argument("wav", type=Path)
    args = parser.parse_args()
    if args.command == "build":
        build()
    else:
        print(json.dumps(demodulate(base.read_wav(args.wav)), indent=2))


if __name__ == "__main__":
    main()
