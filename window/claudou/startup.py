"""Launch Claudou when the user signs in (per-user Run key, no admin rights). docs/SPEC.md §5.3."""
from __future__ import annotations

import sys

_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE = "Claudou"


def supported() -> bool:
    """Only the packaged Claudou.exe can register itself; a source checkout has no stable executable."""
    return sys.platform == "win32" and bool(getattr(sys, "frozen", False))


def is_enabled() -> bool:
    if not supported():
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _KEY) as key:
            winreg.QueryValueEx(key, _VALUE)
            return True
    except OSError:
        return False


def set_enabled(on: bool) -> None:
    """Raises OSError when the registry cannot be changed."""
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _KEY, 0, winreg.KEY_SET_VALUE) as key:
        if on:
            winreg.SetValueEx(key, _VALUE, 0, winreg.REG_SZ, f'"{sys.executable}"')
        else:
            try:
                winreg.DeleteValue(key, _VALUE)
            except FileNotFoundError:
                pass
