# Claudou for Windows

Runs multiple Claude Desktop accounts side by side (Python + customtkinter, system tray). Behavior and UI follow [docs/SPEC.md](../docs/SPEC.md); the macOS app is the reference implementation.

> **Status:** logic is unit-tested, but the UI and the `--user-data-dir` launch have **not yet been verified on a real Windows install**. See [ISSUES.md](ISSUES.md).

## How it works

Every profile is a separate Claude process with its own data folder:

```
"C:\...\claude.exe" --user-data-dir=<profile folder>
```

- Profiles run in parallel; nothing is quit to open another profile.
- **Default** launches Claude without flags and uses Claude's own folder (`%APPDATA%\Claude`); it is never moved or deleted.
- A profile counts as running when a `claude.exe` main process has a matching `--user-data-dir` (read with `psutil`).
- *Show* focuses the window; *Quit this Claude* sends `WM_CLOSE` and terminates the process tree after 10 s.

```
%LOCALAPPDATA%\Claudou\
├── config.json        # profile list (same schema as macOS)
├── settings.json      # path to claude.exe
└── profiles\<name>\   # data folder for profiles created by Claudou
```

## Run from source

```powershell
cd window
pip install -r requirements.txt
python -m claudou
```

Tests (any OS): `python -m unittest discover -s tests`

## Build `Claudou.exe`

```powershell
cd window
.\build_exe.ps1 -Install      # → dist\Claudou.exe
```

## Usage

- **Launcher window** (bottom-right, hides to the tray on close): **Open** / **Show**, ✕ to quit that Claude.
- **Settings**: path to `claude.exe` (auto-detected for Store, per-user and Program Files installs) and profile **create / edit / delete**.

## Source layout

| File | Purpose |
|---|---|
| `claudou/store.py` | Profile model, persistence, settings |
| `claudou/launcher.py` | Command building, process discovery, focus/quit |
| `claudou/ui.py` | Launcher window, Settings, profile editor, tray |
| `claudou/theme.py` | Palette (same values as `Theme.swift`) |
| `tests/test_core.py` | Store + matching tests |
| `main.py` | PyInstaller entry point |

## Requirements

Windows 10/11 · Python 3.10+ (source) · Claude Desktop. No administrator rights needed.
