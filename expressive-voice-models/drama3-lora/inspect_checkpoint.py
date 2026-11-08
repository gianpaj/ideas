#!/usr/bin/env python3
"""Read pinned Hugging Face checkpoint metadata without loading tensor payloads."""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
import re
import struct
from urllib.request import Request, urlopen


MAX_HEADER = 2 * 1024 * 1024
MAX_INDEX = 8 * 1024 * 1024


def read_index(base_url):
    with urlopen(f"{base_url}/model.safetensors.index.json", timeout=30) as response:
        data = response.read(MAX_INDEX + 1)
    if len(data) > MAX_INDEX:
        raise ValueError("Index exceeds the download limit")
    return json.loads(data)["weight_map"]


def read_range(url, first, last):
    size = last - first + 1
    request = Request(url, headers={"Range": f"bytes={first}-{last}"})
    with urlopen(request, timeout=30) as response:
        content_range = response.headers.get("Content-Range", "")
        if response.status != 206 or not content_range.startswith(f"bytes {first}-{last}/"):
            raise ValueError("Server did not honor the requested byte range")
        data = response.read(size + 1)
    if len(data) != size:
        raise ValueError("Unexpected range length")
    return data


def read_header(base_url, shard):
    if not re.fullmatch(r"model-\d+-of-\d+\.safetensors", shard):
        raise ValueError(f"Unexpected shard name {shard!r}")
    url = f"{base_url}/{shard}"
    (size,) = struct.unpack("<Q", read_range(url, 0, 7))
    if not 0 < size <= MAX_HEADER:
        raise ValueError(f"Shard header exceeds the download limit ({size} bytes)")
    header = json.loads(read_range(url, 8, 7 + size))
    header.pop("__metadata__", None)
    return shard, size + 8, header


def component(name):
    if ".mlp.experts." in name:
        return "routed_expert_scales" if name.endswith(".weight_scale_inv") else "routed_experts"
    if name.startswith("audio_decoder"):
        return "audio_decoder"
    if name == "lm_head.weight":
        return "lm_head"
    if name == "model.language_model.embed_tokens.weight":
        return "token_embeddings"
    return "other_backbone"


def inspect(model, revision, tensor_patterns):
    base_url = f"https://huggingface.co/{model}/resolve/{revision}"
    index = read_index(base_url)
    shards = sorted(set(index.values()))
    totals = Counter()
    dtypes = Counter()
    tensors = {}
    header_bytes = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        for shard, size, header in pool.map(lambda s: read_header(base_url, s), shards):
            header_bytes += size
            for name, record in header.items():
                if index.get(name) != shard or name in tensors:
                    raise ValueError(f"Index and shard disagree for {name}")
                first, last = record["data_offsets"]
                totals[component(name)] += last - first
                dtypes[record["dtype"]] += last - first
                tensors[name] = [record["dtype"], record["shape"]]
    if set(tensors) != set(index):
        raise ValueError("Index and shard headers list different tensors")
    return {
        "model": model,
        "revision": revision,
        "shards": len(shards),
        "tensor_count": len(tensors),
        "shard_header_bytes_read": header_bytes,
        "tensor_bytes": sum(totals.values()),
        "bytes_by_component": dict(totals),
        "bytes_by_dtype": dict(dtypes),
        "selected_tensors": {
            name: tensors[name]
            for name in sorted(tensors)
            if any(pattern.search(name) for pattern in tensor_patterns)
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", help="Hugging Face owner/name")
    parser.add_argument("revision", help="Full 40-character checkpoint commit")
    parser.add_argument("--tensor", action="append", default=[], help="Regex for tensor names to print")
    args = parser.parse_args()
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", args.model):
        parser.error("model must be an owner/name")
    if not re.fullmatch(r"[0-9a-f]{40}", args.revision):
        parser.error("revision must be a full lowercase commit SHA")
    result = inspect(args.model, args.revision, [re.compile(pattern) for pattern in args.tensor])
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
