# Expressive voice models — custom TTS

Research and reproducible experiments for **custom text-to-speech models**:
fine-tuning, LoRA/adapters, training, and controllable non-speech sounds.
This is the learning record for speech synthesis, not the voice agent's LLM
benchmark archive.

## Scope

- TTS model architecture, conditioning, audio codecs and representation limits.
- Dataset sourcing, cleaning, event labels, alignment and held-out evaluation.
- Fine-tuning/LoRA and training workflows with an exact compatible trainer,
  trainable-module mapping and export/runtime path.
- Human non-speech controls such as laughter, breathing, sighs and coughs.
- Custom animal-sound controls, distinguishing real sounds, human imitations
  and stylized character voices.
- Synthesis evaluation: intelligibility, speaker consistency, requested-event
  accuracy, false insertions and listening tests.

A plausible bracket tag is not evidence that a model learned the event.
Native human vocalizations do not establish animal-sound support; codec
representability and exact-runtime behavior must be checked separately.

## Learning notes

- [Non-speech and animal-sound control: baseline checks, datasets, codec limits and training prerequisites](notes/non-speech-and-animal-sound-tags.md)

## Results status and hardware

**No custom TTS training or animal-sound fine-tune has been performed yet.**
The existing notes describe research and proposed experiments, not a proven
training recipe, data requirement or quality result.

The target development machine is Linux with an NVIDIA RTX 4060 Ti (16 GB
VRAM). Estimate training weights, gradients, optimizer state and activations
separately from inference. Do not infer a training fit from a quantized model
loading successfully.

## Separate voice-agent repository

The application, LLM selection, **Qwen versus Nanbeige benchmarks**, quality
results, first-text/prefill/decode measurements, charts and reproduction scripts
belong in **gianpaj/local-voice-agent**:

- [Canonical LLM benchmark index](https://github.com/gianpaj/local-voice-agent/blob/e3afaf93a2c125bae19ca3aa769c1a929c1c7daa/benchmarks/README.md)
- [Preserved Qwen–Nanbeige comparison and timing charts](https://github.com/gianpaj/local-voice-agent/blob/e3afaf93a2c125bae19ca3aa769c1a929c1c7daa/benchmarks/companion-support-2026-11-07/COMPARISON.md)

The links pin the migrated archive revision so they work before or after branch
merges. Legacy benchmark paths here contain redirects only; no benchmark data
or chart copies are maintained in this TTS research folder.
