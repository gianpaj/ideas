#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

mkdir -p run/openmoss-trainer run/tmp
export TMPDIR="$PWD/run/tmp"
export UV_CACHE_DIR="$PWD/run/uv-cache"
export HF_HOME="$PWD/run/hf"
export HF_HUB_DOWNLOAD_TIMEOUT=120

uv venv --allow-existing --python 3.12 run/venv
uv pip install --python run/venv/bin/python --index https://download.pytorch.org/whl/cu128 \
  'torch==2.9.1+cu128' 'torchaudio==2.9.1+cu128'
uv pip install --python run/venv/bin/python \
  'transformers==5.12.1' 'peft==0.20.0' 'accelerate==1.15.0' 'torchcodec==0.8.1' 'soundfile==0.14.0'

upstream=https://raw.githubusercontent.com/OpenMOSS/MOSS-TTS/934d6826b084c46a0d033402174d5f8ac4ed2519/moss_tts_local_v1.5/finetuning
for file in common.py dataset.py sft.py; do
  curl -fLsS --retry 2 "$upstream/$file" -o "run/openmoss-trainer/$file"
done

download_snapshot() {
  local repo="$1" revision="$2" name="$3"
  local snapshot="$HF_HOME/hub/models--${repo/\//--}/snapshots/$revision"
  run/venv/bin/hf download "$repo" --revision "$revision"
  test -f "$snapshot/config.json"
  # Transformers resolves relative imports beside the file, so use real files.
  local model_dir="$PWD/run/moss_${name}_${revision:0:8}"
  mkdir -p "$model_dir"
  cp -alL --update=none "$snapshot/." "$model_dir/"
  printf '%s\n' "$model_dir" > "run/$name.path"
}

download_snapshot laion/moss-tts-local-transformer-4.55b-voice-acting-v2 1aff170de525ea80ad916f89ce19b61fb2c1d25e model
download_snapshot OpenMOSS-Team/MOSS-Audio-Tokenizer-v2 f6e20e543b33d2c252a7ef71bdf8aa71e5ff9169 codec
run/venv/bin/python make_data.py
