# Minimal Drama 3 LoRA experiment

2026-11-07 · [Verdict and memory budget](REPORT.md) · [Tensor contract](ARCHITECTURE.md)

**Objective.** Prove that the full Drama 3 checkpoint can train and reload an adapter using a real teacher-forced speech example. The behavior probe is a brief laugh at a specified mid-line boundary in an English utterance, with its plain counterpart as a control. The base model already accepts the cue. Run the adaptation pilot only if the pinned base shows a repeatable gap. The pilot does not estimate how much data production-quality control or Japanese adaptation requires.

## Dataset

Record eight volunteers who explicitly consent to model training, voice-reference conditioning and listening evaluation. Store consent records separately and use opaque speaker and recording IDs. For each speaker record six short scripts in two takes, one with a brief laugh between two phrases and one with the same words spoken plainly. Also record one neutral 2–3 s reference in a separate recording session with different words. Use target clips around 2–5 s. Keep the pause near the event natural, trim leading and trailing dead air conservatively and skip clipped, overlapping, noisy or mislabeled takes. Ask a second listener to verify word and event boundaries. If using licensed data, document both reuse terms and permission for voice conditioning before collecting it.

Split by speaker into four train, two validation and two test speakers (48/24/24 targets plus split-local references). Give each split its own scripts and source recordings. Keep plain and tagged variants together. Assert disjoint speaker IDs, normalized target texts, reference texts, recording IDs and file hashes across splits. Within each split, ensure no reference shares a source with its targets. Keep the raw file hashes and provenance so segmented, overlapping or re-encoded copies can be traced. Use validation only to choose a checkpoint. Hold out test renders until the end.

One JSONL object per target. Paths are relative to the isolated run directory. `target.event.after_word` is the 1-based index in the plain transcript. Times are relative to the processed WAV, in seconds.

```json
{
  "id": "spk01-p03-laugh",
  "pair_id": "spk01-p03",
  "split": "train",
  "speaker_id": "spk01",
  "language": "en",
  "target": {
    "recording_id": "spk01-session02-take03",
    "wav": "wav/spk01-p03-laugh.wav",
    "codes": "codes/spk01-p03-laugh.npy",
    "text": "All right, I admit it. I packed the wrong bag.",
    "prompt": "All right, I admit it. [laughs] I packed the wrong bag.",
    "event": {
      "type": "laugh",
      "after_word": 5,
      "start_seconds": 1.7,
      "end_seconds": 2.1
    }
  },
  "references": [
    {
      "recording_id": "spk01-session01-ref01",
      "wav": "wav/spk01-ref01.wav",
      "codes": "codes/spk01-ref01.npy",
      "text": "The window looks out over a quiet street."
    }
  ],
  "permission_record": "consent-spk01",
  "sample_rate_hz": 44100
}
```

Use `event: null` and `prompt == text` for plain takes. The example values are illustrative. Save a checksum manifest, actual durations and frame lengths, normalization tool version, codec SHA, config and tokenizer hashes, split seed, and annotation rules with the run. Captioning is omitted from this experiment.

## Commands for a later isolated run

The metadata inspector ran for both base revisions and the Japanese checkpoint. FFmpeg normalization ran on a synthetic stereo fixture. The install, model download, codec extraction and baseline synthesis commands below were checked against the source. Their first execution with model weights is pending. Use a separate GPU allocation or a separate machine. Leave the voice services running. Log the driver, Torch/CUDA versions, GPU/RAM headroom and disk space before installing or loading the model. The full checkout files below require about 42 GB on disk.

```bash
# Read-only on any machine. No weight payloads.
python3 inspect_checkpoint.py fishaudio/drama-3 \
  78e5ab79e49aa9a25abe8799eff2c4d73a1c3216 \
  --tensor 'embed_tokens|lm_head|layers\.0\.mlp\.experts\.0\.|mtp.heads.0'
```

On the dedicated training box, use Python 3.12 and the upstream `uv.lock` with the `cu129` extra. Prerequisites include Git, uv, the Hugging Face `hf` CLI, ffmpeg, libsox and PortAudio development headers on Debian-like Linux. Record exact tool versions. Source checkout was verified in the research workspace.

```bash
# Run only after the model download and hardware have been authorized.
export DRAMA3_RUN=/absolute/path/to/drama3-smoke
mkdir -p "$DRAMA3_RUN"/{model,wav,codes,out,raw}
git clone https://github.com/fishaudio/fish-speech.git "$DRAMA3_RUN/fish-speech"
cd "$DRAMA3_RUN/fish-speech"
git checkout --detach 0f8a12e8a651062fdee9c33a894bdccd3a8513f1
uv sync --locked --python 3.12 --extra cu129

hf download fishaudio/drama-3 \
  --revision 78e5ab79e49aa9a25abe8799eff2c4d73a1c3216 \
  --local-dir "$DRAMA3_RUN/model"
printf '%s  %s\n' \
  74fc41c5a7151c6f350af8bd7e5d6e3accfcc7f3dfbfac23afd35af07052bb2f \
  "$DRAMA3_RUN/model/codec.pth" | sha256sum --check
```

Prepare each manifest WAV with FFmpeg and extract its codes using the surviving **single-file** codec CLI. The WAV output from the codec command is a round-trip artifact. The adjacent NPY is the input for training.

```bash
id=spk01-ref01
ffmpeg -nostdin -i "$DRAMA3_RUN/raw/$id.wav" \
  -ac 1 -ar 44100 -c:a pcm_s16le "$DRAMA3_RUN/wav/$id.wav"

uv run --no-sync python -m fish_speech.models.dac.inference \
  --device cpu --config-name modded_dac_vq \
  --checkpoint-path "$DRAMA3_RUN/model/codec.pth" \
  --input-path "$DRAMA3_RUN/wav/$id.wav" \
  --output-path "$DRAMA3_RUN/codes/$id.wav"
```

Validate each NPY with `allow_pickle=False`: integer shape `[10,F]`, nonempty, `F == ceil(wav_samples/2048)`, row 0 values below 4096, rows 1–9 below 1024, all nonnegative. Listen to the codec round-trip. A missing laugh there indicates a data/codec problem upstream of LoRA. If CPU extraction is too slow, use CUDA on the dedicated machine in a separate process before loading the backbone.

Run the pinned native baseline once with the tag and once without it, writing distinct outputs and code directories. Use seeds 42, 43 and 44 for the final comparison. Use the same precision, sampling and reference in the adapted runner. This command uses the dequantized BF16 base for comparison with the proposed trainer. Record the official FP8 baseline separately if desired.

```bash
FISH_DRAMA3_FP8_EXPERTS=0 FISH_DRAMA3_CUDA_GRAPH=0 \
  uv run --no-sync python -m fish_speech.models.text2semantic.inference \
  --checkpoint-path "$DRAMA3_RUN/model" --device cuda:0 \
  --prompt-text 'The window looks out over a quiet street.' \
  --prompt-tokens "$DRAMA3_RUN/codes/spk01-ref01.npy" \
  --text 'All right, I admit it. [laughs] I packed the wrong bag.' \
  --seed 42 --single-chunk --max-new-tokens 256 \
  --reference-sampling --reference-sampling-fallback argmax \
  --temperature 1.0 --top-p 1.0 --top-k 0 --epsilon-cutoff 0.001 \
  --output "$DRAMA3_RUN/out/base-laugh-42.wav" \
  --output-dir "$DRAMA3_RUN/out/base-laugh-42-codes"
```

[Installation prerequisites and extras](https://github.com/fishaudio/fish-speech/blob/0f8a12e8a651062fdee9c33a894bdccd3a8513f1/docs/en/install.md) · [Codec CLI](https://github.com/fishaudio/fish-speech/blob/0f8a12e8a651062fdee9c33a894bdccd3a8513f1/fish_speech/models/dac/inference.py#L50) · [Native synthesis CLI](https://github.com/fishaudio/fish-speech/blob/0f8a12e8a651062fdee9c33a894bdccd3a8513f1/fish_speech/models/text2semantic/inference.py#L1134)

## Training forward to implement

The pseudocode calls methods from the pinned Python source. Row construction, the loss reduction, adapter wiring and the uncached-versus-cached oracle need implementation and testing. There is no training command until these checks pass.

```text
load FishOmniModel.from_pretrained in BF16 with FP8 expert buffers disabled
freeze all model parameters and keep cache capacity at zero
wrap backbone.model.layers.{36,37,38}.linear_attn.out_proj
wrap backbone.model.layers.39.self_attn.o_proj
each wrapper adds (alpha / rank) * B(A(x)) to the frozen projection
use rank=8, alpha=8, FP32 factors with BF16 matmuls, B initialized to zero

prompt = build_drama3_prompt(tagged_text, tokenizer, config, refs_text, refs_codes)
rows = concat(prompt, target_audio_rows, one_eos_row)  # [T+1, 11]
x, y = rows[:-1], rows[1:]
assert T <= 256 and do not truncate an utterance to fit
semantic_loss = shifted label belongs to target audio
eos_loss = shifted label is the final target EOS
injection = tower.is_semantic(y[:, 0])                 # includes reference context
positions = arange(T)                                  # single example, no pad

fused = tower.embed_backbone(x, backbone.embed(x[:, 0]))
h = backbone(inputs_embeds=fused[None])[0]
L_eos = full_vocab_CE(backbone.compute_logits(h[eos_loss]), y[eos_loss, 0])
L_sem = full_vocab_CE(backbone.compute_logits(h[semantic_loss]), y[semantic_loss, 0])

state = tower.run_shared(h, y[:, 1], injection, positions, x)
for i in 0..8:
    state = tower.residual_layers[i](state, y[:, i+1], injection, positions)
    logits = tower.codebook_heads[i](state[semantic_loss])
    L_res[i] = CE(logits.float(), y[semantic_loss, i+2])
L = L_eos + 0.5 * L_sem + 0.5 * mean(L_res)
```

Install the wrappers after loading the pinned weights. Keep a switch that bypasses only the LoRA branch. Use the two boolean loss masks for row indexing. Compute CE in FP32. The frozen prefix can run in `no_grad` and produce an ordinary tensor. Avoid inference-mode tensors at the autograd boundary. Since the first adapters are in block 36, the reference implementation can also leave global grad mode enabled and assert that intermediate outputs before the first adapter do not require gradients. The remaining frozen MoE and tower operations must keep their input gradients. If memory requires it, checkpoint the gradient-bearing blocks with non-reentrant recomputation and verify identical masks and toleranced gradients. Keep train and synth model instances separate so inference caches cannot leak into training.

A standalone residual/tower-only cached-feature prototype would be simpler to fit and can test acoustic CE. Its trainable parameters cannot directly change the backbone's first semantic/EOS prediction. It cannot establish the behavior of the backbone adapter proposed here.

## Gates and success criteria

1. **Metadata, conditioning and base.** Reproduce the tensor counts and key shapes in [SOURCES.md](SOURCES.md), confirm exactly four target modules and 196,608 trainable scalars, render tagged/plain base takes, and retain all failures. Record sampler, seeds and codec round-trip. Proceed to an adaptation pilot if the validation set shows a repeatable gap. The standalone plumbing test may still be run to verify training.
2. **One-example forward.** First compare the disabled-adapter training logits against an instrumented native teacher-forced prefill using the same rows, shifted labels and BF16 weights. Native prefill has no residual logit return, so capture inputs to each residual head and project in the oracle. Compare cached versus uncached hidden states and logits at the first target frame, interior frames and EOS. Measure repeat-run numerical noise and declare tolerance before evaluating adapter parity. Assert `F` semantic, `F` labels per residual head and one EOS label, no scored prefix or references, finite per-head and total losses. Compare loss to a hand-computed toy row. Perturb future frames and the current head's own label while holding its allowed context fixed; earlier predictions and that head's logits must stay equal within tolerance. Lower-order code inputs may change higher heads.
3. **One backward and optimizer step.** Use AdamW, constant `2e-4`, FP32 factors, zero dropout and one microbatch. These are experiment settings. Check finite, nonzero gradients in each adapter's initially trainable B factor, and in A after B changes and another backward. Track norms for semantic/EOS and residual loss separately to verify the latter reaches the backbone adapters. Assert no frozen gradients, no optimizer entries for frozen tensors, and unchanged frozen tensor samples or chunked checksums. Assert the step changes expected adapter factors and selected predictions. Record load, forward, backward and step peaks and timings, available RAM and GPU headroom. Stop before a longer run if driver headroom falls below 4 GiB on the allocated card or the graph path fails.
4. **Tiny overfit.** Use one tagged/plain pair or two pairs from train. Alternate examples for at most 100 steps, batch 1 and no padding. Keep the seed, order and optimizer settings fixed. Proposed pass: at least 10% lower paired teacher-forced total loss than step zero, finite component losses, and measurable parameter updates. If it misses, check gradients and off-by-one labels before changing settings. Overfit verifies the training plumbing only.
5. **Save and reload.** Store adapter tensors as safetensors plus a JSON manifest with base and code SHA, exact names, ranks, alpha, dtype and hashes. Include optimizer state separately only for resuming. Require exact adapter keys/shapes/dtypes and byte-identical saved factors after a fresh load. Check active-adapter logits against the pre-save run, and disabled-adapter logits against the pre-training base. With matched backend and seeds compare pre/post-save codes, and diagnose any numerical mismatch before accepting the artifact. If later training embeddings or tower weights, persist their complete selected state and verify it separately. If later exporting a merged dense adapter, add ΔW to the correct BF16 weight with explicit dtype/cast handling and verify merged versus unmerged logits and synthesis on the same backend before quantizing or changing servers.
6. **Bounded held-out comparison.** After the gates pass, optionally train one capped pass (48 updates, constant settings, no test tuning) with a separate run ID. Compare base and adapted on all 12 held-out text pairs, both prompt variants, three fixed seeds and one held-out neutral reference per speaker. Randomize audio IDs and have two listeners score whether a genuine short laugh occurred at the requested phrase boundary, laugh false positives on plain prompts, whether the bracket cue was read aloud, post-event intelligibility and voice similarity. Report disagreement and raw denominators. Include a few fixed sigh and cough prompts as exploratory transfer checks. Score lexical WER/CER with a pinned ASR and normalization rule, and optionally a pinned speaker-verification encoder. ASR does not score whether a laugh, sigh or cough sounded natural or occurred at the right time. Log duration, empty output, unintended silence of at least 1 s confirmed by listening, incomplete text, runaway/frame cap, cold/warm synthesis wall time, real-time factor and memory. Retain the native CLI's `finish=eos` or `finish=length` log for each take, and log the same finish reason in the adapted runner. Keep every attempted take in the failure-rate denominator. Report conditional lexical metrics and counts of failures together.

An exploratory behavior signal is higher paired boundary adherence on tagged takes without more plain false positives, incomplete/empty/capped takes, or a consistent drop in lexical accuracy or voice similarity. Report per-speaker and per-seed counts even if the pilot misses that criterion. Two test speakers cannot establish generalization.

## Execution status

- **Executed:** read-only machine and GPU telemetry, source checkouts and static inspection, pinned JSON/tokenizer/codec metadata checks, remote safetensors header inspector across 31 shards, FFmpeg normalization of a generated stereo fixture to 44.1 kHz mono PCM, and small byte-range fingerprints recorded in [SOURCES.md](SOURCES.md).
- **Prepared:** manifest contract, source-checked normalization/extraction/synthesis commands, teacher-forced pseudocode, and ordered pass/fail gates.
- **Pending:** consented recordings, runtime dependency setup, waveform codec extraction, baseline synthesis, no-cache logit parity, backward, optimizer step, overfit, save/reload and listening tests. No checkpoint was loaded and no training job ran.
