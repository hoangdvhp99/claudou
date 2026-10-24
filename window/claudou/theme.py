"""Windows palette, shared by value with the macOS app only for the brand colors (docs/SPEC.md §5.1).

Surfaces, text and borders are (light, dark) pairs so the UI follows the Windows app mode; customtkinter
picks the matching entry. The accent, success and profile colors are the same on every platform.
"""
import sys
from pathlib import Path

# Shared brand colors (macOS: Theme.swift)
ACCENT = "#e8590c"
ACCENT_HOVER = "#c94a08"
SUCCESS = "#5fb878"
SUCCESS_STRONG = "#2f9e5b"       # fill behind white text
SUCCESS_HOVER = "#27854c"

PROFILE_COLORS = ["#e8590c", "#f59f00", "#d9480f", "#c2255c",
                  "#7048e8", "#1c7ed6", "#0ca678", "#868e96"]

# Windows surfaces: (light, dark)
BG = ("#f3f3f3", "#202020")
CARD = ("#ffffff", "#2b2b2b")
CARD_HOVER = ("#e9e9e9", "#383838")
INPUT = ("#ffffff", "#1c1c1c")
BORDER = ("#dcdcdc", "#3d3d3d")
BUTTON = ("#e6e6e6", "#3a3a3a")
BUTTON_HOVER = ("#d8d8d8", "#474747")
TEXT = ("#1a1a1a", "#f5f5f5")
DIM = ("#6b6b6b", "#a3a3a3")
SUCCESS_BG = ("#dff3e6", "#243a2c")
WARNING_BG = ("#fde8d8", "#4a2f1c")


def asset(name: str) -> Path:
    """Resolve a file in the repo's assets/ folder (or the PyInstaller bundle)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return base / "assets" / name
