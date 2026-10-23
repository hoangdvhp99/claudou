import sys
from pathlib import Path

APP_NAME = "Claudou"


def _version() -> str:
    """Single source of truth: the VERSION file at the repo root (bundled next to the exe when frozen)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    try:
        return (base / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "0.0.0"


APP_VERSION = _version()
