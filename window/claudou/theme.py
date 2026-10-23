"""Dark-orange palette shared (by value) with the macOS app: macOS/Claudou/Sources/Claudou/Theme.swift."""
import sys
from pathlib import Path

ACCENT = "#e8590c"
ACCENT_HOVER = "#c94a08"
BG = "#140f0b"
SURFACE = "#1b1410"
CARD = "#241a14"
CARD_HOVER = "#2d2018"
INPUT = "#100b08"
BORDER = "#3a2b21"
TEXT = "#f5ece4"
DIM = "#a38f80"
SUCCESS = "#5fb878"

PROFILE_COLORS = ["#e8590c", "#f59f00", "#d9480f", "#c2255c",
                  "#7048e8", "#1c7ed6", "#0ca678", "#868e96"]


def asset(name: str) -> Path:
    """Resolve a file in the repo's assets/ folder (or the PyInstaller bundle)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return base / "assets" / name
