#!/usr/bin/env python3
"""Reproducible research sample, not a telephone stack or production DTMF receiver.

The decoder uses only the input WAV. Generation metadata is NEVER its input.
CP frame syntax: upstream viva-lee/agent-handshake@a965c167faa59bc52738b90dee6d57b8a68cd864.
No network requests, phone calls, microphone access, model services, or booking.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile
from scipy.ndimage import maximum_filter1d
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

FS = 8000
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "phone-handshake-2026-11-05"
RESULTS = Path(__file__).resolve().parent / "results"
ROWS = [697, 770, 852, 941]
COLS = [1209, 1336, 1477]
KEYS = ["123", "456", "789", "*0#"]
FREQS = {key: (ROWS[row], COLS[col])
         for row, keys in enumerate(KEYS) for col, key in enumerate(keys)}
TONE_S = .080
GAP_S = .060
SEED = 20261105
CODE = "4815162342"
BIND = "271828"
MULAW_LOOKUP = None


def luhn(digits: str) -> str:
    total = 0
    for i, char in enumerate(reversed(digits)):
        d = int(char)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return str((-total) % 10)


def frame(kind: str, code: str = "") -> str:
    if kind == "probe":
        body = "2"
    elif kind == "offer" and re.fullmatch(r"\d{10}", code):
        body = "10" + code  # Registry 0 is upstream's reserved local test registry.
    elif kind == "bind" and re.fullmatch(r"\d{6}", code):
        body = "3" + code
    else:
        raise ValueError("unsupported frame or malformed decimal payload")
    return "*#" + body + luhn(body) + "#"


EXPECTED = [frame("probe"), frame("offer", CODE), frame("bind", BIND)]


def tone_stream(text: str, *, twist_db: float = 0, detune: float = 0,
                tone_s: float = TONE_S, gap_s: float = GAP_S) -> np.ndarray:
    """12-key DTMF; 4ms cosine ramps avoid clicks, equal nominal tone power."""
    n = round(FS * tone_s)
    time = np.arange(n) / FS
    ramp_n = min(round(.004 * FS), n // 2)
    envelope = np.ones(n)
    ramp = np.sin(np.linspace(0, math.pi / 2, ramp_n)) ** 2
    envelope[:ramp_n], envelope[-ramp_n:] = ramp, ramp[::-1]
    high_gain = 10 ** (twist_db / 20)
    chunks = []
    for key in text:
        low, high = FREQS[key]
        tone = (.24 * np.sin(2 * math.pi * low * (1 + detune) * time)
                + .24 * high_gain * np.sin(2 * math.pi * high * (1 + detune) * time))
        chunks.extend([tone * envelope, np.zeros(round(FS * gap_s))])
    return np.concatenate(chunks) if chunks else np.zeros(0)


def write_wav(path: Path, samples: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(path, FS, np.round(np.clip(samples, -1, 1) * 32767).astype(np.int16))


def read_wav(path: Path) -> np.ndarray:
    fs, data = wavfile.read(path)
    if data.dtype == np.uint8:
        data = (data.astype(float) - 128) / 128
    elif np.issubdtype(data.dtype, np.integer):
        data = data.astype(float) / max(abs(np.iinfo(data.dtype).min), np.iinfo(data.dtype).max)
    else:
        data = data.astype(float)
    if data.ndim > 1:
        data = data.mean(axis=1)
    if fs != FS:
        divisor = math.gcd(fs, FS)
        data = signal.resample_poly(data, FS // divisor, fs // divisor)
    return data


def mulaw_roundtrip(x: np.ndarray) -> np.ndarray:
    """Actual FFmpeg G.711 PCMU roundtrip, cached for all65536 int16 values.

    This uses the installed codec rather than a smooth mu-law approximation.
    The lookup is derived once with FFmpeg, then reused in the channel sweep.
    """
    global MULAW_LOOKUP
    if MULAW_LOOKUP is None:
        all_pcm = np.arange(-32768, 32768, dtype="<i2")
        encoded = subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "s16le", "-ar", str(FS),
                                  "-ac", "1", "-i", "pipe:0", "-f", "mulaw", "pipe:1"],
                                 input=all_pcm.tobytes(), capture_output=True, check=True).stdout
        decoded = subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "mulaw", "-ar", str(FS),
                                  "-ac", "1", "-i", "pipe:0", "-f", "s16le", "pipe:1"],
                                 input=encoded, capture_output=True, check=True).stdout
        MULAW_LOOKUP = np.frombuffer(decoded, dtype="<i2").astype(float) / 32768
    pcm = np.round(np.clip(x, -1, 1) * 32767).astype(np.int32)
    return MULAW_LOOKUP[pcm + 32768]


def phone_channel(x: np.ndarray, *, snr_db: float = 20, seed: int = SEED,
                  echo_gain: float = .12, hum_db: float = -43,
                  codec: bool = True, dropout: tuple[float, float] | None = None) -> np.ndarray:
    """Synthetic narrowband channel, NOT a measured carrier impairment model.

    SNR refers to whole-recording active-signal RMS relative to added bandlimited
    noise, before mu-law. Active means abs(x) > .015; logged for reproducibility.
    Echo is delayed50ms, no feedback; hiss is300–3400Hz. No AGC/PLC/speech codec.
    """
    sos = signal.butter(5, [300, 3400], btype="bandpass", fs=FS, output="sos")
    filtered = signal.sosfilt(sos, x)
    delay = round(.050 * FS)
    echo = np.zeros_like(filtered)
    if len(filtered) > delay:
        echo[delay:] = echo_gain * filtered[:-delay]
    y = filtered + echo
    rng = np.random.default_rng(seed)
    noise = signal.sosfilt(sos, rng.normal(size=len(x)))
    active = np.abs(filtered) > .015
    reference_rms = np.sqrt(np.mean(filtered[active] ** 2)) if np.any(active) else .20
    noise_rms = max(np.sqrt(np.mean(noise ** 2)), 1e-12)
    y += noise * reference_rms / noise_rms * 10 ** (-snr_db / 20)
    y += 10 ** (hum_db / 20) * np.sin(2 * math.pi * 60 * np.arange(len(x)) / FS)
    if dropout:
        start, duration = dropout
        y[round(start * FS):round((start + duration) * FS)] *= .02
    return mulaw_roundtrip(y) if codec else y


def decode(samples: np.ndarray) -> dict:
    """Blind DTMF detector:30ms Hann windows,5ms hop; nominal frequencies only.

    Gates: >-43dBFS RMS and >16% local125ms peak power (echo-tail rejection),
    each winning row/column >6dB over runner-up,
    +/-8dB twist and >=68% sinusoid power concentration. Minimum35ms
    consensus,30ms interdigit release. This intentionally conservative research
    detector is NOT a Q.24-conformance claim; the sensitivity sweep measures it.
    """
    width, hop = 240, 40
    if len(samples) < width:
        return {"sample_rate_hz": FS, "duration_s": len(samples) / FS, "digits": [], "frames": []}
    windows = np.lib.stride_tricks.sliding_window_view(samples, width)[::hop]
    hann = signal.windows.hann(width, sym=False)
    freqs = np.array(ROWS + COLS)
    template = np.exp(-2j * math.pi * freqs[:, None] * np.arange(width)[None, :] / FS)
    weighted = windows * hann
    projection = weighted @ template.T
    powers = 2 * np.abs(projection / hann.sum()) ** 2
    total = (windows ** 2 * hann).sum(axis=1) / hann.sum()
    row, col = powers[:, :4], powers[:, 4:]
    ri, ci = row.argmax(axis=1), col.argmax(axis=1)
    idx = np.arange(len(windows))
    rp, cp = row[idx, ri], col[idx, ci]
    rnext, cnext = np.partition(row, -2, axis=1)[:, -2], np.partition(col, -2, axis=1)[:, -2]
    eps = 1e-15
    local_peak = maximum_filter1d(total, size=25, mode="nearest")
    valid = ((total > 10 ** (-43 / 10)) & (total > .16 * local_peak) & (rp / (rnext + eps) > 4)
             & (cp / (cnext + eps) > 4) & ((rp + cp) / (total + eps) > .68)
             & (np.abs(10 * np.log10((rp + eps) / (cp + eps))) < 8))
    labels = [KEYS[r][c] if ok else None for r, c, ok in zip(ri, ci, valid)]
    # Collect contiguous consensus; require a genuine release before a repeated digit.
    runs = []
    start = 0
    for end in range(1, len(labels) + 1):
        if end == len(labels) or labels[end] != labels[start]:
            if labels[start] and (end - start) * hop / FS >= .035:
                runs.append({"digit": labels[start], "start_s": round((start * hop + width / 2) / FS, 4),
                             "end_s": round(((end - 1) * hop + width / 2) / FS, 4),
                             "confidence_ratio_min": round(float(np.min((rp + cp)[start:end] / (total[start:end] + eps))), 3)})
            start = end
    digits = []
    for item in runs:
        if digits and item["digit"] == digits[-1]["digit"] and item["start_s"] - digits[-1]["end_s"] < .03:
            digits[-1]["end_s"] = item["end_s"]
            continue
        digits.append(item)
    groups = []
    for digit in digits:
        if not groups or digit["start_s"] - groups[-1][-1]["end_s"] > .45:
            groups.append([])
        groups[-1].append(digit)
    frames = []
    for group in groups:
        text = "".join(d["digit"] for d in group)
        for match in re.finditer(r"\*#(\d+)#", text):
            body = match[1]
            if len(body) < 2 or luhn(body[:-1]) != body[-1]:
                continue
            kind, payload = body[0], body[1:-1]
            content = None
            if kind == "2" and not payload:
                content = {"kind": "probe"}
            elif kind == "1" and len(payload) == 11:
                content = {"kind": "offer", "registry": payload[0], "rendezvous_code": payload[1:]}
            elif kind == "3" and len(payload) == 6:
                content = {"kind": "bind", "bind_code": payload}
            if content:
                frames.append({**content, "wire": match[0], "start_s": group[match.start()]["start_s"],
                               "end_s": group[match.end() - 1]["end_s"], "luhn_valid": True})
    return {"sample_rate_hz": FS, "duration_s": round(len(samples) / FS, 4),
            "digit_stream": " ".join("".join(d["digit"] for d in g) for g in groups),
            "digits": digits, "frames": frames,
            "timestamp_note": "center-of-analysis-window estimates, not sample-exact onset/offset"}


def speech(text: str, voice: str = "slt") -> np.ndarray:
    # Flite is bundled into this ffmpeg build, so no model download/cloud TTS.
    with tempfile.TemporaryDirectory(prefix="phone-handshake-") as tmp:
        output = Path(tmp) / "speech.wav"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i",
                        f"flite=text='{text}':voice={voice}", "-ar", str(FS), "-ac", "1", str(output)], check=True)
        x = read_wav(output)
    peak = max(float(np.max(np.abs(x))), .001)
    return x * (.48 / peak)


def make_call() -> tuple[np.ndarray, list[dict]]:
    chunks, timeline = [], []
    cursor = 0

    def add(role: str, kind: str, value: str, samples: np.ndarray) -> None:
        nonlocal cursor
        timeline.append({"role": role, "kind": kind, "value": value,
                         "start_s": round(cursor / FS, 4), "end_s": round((cursor + len(samples)) / FS, 4)})
        chunks.append(samples)
        cursor += len(samples)

    def pause(seconds: float, reason: str = "turn-taking gap") -> None:
        add("channel", "silence", reason, np.zeros(round(seconds * FS)))

    pause(.35, "connected call, no ringing simulation")
    greeting = "Hello. I am the automated receptionist for Example Clinic."
    add("business", "speech", greeting, speech(greeting, "slt"))
    pause(.25)
    disclosure = "I am an AI agent calling on behalf of a person. Can we connect directly?"
    add("caller", "speech", disclosure, speech(disclosure, "rms"))
    pause(.20)
    add("caller", "probe", EXPECTED[0], tone_stream(EXPECTED[0]))
    pause(.22)
    offer_phrase = "Agent connect is available on this line."
    add("business", "speech", offer_phrase, speech(offer_phrase, "slt"))
    pause(.20)
    add("business", "offer", EXPECTED[1], tone_stream(EXPECTED[1]))
    pause(.65, "SIMULATED HTTPS: resolve signed rendezvous, validate, accept, receive bind challenge; no audio data")
    add("caller", "bind", EXPECTED[2], tone_stream(EXPECTED[2]))
    pause(.22)
    summary = "The data session is connected. This is a demonstration. No booking has been made."
    add("business", "speech", summary, speech(summary, "slt"))
    pause(.50, "end of demonstration")
    return np.concatenate(chunks), timeline


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def security_fixture() -> dict:
    """Offline fixture only. Published deterministic seed is NOT a credential.

    Demonstrates the essential signed-lookup checks and call-scoped BIND gate;
    does not implement mandates, full CP-Commit, a registry, TLS, or live HTTP.
    """
    private = Ed25519PrivateKey.from_private_bytes(hashlib.sha256(b"PUBLIC-INSECURE-DEMO-KEY-2026-11-05").digest())
    public = private.public_key()
    x = b64(public.public_bytes(Encoding.Raw, PublicFormat.Raw))
    bare = {"crv": "Ed25519", "kty": "OKP", "x": x}
    kid = b64(hashlib.sha256(json.dumps(bare, sort_keys=True, separators=(",", ":")).encode()).digest())
    jwk = {**bare, "kid": kid}
    now = 1793865600  # Fixed research clock, 2026-11-05T08:00:00Z.
    record = {"typ": "cp.rendezvous", "code": CODE, "session_id": "hs_demo_20261105",
              "business_id": "example-clinic", "tel": "+12025550123", "api": "https://example.invalid/cp/v0.1",
              "business_jwk": jwk, "iat": now, "exp": now + 120}
    header = {"alg": "EdDSA", "typ": "cp+jws", "kid": kid}
    h, p = [b64(json.dumps(v, separators=(",", ":")).encode()) for v in [header, record]]
    compact = f"{h}.{p}.{b64(private.sign(f'{h}.{p}'.encode()))}"

    def verify(token: str, *, clock: int = now + 3, tel: str = "+12025550123") -> dict:
        head, payload, sig = token.split(".")
        parsed_header = json.loads(unb64(head))
        if parsed_header["alg"] != "EdDSA" or parsed_header["kid"] != kid:
            raise ValueError("wrong algorithm or pinned key")
        public.verify(unb64(sig), f"{head}.{payload}".encode())
        result = json.loads(unb64(payload))
        if result["exp"] <= clock or result["tel"] != tel or result["code"] != CODE:
            raise ValueError("expired, wrong dialed telephone, or wrong rendezvous")
        return result

    checks = {"valid_signature_and_claims": verify(compact) == record}
    tampered = dict(record, api="https://attacker.invalid")
    badp = b64(json.dumps(tampered, separators=(",", ":")).encode())
    for name, token, opts in [("tampered_record_rejected", f"{h}.{badp}.{compact.split('.')[2]}", {}),
                              ("expired_record_rejected", compact, {"clock": now + 120}),
                              ("wrong_dialed_number_rejected", compact, {"tel": "+12025550999"})]:
        try:
            verify(token, **opts)
            checks[name] = False
        except (InvalidSignature, ValueError):
            checks[name] = True
    state = {"bound": False, "consumed": False, "call_id": "call-demo-1", "attempts": 0}

    def guarded_demo_mutation() -> str:
        if not state["bound"]:
            raise PermissionError("403 not_bound (offline state model)")
        return "illustrative mutation permitted; no real booking performed"

    def bind(code: str, call_id: str) -> bool:
        if state["consumed"] or call_id != state["call_id"]:
            return False
        state["attempts"] += 1
        if state["attempts"] > 3 or code != BIND:
            return False
        state["bound"], state["consumed"] = True, True
        return True

    try:
        guarded_demo_mutation()
        checks["unbound_mutation_rejected"] = False
    except PermissionError:
        checks["unbound_mutation_rejected"] = True
    checks["wrong_bind_rejected"] = not bind("000000", "call-demo-1")
    checks["wrong_call_rejected"] = not bind(BIND, "different-call")
    checks["correct_call_bind_accepted"] = bind(BIND, "call-demo-1")
    checks["bound_demo_mutation_permitted"] = guarded_demo_mutation().startswith("illustrative")
    checks["replay_bind_rejected"] = not bind(BIND, "call-demo-1")
    return {"scope": "offline illustrative subset, NOT full CP authentication or backend",
            "fixed_clock_unix_s": now, "registry_public_jwk": jwk, "signed_rendezvous_jws": compact,
            "record": record, "checks": checks,
            "key_warning": "Signing seed is deterministic, public in source, and intentionally insecure; NEVER reuse."}


def sweep() -> dict:
    """Single-axis sweeps; detector fixed throughout, developed on nominal fixture."""
    base = np.concatenate([np.zeros(1600), *[np.concatenate([tone_stream(v), np.zeros(4000)]) for v in EXPECTED]])
    cases = []

    def trial(label: str, setting: dict, data: np.ndarray, seed: int) -> None:
        actual = decode(data)
        recovered = [v["wire"] for v in actual["frames"]]
        cases.append({"condition": label, **setting, "seed": seed, "expected_frames": 3,
                      "decoded_frames": len(recovered), "exact_sequence": recovered == EXPECTED,
                      "recovered": recovered})

    for snr in [30, 24, 20, 16, 12, 8, 4, 0, -4]:
        for seed in range(10):
            trial("snr", {"snr_db": snr}, phone_channel(base, snr_db=snr, seed=seed), seed)
    for twist in [-10, -8, -6, -3, 0, 3, 6, 8, 10]:
        alt = np.concatenate([np.zeros(1600), *[np.concatenate([tone_stream(v, twist_db=twist), np.zeros(4000)]) for v in EXPECTED]])
        for seed in range(3):
            trial("twist", {"high_minus_low_db": twist, "snr_db": 20}, phone_channel(alt, seed=seed), seed)
    for detune in [-.03, -.02, -.015, -.01, 0, .01, .015, .02, .03]:
        alt = np.concatenate([np.zeros(1600), *[np.concatenate([tone_stream(v, detune=detune), np.zeros(4000)]) for v in EXPECTED]])
        for seed in range(3):
            trial("frequency_offset", {"fractional_offset": detune, "snr_db": 20}, phone_channel(alt, seed=seed), seed)
    # Deliberately damage an OFFER digit, not an arbitrary silence interval.
    offer_start = .2 + len(EXPECTED[0]) * .14 + .5
    for duration in [.010, .020, .040, .060, .080]:
        for seed in range(3):
            trial("burst_erasure", {"erasure_s": duration, "snr_db": 20},
                  phone_channel(base, seed=seed, dropout=(offer_start + 5 * .14, duration)), seed)
    grouped = []
    for condition in ["snr", "twist", "frequency_offset", "burst_erasure"]:
        selected = [v for v in cases if v["condition"] == condition]
        settings = list(dict.fromkeys(json.dumps({k: v for k, v in row.items() if k not in {"seed", "expected_frames", "decoded_frames", "exact_sequence", "recovered"}}, sort_keys=True) for row in selected))
        for text in settings:
            setting = json.loads(text)
            group = [v for v in selected if all(v[k] == value for k, value in setting.items())]
            grouped.append({**setting, "trials": len(group), "exact_sequence_passes": sum(v["exact_sequence"] for v in group)})
    return {"scope": "Synthetic deterministic impairment sweep; NOT carrier qualification or a speech-codec test",
            "baseline": {"bandpass_hz": [300, 3400], "echo_delay_ms": 50, "echo_gain": .12, "mu_law": True},
            "summary": grouped, "cases": cases}


def negatives() -> dict:
    passages = [
        "Hello, this is the automated receptionist. Please tell me your name and the reason for your call.",
        "I would like an appointment on Tuesday at ten thirty. My telephone number is two zero two five five five zero one two three.",
        "Press one for opening hours, press two for the front desk, or stay on the line to speak with a person.",
        "Could you repeat that? There is some noise on the line. Thank you for calling and have a wonderful afternoon."
    ]
    spoken = np.concatenate([speech(t, voice) for voice in ["slt", "rms"] for t in passages])
    spoken = np.tile(spoken, math.ceil(120 * FS / len(spoken)))[:120 * FS]
    rng = np.random.default_rng(SEED)
    white = rng.normal(0, .12, 120 * FS)
    t = np.arange(120 * FS) / FS
    fax = np.concatenate([.22 * np.sin(2 * math.pi * freq * np.arange(20 * FS) / FS)
                          for freq in [1100, 2100, 1650, 1850, 440, 350]])
    # Contains real DTMF digits but no framing and a deliberately corrupt valid-looking frame.
    ordinary = "0123456789#*1234567890#*"
    bad = EXPECTED[1][:-2] + str((int(EXPECTED[1][-2]) + 1) % 10) + "#"
    samples = {"flite_speech_120s": phone_channel(spoken),
               "bandlimited_noise_120s": phone_channel(white),
               "fax_and_call_progress_sines_120s": phone_channel(fax),
               "unframed_digits_and_bad_checksum": phone_channel(tone_stream(ordinary + bad))}
    output = []
    for name, x in samples.items():
        result = decode(x)
        output.append({"name": name, "duration_s": round(len(x) / FS, 3),
                       "detected_digits": len(result["digits"]), "accepted_frames": result["frames"]})
    # Closed-set synthetic negatives are not a quantified real-world talk-off rate.
    return {"scope": "Synthetic closed-set negatives, two Flite voices; NOT measured human-speech talk-off probability",
            "cases": output, "total_duration_s": sum(v["duration_s"] for v in output),
            "zero_accepted_frames": all(not v["accepted_frames"] for v in output)}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_write(path: Path, value: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def build() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    clean, timeline = make_call()
    noisy = phone_channel(clean, snr_db=20)
    tones = np.concatenate([np.zeros(1600), *[np.concatenate([tone_stream(v), np.zeros(4000)]) for v in EXPECTED]])
    variants = {"call-clean": clean, "call-phone-noise": noisy, "tones-only-phone-noise": phone_channel(tones)}
    outputs = {}
    for name, x in variants.items():
        path = ASSETS / f"{name}.wav"
        write_wav(path, x)
        result = decode(read_wav(path))  # Re-read quantized file: verify what is actually delivered.
        json_write(RESULTS / f"{name}-decoded.json", result)
        passed = [v["wire"] for v in result["frames"]] == EXPECTED
        if not passed:
            raise AssertionError(f"{name} failed independent WAV decoding: {result['digit_stream']}")
        outputs[name] = {"wav": str(path.relative_to(ROOT)), "sha256": sha256(path),
                         "duration_s": len(x) / FS, "decoded_exact_sequence": passed}
    for name in ["call-phone-noise", "tones-only-phone-noise"]:
        path, mp3 = ASSETS / f"{name}.wav", ASSETS / f"{name}.mp3"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(path), "-ar", "24000",
                        "-codec:a", "libmp3lame", "-b:a", "64k", str(mp3)], check=True)
        with tempfile.TemporaryDirectory(prefix="phone-handshake-mp3-") as tmp:
            decoded_wav = Path(tmp) / "decoded.wav"
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(mp3), "-ar", str(FS),
                            "-ac", "1", str(decoded_wav)], check=True)
            result = decode(read_wav(decoded_wav))
        passed = [v["wire"] for v in result["frames"]] == EXPECTED
        if not passed:
            raise AssertionError(f"delivery MP3 failed independent decoding: {result['digit_stream']}")
        json_write(RESULTS / f"{name}-mp3-decoded.json", result)
        outputs[name]["mp3"] = {"path": str(mp3.relative_to(ROOT)), "sha256": sha256(mp3), "decoded_exact_sequence": passed}
    json_write(RESULTS / "timeline.json", timeline)
    security = security_fixture()
    if not all(security["checks"].values()):
        raise AssertionError("offline security fixture failed")
    json_write(RESULTS / "offline-security-fixture.json", security)
    sweeps = sweep()
    json_write(RESULTS / "sensitivity.json", sweeps)
    negative = negatives()
    json_write(RESULTS / "negative-controls.json", negative)
    if not negative["zero_accepted_frames"]:
        raise AssertionError("false positive in closed-set negatives")
    manifest = {"research_date": "2026-11-05", "seed": SEED, "sample_rate_hz": FS,
                "upstream_commit": "a965c167faa59bc52738b90dee6d57b8a68cd864", "expected_frames": EXPECTED,
                "tone_ms": 80, "gap_ms": 60, "total_tone_burst_budget_s": 32 * .14,
                "channel": {"bandpass_hz": [300, 3400], "filter": "5th-order Butterworth bandpass, causal",
                            "active_signal_snr_db": 20, "echo_delay_ms": 50, "echo_gain": .12,
                            "hum_60hz_dbfs_peak": -43, "g711_mu_law_roundtrip": True},
                "audio": outputs, "offline_security_checks": security["checks"],
                "sensitivity_trials": len(sweeps["cases"]), "negative_control_seconds": negative["total_duration_s"],
                "limitations": ["No real call, no carrier certification, no SIP or RFC4733 event test.",
                                "The HTTPS wait is simulated, cryptographic fixture runs separately offline.",
                                "No production secrets; published deterministic key is insecure by design.",
                                "No full CP mandate verification, booking, receipts, TLS or registry service.",
                                "Synthetic voices and channel; not recorded humans or a measured telephone channel."]}
    json_write(RESULTS / "manifest.json", manifest)
    print(json.dumps({"audio": outputs, "sensitivity_trials": len(sweeps["cases"]),
                      "negative_seconds": negative["total_duration_s"], "security_checks": security["checks"]}, indent=2))


def selftest() -> None:
    assert luhn("7992739871") == "3"
    assert EXPECTED == ["*#26#", "*#1048151623426#", "*#32718280#"]
    # A checksum collision is not authentication; never count the check digit as entropy.
    for text in EXPECTED:
        assert luhn(text[2:-2]) == text[-2]
        result = decode(np.concatenate([np.zeros(1600), tone_stream(text), np.zeros(1600)]))
        assert [v["wire"] for v in result["frames"]] == [text], result
    repeated_trials = []
    for kind, code in [("offer", "0000000000"), ("offer", "1111111111"), ("offer", "9999999999"),
                       ("bind", "000000"), ("bind", "111111"), ("bind", "999999")]:
        text = frame(kind, code)
        x = np.concatenate([np.zeros(1600), tone_stream(text), np.zeros(4000)])
        for condition, data in [("clean", x), ("phone_noise", phone_channel(x))]:
            result = decode(data)
            passed = [v["wire"] for v in result["frames"]] == [text]
            assert passed, (text, condition, result)
            repeated_trials.append({"wire": text, "condition": condition, "passed": passed})
    # Known PCMU extrema and zero, after the real FFmpeg codec roundtrip.
    assert np.allclose(mulaw_roundtrip(np.array([-1., 0., 1.])), np.array([-32124, 0, 32124]) / 32768)
    assert all(security_fixture()["checks"].values())
    result = {"selftest": "passed", "expected_frames": EXPECTED, "repeated_digit_waveform_checks": repeated_trials}
    json_write(RESULTS / "selftest.json", result)
    print(json.dumps(result))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build")
    sub.add_parser("selftest")
    dec = sub.add_parser("decode")
    dec.add_argument("wav", type=Path)
    args = parser.parse_args()
    if args.command == "build":
        build()
    elif args.command == "selftest":
        selftest()
    else:
        print(json.dumps(decode(read_wav(args.wav)), indent=2))


if __name__ == "__main__":
    main()
