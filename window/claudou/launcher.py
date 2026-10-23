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
    return ""


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

def _windows_of(pid: int) -> list[int]:
    user32 = ctypes.windll.user32
    found: list[int] = []
    proto = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def cb(hwnd, _):
        owner = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True

    user32.EnumWindows(proto(cb), 0)
    return found


def focus(pid: int):
    user32 = ctypes.windll.user32
    for hwnd in _windows_of(pid):
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.SetForegroundWindow(hwnd)


def quit_pid(pid: int):
    """Ask Claude to close its windows; terminate the process tree if it is still alive after 10s."""
    import psutil
    try:
        proc = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return
    for hwnd in _windows_of(pid):
        ctypes.windll.user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
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
