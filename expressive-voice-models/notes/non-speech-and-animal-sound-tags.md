# Non-speech controls and animal sounds

Research/experiment design, checked 2026-11-07. No animal-sound training run
or generated-animal-audio quality result is claimed here.

## Start with controls the model already learned

Ming 3.0's official **Beyond the words** section documents inline controls
including `[Breathing]`, `[Cough]`, `[Sigh]` and `[Laughter]`. Verify these
through the exact inference runtime and quantization before considering
fine-tuning. Documentation for the original model does not establish that
every conversion exposes the same features.
[Official Ming documentation](https://github.com/inclusionAI/Ming-3.0-tts#beyond-the-words).

These are human paralinguistic events. The documented list does not establish
native dog/cat/other-animal support. Conversely, speaking the words “woof” or
“meow” is not the same experiment as generating a convincing animal waveform.

## Define the desired behavior

These examples are **proposed application labels**, not verified native tokens
or the input schema of a released trainer:

```text
[dog_bark]
That surprised me. [Laughter]
Listen to this: [cat_meow]
```

Decide whether the goal is a real animal recording-like sound, a human
imitation, or a stylized character voice. Treat those as different targets.
Also decide whether events must stand alone or be mixed naturally into speech.

## Proposed investigation sequence

1. **Establish the baseline.** Save exact inputs, model/runtime revisions,
   seeds, reference voice and unedited WAVs. Check documented human events
   and the animal-sound target separately. A missing feature is not solved
   merely by inventing bracket syntax.
2. **Check the acoustic representation.** Encode/decode target clips with the
   base model's audio codec. Listen for loss of bark transients, tonal detail
   or noise texture. If the codec cannot represent the target acceptably,
   language-model LoRA alone may not solve that bottleneck.
3. **Prepare a small labeled dataset.** Use permitted recordings, aligned
   event spans and consistent labels. Retain audio provenance, sample rate,
   duration and quality annotations. Split by recording/source/animal rather
   than allowing near-duplicate segments in train and evaluation sets.
4. **Map architecture before selecting trainable modules.** Identify text
   tokenization/control encoding, audio tokens, conditioning, transformer
   components, audio decoder and waveform codec. Adding a tokenizer entry
   also requires a plan for its embeddings and any relevant output head.
5. **Only then pick a training experiment.** A supported adapter/trainer,
   codec-token extraction, loss/masking rules, speaker conditioning and
   checkpoint export path are prerequisites—not details to guess from an
   inference-only model card. Estimate training VRAM separately from inference.
6. **Preserve normal speech.** Mix in speech/control examples and negative
   examples where animal words should be spoken literally. Check that adding
   new events does not cause unwanted barks/laughter in ordinary dialogue.
7. **Evaluate held-out events and speech.** Report requested-event accuracy,
   false insertions, duration/control consistency, human listening preference,
   intelligibility and speaker consistency. Speech recognition alone cannot
   certify a cough or bark; do not delete failed/silent generations from the
   success denominator.

This sequence is an engineering proposal, not a measured data requirement or
claim that a particular amount of audio/LoRA rank will work on 16 GB VRAM.

## What the Drama-3 Japanese adaptation establishes—and does not

The author reports LoRA rank/alpha 32/32, approximately 70,000 hours of
Japanese speech for one epoch, **plus token-embedding and audio-decoder
training**. That is not an adapter-only proof of cheap animal-sound training.
The published model demonstrates language/expressive adaptation, not a
reproducible small-data recipe for this proposed use case.
[Author's training section](https://huggingface.co/Aratako/Drama-3-Japanese#training).

Fish Speech's Drama-3 beta release explicitly removed its training/LoRA/data
extraction tools. Older Fish Speech training tutorials should not be assumed
compatible with Drama 3. An exact compatible trainer and module/loss mapping
are still prerequisites before calling a run reproducible.
[Official release notes](https://github.com/fishaudio/fish-speech/releases/tag/v3.0.0-beta).

## Alternative worth comparing

For a product prototype, routing a controlled event to a small licensed sound
library is a useful baseline. It can establish whether the feature improves
the experience before spending time on a generative model. Label this as
sample playback—not learned synthesis or fine-tuning—and test transitions
into/out of speech separately.

## Results status

- Native Ming human-event controls: documented upstream; exact-runtime
  verification belongs in a separately recorded test.
- Animal controls: proposed, not validated.
- Animal-sound fine-tune: not started.
- Qwen/Nanbeige dialogue evaluation: tracked separately in the
  [benchmark run folder](../benchmarks/companion-support-2026-11-07/README.md).
