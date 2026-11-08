"""Build short, attributed audio fixtures for the MOSS LoRA smoke test."""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "run" / "data"
SOURCES = {
    "lion": ("https://upload.wikimedia.org/wikipedia/commons/7/7d/Lion_raring-sound1TamilNadu178.ogg",
             "https://commons.wikimedia.org/wiki/File:Lion_raring-sound1TamilNadu178.ogg", "public domain", 0.45, 1.6),
    "imitation": ("https://cdn.freesound.org/previews/611/611721_13511310-hq.mp3",
                  "https://freesound.org/people/_justMonke_/sounds/611721/", "CC0-1.0", 0.4, 2.3),
    "sneeze": ("https://upload.wikimedia.org/wikipedia/commons/4/48/Sneeze.ogg",
               "https://commons.wikimedia.org/wiki/File:Sneeze.ogg", "CC0-1.0", 0.0, 1.0),
    "sneezing": ("https://upload.wikimedia.org/wikipedia/commons/d/d0/Sneezing.ogg",
                 "https://commons.wikimedia.org/wiki/File:Sneezing.ogg", "public domain", 0.0, 3.4),
}
ROWS = [
    ("Come closer.", "Want to see my den?", "a short playful lion roar", "lion"),
    ("Listen carefully.", "Did you hear me?", "a short playful lion roar", "imitation"),
    ("That flower tickles.", "Much better.", "sneeze", "sneeze"),
    ("Something is in the air.", "I am all right.", "sneeze", "sneezing"),
    ("Come closer.", "Want to see my den?", None, None),
    ("That flower tickles.", "Much better.", None, None),
]


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def speech(text, path):
    ffmpeg("-f", "lavfi", "-i", f"flite=text={text}:voice=slt", "-ar", "48000", "-ac", "2", str(path))


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    reference = ROOT / "reference.wav"
    speech("I live near the big hill. It is nice and quiet here.", reference)
    gap = ROOT / "gap.wav"
    ffmpeg("-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "0.15", str(gap))
    events = {}
    for name, (url, _, _, start, duration) in SOURCES.items():
        original = ROOT / f"{name}.source"
        if not original.exists():
            subprocess.run(["curl", "-fLsS", "--retry", "2", "--max-time", "40", url, "-o", str(original)], check=True)
        events[name] = ROOT / f"{name}.wav"
        ffmpeg("-ss", str(start), "-i", str(original), "-t", str(duration), "-ar", "48000", "-ac", "2",
               "-af", "loudnorm=I=-20:LRA=7:TP=-2,afade=t=in:d=0.01,areverse,afade=t=in:d=0.01,areverse",
               str(events[name]))

    records = []
    left, right = ROOT / "left.wav", ROOT / "right.wav"
    for index, (before, after, cue, source) in enumerate(ROWS):
        speech(before, left)
        speech(after, right)
        parts = [left, gap, events[source], gap, right] if cue else [left, gap, right]
        target = ROOT / f"row-{index:02}.wav"
        inputs = [arg for path in parts for arg in ("-i", str(path))]
        ffmpeg(*inputs, "-filter_complex", f"concat=n={len(parts)}:v=0:a=1", str(target))
        script = f"{before} ({cue}) {after}" if cue else f"{before} {after}"
        records.append({
            "id": target.stem,
            "audio": str(target),
            "ref_audio": str(reference),
            "language": "English",
            "text": f"{before} {after}",
            "instruction": f"GENERAL: A friendly lion speaks in a warm, playful voice.\nSCRIPT:\n{script}",
            "source": SOURCES[source][1] if source else None,
            "source_license": SOURCES[source][2] if source else None,
        })
    (ROOT / "train.jsonl").write_text("".join(json.dumps(row) + "\n" for row in records))


if __name__ == "__main__":
    main()
