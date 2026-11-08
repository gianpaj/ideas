# Animals TTS

**Stage** · Roar pilot
**Date** · 2026-11-08

A voice for a fictional animal that can make its own sound mid-sentence. The first cue is `[roar]`. The application translates it to `(Lion Roar)` in the MOSS script and leaves the spoken text as plain dialogue. The model generates the speech and roar in one pass.

The local pilot produced one take with a roar between the phrases, confirmed by listening. The other 20 tagged takes did not meet the automated criterion. Whisper recovered both phrases in all 21. [Listen to the confirmed take](assets/speech-roar-speech.mp3)

## Training recipe

1. Start from LAION MOSS-TTS Local Voice Acting v2 at revision `1aff170de525ea80ad916f89ce19b61fb2c1d25e` and OpenMOSS Audio Tokenizer v2 at `f6e20e543b33d2c252a7ef71bdf8aa71e5ff9169`. [Model](https://huggingface.co/laion/moss-tts-local-transformer-4.55b-voice-acting-v2/tree/1aff170de525ea80ad916f89ce19b61fb2c1d25e) · [Codec](https://huggingface.co/OpenMOSS-Team/MOSS-Audio-Tokenizer-v2/tree/f6e20e543b33d2c252a7ef71bdf8aa71e5ff9169)
2. Cut 15 roar excerpts of about 1.5 seconds from eight public sources. Normalize toward −20 dBFS RMS and fade the edges. Split each of 20 MOSS-generated carrier lines between its two phrases using Whisper word timestamps. Insert three different roar excerpts per line, with 60–140 ms of silence on each side. Keep the 20 original lines as matched controls. This yields 60 tagged targets and 20 controls at 48 kHz stereo. [Source credits](references/roar-audio.md)
3. Encode each target and the shared voice reference to 12 codec codebooks. Use the processor's generation prefix for each prompt. Append assistant audio rows and an audio-end row, shift labels by one row, and mask the prompt and audio padding. This keeps the first generated audio frame supervised with the same prompt layout used at inference. [OpenMOSS training utilities at the pilot revision](https://github.com/OpenMOSS/MOSS-TTS/tree/934d6826b084c46a0d033402174d5f8ac4ed2519/moss_tts_local_v1.5/finetuning)
4. Train a fresh PEFT LoRA with rank 16, alpha 32, dropout 0.05 and a frozen BF16 base. Target Q/K/V/O, gate/up/down, local attention and feed-forward projections, and all 12 audio heads. Use SDPA, gradient checkpointing, microbatch 1, accumulation 2, AdamW at `1e-4`, betas `(0.9, 0.95)`, zero weight decay, clip norm 1.0, seed 314 and 120 optimizer steps. Weight each audio codebook loss by `32/12` relative to text. On the RTX 4060 Ti, the optimizer loop took 76 seconds and peaked at 10.46 GiB of reserved VRAM. The separate codec pass peaked at 10.94 GiB.

The pilot used public source audio. ElevenLabs requires express permission to use its generated output for model training. [ElevenLabs policy](https://elevenlabs.io/use-policy)

## Confirmed take

Use the same voice reference for training and inference. The pilot reference is a local Flite `slt` reading of “I live near the big hill. It is nice and quiet here.”

```text
GENERAL: A friendly lion speaks in a warm, playful voice.
SCRIPT:
I heard you call my name. (Lion Roar) You can come a little closer.
```

The `text` field contains both phrases with the cue removed. Load the step-120 adapter unmerged at strength **0.75** and sample with seed **3043**, text temperature 0.7, audio temperature 1.0, audio top-p 0.95, audio top-k 25, audio repetition penalty 1.1 and a 160-frame cap.

The take runs 5.92 seconds. Listen around 3 seconds. Whisper placed the gap between the phrases at 1.50–3.66 seconds, where YAMNet scored the roar at 0.50. The pilot used 0.30 as a screening threshold and used a human listen to confirm the selected take. The rate of 1 in 21 is from three held-out lines, several seeds and three adapter strengths.

The pilot scripts, dataset manifest, trained checkpoint and full scores are in the local `../moss-v2-smoke/run/roar-pilot/` directory on `gianrtx`. Git ignores the run directory. The MP3 in this folder is the selected generation from that run.

[Expressive voice models](../README.md)
