"""TOML-backed config at ~/.spartastruct/config.toml."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import tomli_w

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[no-redef]

CONFIG_DIR = Path.home() / ".spartastruct"
CONFIG_FILE = CONFIG_DIR / "config.toml"

_DEFAULT_MODEL = "anthropic/claude-haiku-4-5-20251001"


@dataclass
class Config:
    model: str = _DEFAULT_MODEL
    api_keys: dict[str, str] = field(default_factory=dict)
    output_dir: str = "spartadocs"


def load_config() -> Config:
    """Load config from ~/.spartastruct/config.toml, returning defaults if absent."""
    if not CONFIG_FILE.exists():
        return Config()
    raw = CONFIG_FILE.read_bytes()
    data = tomllib.loads(raw.decode())
    return Config(
        model=data.get("model", _DEFAULT_MODEL),
        api_keys=data.get("api_keys", {}),
        output_dir=data.get("output_dir", "spartadocs"),
    )


def save_config(config: Config) -> None:
    """Write config to ~/.spartastruct/config.toml."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data: dict = {
        "model": config.model,
        "output_dir": config.output_dir,
    }
    if config.api_keys:
        data["api_keys"] = config.api_keys
    CONFIG_FILE.write_bytes(tomli_w.dumps(data).encode())
