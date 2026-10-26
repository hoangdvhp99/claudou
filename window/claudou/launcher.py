"""Everything that touches Claude Desktop: command building, process discovery, focus and quit.

Each profile is a separate Claude process started with --user-data-dir, so profiles run in
parallel and Claude's own data folder is never modified.
"""
from __future__ import annotations

import ctypes
import ntpath
import os
import subprocess
import sys
import time
from functools import lru_cache
from pathlib import Path

FLAG = "--user-data-dir="
QUIT_TIMEOUT = 10.0


# ── Claude executable ──

def detect_claude_exe() -> str:
    """Best-effort lookup of claude.exe (Store/MSIX, per-user installer, Program Files)."""
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    candidates: list[Path] = []
    windows_apps = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "WindowsApps"
    try:
        candidates += sorted(windows_apps.glob("Claude_*_x64__*/app/claude.exe"), reverse=True)
    except OSError:
        pass
    candidates += [
        local / "AnthropicClaude" / "claude.exe",
        local / "Programs" / "claude" / "Claude.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Claude" / "Claude.exe",
    ]
    for c in candidates:
        if str(c) not in ("", ".") and c.exists():
            return str(c)
    return _store_exe()


@lru_cache(maxsize=1)
def _store_exe() -> str:
    """WindowsApps can't be listed without admin rights, so ask the package manager for the Store install."""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             "(Get-AppxPackage -Name Claude | Select-Object -First 1).InstallLocation"],
            capture_output=True, text=True, timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""
    exe = Path(out) / "app" / "Claude.exe" if out else None
    return str(exe) if exe and exe.exists() else ""


# ── Commands ──

def build_command(exe: str, data_dir: str | None) -> str:
    """`claude.exe [--user-data-dir=<dir>]`; the default profile passes no flag."""
    args = [exe]
    if data_dir:
        args.append(f"{FLAG}{data_dir}")
    return subprocess.list2cmdline(args)


def run_command(command: str, exe: str):
    if not exe or not Path(exe).exists():
        raise RuntimeError("Claude executable not found. Set its path in Settings.")
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    try:
        subprocess.Popen(command, creationflags=flags, close_fds=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as e:
        raise RuntimeError(f"Could not open Claude: {e}") from e


# ── Process discovery ──

def _norm(path: str) -> str:
    return ntpath.normcase(ntpath.normpath(path.strip().strip('"')))


def main_processes() -> list[tuple[int, list[str]]]:
    """(pid, argv) of running Claude main processes (Electron children carry --type=)."""
    import psutil
    out = []
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            name = (p.info["name"] or "").lower()
            args = p.info["cmdline"] or []
            if name == "claude.exe" and not any(a.startswith("--type=") for a in args):
                out.append((p.info["pid"], args))
        except Exception:
            continue
    return out


def match_profiles(procs: list[tuple[int, list[str]]],
                   profiles: list[tuple[str, str | None]]) -> dict[str, int]:
    """Map profile id → pid. `profiles` holds (id, data_dir); data_dir None means the default profile."""
    result: dict[str, int] = {}
    by_dir = {_norm(d): pid_ for pid_, d in profiles if d}
    default_id = next((pid_ for pid_, d in profiles if d is None), None)
    for pid, args in procs:
        flag = next((a for a in args if a.startswith(FLAG)), None)
        if flag is None:
            if default_id:
                result[default_id] = pid
        else:
            pid_ = by_dir.get(_norm(flag[len(FLAG):]))
            if pid_:
                result[pid_] = pid
    return result


def running_pids(profiles: list[tuple[str, str | None]]) -> dict[str, int]:
    return match_profiles(main_processes(), profiles)


# ── Window control (Windows only) ──

def _windows_of(pid: int, visible_only: bool = True) -> list[int]:
    user32 = ctypes.windll.user32
    found: list[int] = []
    proto = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def cb(hwnd, _):
        owner = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and (not visible_only or user32.IsWindowVisible(hwnd)):
            found.append(hwnd)
        return True

    user32.EnumWindows(proto(cb), 0)
    return found


def _class_name(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(64)
    ctypes.windll.user32.GetClassNameW(hwnd, buf, 64)
    return buf.value


def focus(pid: int):
    user32 = ctypes.windll.user32
    for hwnd in _windows_of(pid):
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.SetForegroundWindow(hwnd)


def _request_exit(pid: int):
    """WM_CLOSE only hides Claude to the tray. Claude quits on a Windows `session-end` event, which Electron
    raises from WM_QUERYENDSESSION + WM_ENDSESSION(ENDSESSION_CLOSEAPP) sent to its app windows, hidden or not."""
    user32 = ctypes.windll.user32
    result = ctypes.c_ulong()
    for hwnd in _windows_of(pid, visible_only=False):
        if _class_name(hwnd) != "Chrome_WidgetWin_1":
            continue
        for msg, wparam in ((0x0011, 0), (0x0016, 1)):  # WM_QUERYENDSESSION, WM_ENDSESSION
            user32.SendMessageTimeoutW(hwnd, msg, wparam, 1, 2, 1000, ctypes.byref(result))  # SMTO_ABORTIFHUNG


def quit_pid(pid: int):
    """Ask Claude to exit cleanly; terminate the process tree if it is still alive after 10s."""
    import psutil
    try:
        proc = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return
    _request_exit(pid)
    deadline = time.time() + QUIT_TIMEOUT
    while time.time() < deadline:
        if not proc.is_running():
            return
        time.sleep(0.25)
    try:
        for child in proc.children(recursive=True):
            child.terminate()
        proc.terminate()
    except psutil.NoSuchProcess:
        pass
