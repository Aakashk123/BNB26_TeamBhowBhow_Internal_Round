from pathlib import Path
from typing import Any, cast

import yaml

from app.core.hashing import sha256

ROOT = Path(__file__).resolve().parents[3]


def load_policy() -> tuple[dict[str, Any], str]:
    raw = (ROOT / "config/trust_policy.yaml").read_bytes()
    return cast(dict[str, Any], yaml.safe_load(raw)), sha256(raw)
