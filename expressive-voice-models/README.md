# Expressive local voice models

Research and reproducible experiments for a companion/customer-support voice
product, including custom speech with controllable non-speech sounds.

The target development machine is Linux with an NVIDIA RTX 4060 Ti (16 GB
VRAM). Available memory must include speech recognition, speech synthesis,
embeddings and inference buffers—not just an LLM's weight file.

## Keep the questions separate

| Question | Evidence to collect |
| --- | --- |
| Which local LLM makes a good companion? | Multi-turn emotional/social responses and independent preference/rubric scoring |
| Which LLM resolves support requests? | Policies, tools and verified task outcomes |
| Does the whole voice product feel responsive? | Recorded caller → STT → LLM → TTS, including pauses and interruptions |
| Can speech synthesis render laughter/coughs? | Native documented controls, runtime verification and listening tests |
| Can it generate animal sounds on command? | A separate labeled-audio/codec/training experiment; not inferred from human vocalizations |

An LLM benchmark is not evidence that a TTS model can synthesize an animal
sound. A plausible-looking control tag is not evidence that a model learned it.

## Experiments and learning notes

- [Companion/support benchmark selection](notes/2026-11-07-benchmark-selection.md)
- [Qwen-first pilot: setup, progress, results and rerun instructions](benchmarks/companion-support-2026-11-07/README.md)
- [Final matched Qwen–Nanbeige comparison and audited evidence](benchmarks/companion-support-2026-11-07/COMPARISON.md)
- [Retained Qwen–Nanbeige latency, prefill counters and decode evidence](benchmarks/companion-support-2026-11-07/PERFORMANCE.md)
- [Non-speech and animal-sound control: what to verify before fine-tuning](notes/non-speech-and-animal-sound-tags.md)

## Current scope

![Qwen versus Nanbeige: average EQ rubric 4.30 vs 5.57 out of 20; both pass 8 of 10 retail tasks. Custom text pilot, not official leaderboard scores.](benchmarks/companion-support-2026-11-07/assets/qwen-nanbeige-comparison.svg)

The matched Qwen3.5 9B Q4_K_M and Nanbeige4.3-33B IQ2_M evaluation is complete.
Both have ten independently graded EQ scenarios and ten retail outcomes.
EQ custom-rubric means are **4.30/20 vs 5.57/20**; retail is **8/10 for both**.
These are custom local pilots, not official full-suite scores or evidence of
statistical superiority. Codex CLI is the independent rubric judge and customer
simulator. The original Qwen voice service was independently verified restored;
audio latency was not measured. See the final comparison for retained failures
and runtime, quantization, cache and debrief-order differences.

No custom TTS training or animal-sound fine-tune has been performed yet. This
folder is the learning record and experiment home, not a claim of a working
training recipe.
