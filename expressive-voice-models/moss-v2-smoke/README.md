# MOSS v2 LoRA smoke test

Run from this directory on a CUDA host with at least 12 GiB free VRAM. Setup uses `uv`, `curl`, and FFmpeg with `libflite`. It downloads about 17 GB of model and codec weights plus the CUDA environment into `run/`.

```sh
bash setup.sh
HF_HOME="$PWD/run/hf" HF_HUB_OFFLINE=1 OMP_NUM_THREADS=2 CUDA_VISIBLE_DEVICES=0 \
  run/venv/bin/python -u smoke.py
```

The six fixtures pair short Flite dialogue with two roar sources, two sneeze sources, and two dialogue controls. `run/data/train.jsonl` records the source and license for each splice. The input uses the same English script cue and prompt packing as inference. The target covers every assistant audio frame and the stop token.

The trainer freezes the pinned BF16 base and updates a rank-16 adapter for ten optimizer steps with four microbatches per step. It encodes the fixtures before loading the TTS base so only one large model occupies the GPU at a time. The run checks the first audio label, finite gradients, and an actual LoRA weight update. It saves the adapter and per-step metrics under `run/result/`. Load the adapter unmerged because the audio head weights are tied to the input embeddings.

This fixture set measures training feasibility and memory use. Cue accuracy needs a separate evaluation on held-out lines.
