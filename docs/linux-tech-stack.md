# Linux (Ubuntu) — technology stack proposal

Status: **proposal, not implemented.** Behavior must follow [SPEC.md](SPEC.md); this document only chooses the stack.

## Constraints specific to Linux

- Anthropic does not ship an official Claude Desktop for Linux. Users run a community repackaging (`.deb`, AppImage…), so the executable path varies (`/usr/bin/claude-desktop`, `~/Applications/*.AppImage`, …) → the **Claude executable setting + auto-detect** (SPEC F-07) matters more here. Electron still honors `--user-data-dir`, so the core mechanism (SPEC §2) is unchanged. Default data folder: `~/.config/Claude`.
- Ubuntu's default desktop is **GNOME**. System tray icons use **AppIndicator** (menus only, no popover) and need the `ubuntu-appindicators` extension, which Ubuntu enables by default.
- **Wayland** forbids focusing another app's window. "Show" can't rely on `xdotool`/`wmctrl`; re-running the same command with the same `--user-data-dir` makes Electron's single-instance lock raise the existing window (verify per build), with `wmctrl` as an X11-only fallback.
- Process discovery: read `/proc/<pid>/cmdline` (or `psutil`); main process = no `--type=` argument.

## Options

| Option | Fit for Ubuntu | Pros | Cons |
|---|---|---|---|
| **A. Python 3 + GTK4 + libadwaita (PyGObject) + AyatanaAppIndicator3** | Native GNOME look, preinstalled libs | Smallest footprint; no toolchain to build; mirrors the Windows codebase language (shared mental model, same `psutil` logic, same unit tests); `.deb` is simple | Needs system packages (`python3-gi`, `gir1.2-ayatanaappindicator3-0.1`); Python GUI startup ~200 ms |
| B. Tauri 2 (Rust + React/TS/Tailwind) | Works, WebKitGTK UI | Matches the company's frontend stack; ~10 MB bundle | **Tray click events are not emitted on Linux** (menu only); web UI feels non-native; Rust + Node toolchain |
| C. Qt 6 (PySide6) | Good on KDE, OK on GNOME | One toolkit for all DEs; `QSystemTrayIcon` | 100+ MB runtime; looks foreign on GNOME |
| D. Rust + gtk4-rs | Native | Single static-ish binary, fastest | Steepest learning curve; slower to iterate |
| E. Electron | Works | Reuse web skills | Ships a second Chromium just to launch Claude's Chromium |

## Recommendation: **Option A — Python 3 + GTK4/libadwaita + AppIndicator**

Rationale: native to Ubuntu, smallest effort that still feels first-class, reuses the Windows app's logic and tests (`store`, `launcher.match_profiles`, command building), and the "separate native app per OS, no shared code" rule is kept — only the *design* is shared via SPEC.md. Choose **D (Rust + GTK4)** later if startup time or packaging size becomes an issue.

### UI mapping (SPEC §5)

| Spec surface | Linux implementation |
|---|---|
| Launcher (popover) | AppIndicator **menu**: one entry per profile (`● Work — Show` / `Work — Open`), *Quit this Claude* submenu items, **Settings…**, **Quit Claudou** |
| Settings window | `Adw.ApplicationWindow` + `Adw.PreferencesGroup`: Claude executable row, profile list with Edit / Delete |
| Profile editor | `Adw.Window` dialog with the §5.4 fields |
| Palette / square corners | custom CSS provider (`border-radius: 0`, tokens from SPEC §5.1) |

### Proposed layout

```
linux/
├── claudou/            # package: store.py, launcher.py, ui.py, tray.py
├── tests/              # same cases as window/tests (adapt paths)
├── packaging/          # debian/ control + .desktop + icon
└── README.md
```

Config in `~/.config/claudou/config.json` (same schema, SPEC §4). Autostart via `~/.config/autostart/claudou.desktop` (optional).

### Milestones

1. Port `store.py` / `launcher.py` (Linux paths, `/proc` discovery) + tests.
2. Tray menu with Open / Show / Quit this Claude.
3. Settings + editor windows.
4. `.deb` build (`dpkg-deb`), icon from `assets/logo.png`.
5. Fill the Linux column of the parity matrix in SPEC §7.
