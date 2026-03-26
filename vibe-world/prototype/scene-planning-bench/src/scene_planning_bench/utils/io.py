from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def read_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text())


def read_data_file(path: Path) -> Any:
    if path.suffix in {".yaml", ".yml"}:
        return read_yaml(path)
    return read_json(path)


def load_env(path: Path) -> bool:
    if not path.exists():
        return False
    return load_dotenv(path, override=False)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True))


def utc_timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned or "run"
