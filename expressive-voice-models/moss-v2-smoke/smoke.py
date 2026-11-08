"""Run ten optimizer steps on the LAION MOSS v2 speech-and-burst fixtures."""

import argparse
import gc
import json
import random
import sys
import time
from pathlib import Path

import soundfile as sf
import torch
from peft import LoraConfig, get_peft_model
from transformers import AutoModel, AutoProcessor

ROOT = Path(__file__).resolve().parent / "run"
sys.path.insert(0, str(ROOT / "openmoss-trainer"))
from sft import compute_supervised_loss, configure_gradient_checkpointing  # noqa: E402

TARGETS = [
    "q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj",
    "c_attn", "c_proj", "fc_in", "fc_out",
    *(f"audio_lm_heads.{i}" for i in range(12)),
]
MAX_ROWS = 256
ACCUMULATION = 4
STEPS = 10
SEED = 314


def load_rows(model_path, codec_path):
    processor = AutoProcessor.from_pretrained(
        model_path, trust_remote_code=True, codec_path=str(codec_path),
        codec_compute_dtype="bf16", codec_attention_implementation="sdpa",
    )
    processor.audio_tokenizer.to("cuda").eval()
    config = processor.model_config
    assert config.n_vq == 12 and config.sampling_rate == 48000

    def encode(path):
        waveform, rate = sf.read(path, dtype="float32", always_2d=True)
        return processor.encode_audios_from_wav(torch.from_numpy(waveform.T), rate)[0]

    records = [json.loads(line) for line in (ROOT / "data" / "train.jsonl").read_text().splitlines()]
    batches = []
    references = {}
    with torch.inference_mode():
        for record in records:
            ref_path = record["ref_audio"]
            if ref_path not in references:
                references[ref_path] = encode(ref_path)
            codes = encode(record["audio"])
            assert codes.ndim == 2 and codes.shape[1] == 12 and codes.shape[0] > 0
            assert int(codes.min()) >= 0 and int(codes.max()) < config.audio_pad_token_id
            message = processor.build_user_message(
                text=record["text"], instruction=record["instruction"],
                language=record["language"], reference=[references[ref_path]],
            )
            prefix = processor([[message]], mode="generation")["input_ids"][0]
            assert int(prefix[-1, 0]) == config.audio_start_token_id
            audio = processor._build_audio_rows(codes, config.audio_assistant_slot_token_id)
            stop = processor._build_text_rows([config.audio_end_token_id])
            packed = torch.cat((prefix, audio, stop))
            assert packed.shape[0] <= MAX_ROWS, (record["id"], packed.shape[0])
            labels = packed[1:].clone()
            labels[:len(prefix) - 1] = -100
            labels[:, 1:].masked_fill_(labels[:, 1:] == config.audio_pad_token_id, -100)
            assert torch.equal(labels[len(prefix) - 1, 1:], codes[0])
            assert int(labels[-1, 0]) == config.audio_end_token_id
            batches.append((packed[:-1], labels))
            print(f'{record["id"]}: {len(prefix)} prompt rows, {len(codes)} audio frames', flush=True)

    processor.audio_tokenizer = None
    return [(ids.clone().unsqueeze(0), labels.clone().unsqueeze(0)) for ids, labels in batches]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "result")
    args = parser.parse_args()
    if not torch.cuda.is_available():
        raise SystemExit("CUDA is unavailable. Run this on the 4060 Ti host with GPU access.")
    free, total = torch.cuda.mem_get_info()
    print(f"{torch.cuda.get_device_name()}: {free / 2**30:.2f} GiB free of {total / 2**30:.2f} GiB", flush=True)
    if free < 12 * 2**30:
        raise SystemExit("The smoke test needs at least 12 GiB free before loading the model.")
    torch.manual_seed(SEED)
    rng = random.Random(SEED)
    torch.cuda.reset_peak_memory_stats()
    model_path = Path((ROOT / "model.path").read_text().strip())
    codec_path = Path((ROOT / "codec.path").read_text().strip())
    rows = load_rows(model_path, codec_path)
    codec_peak = torch.cuda.max_memory_reserved()
    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()

    base = AutoModel.from_pretrained(
        model_path, trust_remote_code=True, dtype=torch.bfloat16,
        attn_implementation="sdpa", device_map={"": 0},
    )
    model = get_peft_model(base, LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05, bias="none", target_modules=TARGETS,
    ))
    configure_gradient_checkpointing(base, scope="all", use_reentrant=False, impl="module_wrapper")
    model.train()
    trainable = [p for p in model.parameters() if p.requires_grad]
    assert trainable and all(p.dtype == torch.float32 for p in trainable)
    assert all("lora_" in name for name, p in model.named_parameters() if p.requires_grad)
    count = sum(p.numel() for p in trainable)
    print(f"{count:,} trainable LoRA parameters", flush=True)
    optimizer = torch.optim.AdamW(trainable, lr=1e-4, betas=(0.9, 0.95), weight_decay=0, foreach=False)

    tracked = next(p for name, p in model.named_parameters() if "lora_B" in name)
    before = tracked.detach().clone()
    order = list(range(len(rows)))
    history = []
    start = time.monotonic()
    for step in range(STEPS):
        optimizer.zero_grad(set_to_none=True)
        losses = []
        for micro in range(ACCUMULATION):
            index = (step * ACCUMULATION + micro) % len(order)
            if index == 0:
                rng.shuffle(order)
            ids, labels = (t.cuda() for t in rows[order[index]])
            with torch.autocast("cuda", dtype=torch.bfloat16):
                loss = compute_supervised_loss(
                    model, input_ids=ids, labels=labels,
                    attention_mask=torch.ones(ids.shape[:2], dtype=torch.bool, device=ids.device),
                    channelwise_loss_weight=[1.0] + [32 / 12] * 12,
                )
            value = loss.item()
            if not torch.isfinite(loss):
                raise RuntimeError(f"Non-finite loss at step {step + 1}, microbatch {micro + 1}")
            (loss / ACCUMULATION).backward()
            losses.append(value)

        norm = torch.nn.utils.clip_grad_norm_(trainable, 1.0, error_if_nonfinite=True).item()
        optimizer.step()
        torch.cuda.synchronize()
        metrics = {
            "step": step + 1, "loss": sum(losses) / len(losses), "grad_norm": norm,
            "peak_reserved_gib": torch.cuda.max_memory_reserved() / 2**30,
            "peak_allocated_gib": torch.cuda.max_memory_allocated() / 2**30,
            "seconds": time.monotonic() - start,
        }
        history.append(metrics)
        print(json.dumps(metrics), flush=True)
    if torch.equal(before, tracked):
        raise RuntimeError("The monitored LoRA tensor did not update.")

    args.output.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.output / "adapter")
    summary = {
        "gpu": torch.cuda.get_device_name(), "torch": torch.__version__,
        "seed": SEED, "examples": len(rows), "accumulation": ACCUMULATION,
        "codec_peak_reserved_gib": codec_peak / 2**30, "trainable_parameters": count,
        "steps": history,
    }
    (args.output / "metrics.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
