# Claudou — Product Specification

**Source of truth for all platforms.** The macOS, Windows and Linux apps are separate native implementations; they must behave the same way as described here. Rules for changing this file: [CONTRIBUTING.md](CONTRIBUTING.md).

## 1. Purpose

Run several Claude Desktop accounts on one computer, in parallel. Each account is a *profile* with its own login session, chat history and MCP configuration.

## 2. Core mechanism

Claude Desktop is an Electron app. A profile is simply a separate **user-data folder**; the app is started once per profile:

| Platform | Launch command (generated) |
|---|---|
| macOS | `open -n -a '<Claude.app>' --args --user-data-dir='<dir>'` |
| Windows | `"<claude.exe>" --user-data-dir=<dir>` (via `CreateProcess`, no shell) |
| Linux | `<claude executable> --user-data-dir=<dir>` |

The **Default** profile passes **no flag** and therefore uses Claude's own data folder (macOS `~/Library/Application Support/Claude`, Windows `%APPDATA%\Claude`, Linux `~/.config/Claude`). The tool never moves, copies or deletes that folder.

## 3. Behavior rules

| ID | Rule |
|---|---|
| B-1 | Profiles run in parallel. Opening a profile never quits another one. |
| B-2 | A profile is *running* when a Claude **main** process (not an Electron `--type=` child) exists whose `--user-data-dir` equals the profile folder. Default = a main process with no `--user-data-dir`. Paths compare normalized (Windows: case-insensitive). |
| B-3 | **Open** on a stopped profile runs its launch command. **Show** on a running profile brings its window to the front (never starts a second instance). |
| B-4 | **Quit this Claude** asks the app to close like ⌘Q / window-close and waits up to **10 s**; only then force-terminates. |
| B-5 | The launch command is saved per profile. Unless `commandEdited` is true it is **regenerated** at launch from the current Claude path and the profile folder; when true it is used verbatim. |
| B-6 | An empty data folder means *Claudou-owned*: `<claudou root>/profiles/<id>`, created on save. A chosen folder is *external*. |
| B-7 | Delete: **Default can't be deleted; a running profile can't be deleted.** Deleting a Claudou-owned profile erases its folder (confirmation required). Deleting an external profile only removes it from the list. |
| B-8 | `id` = slug of the name (lowercase ASCII, diacritics stripped, `đ→d`, non-alphanumerics → `_`); duplicates get `_2`, `_3`… The Default profile's id is `default`. |
| B-9 | Running state refreshes every ~2 s. Launch errors are shown to the user; nothing is silently swallowed. |
| B-10 | No admin/root rights are required. |

## 4. Data

Claudou root: macOS `~/Library/Application Support/Claudou` · Windows `%LOCALAPPDATA%\Claudou` · Linux `~/.config/claudou` (planned).

`config.json` — JSON array, identical on every platform:

```json
[
  { "id": "default", "name": "Default", "colorHex": "#e8590c", "commandEdited": false },
  { "id": "work", "name": "Work", "colorHex": "#1c7ed6",
    "dataDir": "/path/to/folder", "command": "…", "commandEdited": true,
    "lastUsed": "2026-10-23T10:36:38Z" }
]
```

`dataDir`, `command`, `lastUsed` are omitted when empty. Dates are UTC ISO-8601 (`yyyy-MM-ddTHH:mm:ssZ`). Unknown keys must be ignored.

The path to the Claude app/executable is a per-platform setting (macOS `UserDefaults: claudeAppPath`, Windows `settings.json: claudeExePath`). Default: macOS `/Applications/Claude.app`; Windows/Linux auto-detected.

## 5. UI specification

Language: **English only**. Compact density, orange accent. Every platform follows the system look; only the brand colors are shared.

**macOS 26 (reference):** follows the system appearance and uses system semantic colors. Settings and the editor are translucent windows (behind-window vibrancy, transparent title bar) with flat rounded cards (radius 16) on a large bold title. Controls are native: `.bordered` for secondary and `.borderedProminent` tinted with the accent for primary actions; the launcher uses small filled pills. Older macOS falls back to the same styles without glass.

**Windows:** follows the Windows app mode (light/dark) with neutral Windows 11 surfaces, rounded cards (radius 14), rounded controls (radius 8), pills for Open/Show. Same layout as macOS.

**Linux:** planned, libadwaita defaults (see [linux-tech-stack.md](linux-tech-stack.md)).

### 5.1 Colors

Shared by all platforms:

| Token | Hex | Use |
|---|---|---|
| accent | `#e8590c` | Open pill, primary buttons, switch |
| accent hover | `#c94a08` | Windows hover/pressed |
| success | `#5fb878` | `Running`, `N running`, found banner |
| success strong | `#2f9e5b` | Show pill fill (white text) |

Profile colors: `#e8590c #f59f00 #d9480f #c2255c #7048e8 #1c7ed6 #0ca678 #868e96`.

Surfaces, text, borders and secondary buttons are platform-native: macOS system colors, Windows (light, dark) pairs in `window/claudou/theme.py`.

### 5.2 Launcher (menu bar popover / tray window / tray menu)

A menu-style, launch-only surface, ~340 pt wide, no section label above the list.

- **Header:** rounded logo (30), "Claudou", and below it the status text — `N running` (success color) or `Idle`. Hairline divider.
- **Row** (48 pt, the hover highlight fills the whole row, rows 2 pt apart): rounded avatar (30, profile color, white initial) · name · subtitle (`Running` / `Never opened` / `Opened MMM d, HH:mm`) · pill **Open** (accent) or **Show** (success strong) · ✕ *Quit this Claude* only while running · double-click = Open/Show. The ✕ slot is always reserved so Open/Show line up across rows.
- **Divider**, then plain menu rows: **Settings…** · **Quit** (shortcut ⌘Q on macOS, Ctrl+Q on Windows).

Linux may use a tray *menu* with the same entries because AppIndicator has no popover.

### 5.3 Settings window

Header: rounded logo (56), **Claudou** (26 bold), subtitle "Run several Claude accounts side by side." Then, as cards:

1. **Claude app/executable** (macOS `Claude.app`, Windows `Claude executable`) — path field, **Browse…**, **Reset** (macOS) / **Auto-detect** (Windows, Linux). Below it a status banner, green `Claude found` or orange `Not found at this path`. Saved automatically as you type.
2. **Launch at startup** — switch with the hint "Start Claudou in the menu bar when your computer starts." (Windows: "…in the tray…"). macOS uses `SMAppService` (a hint explains approval in Login Items if needed); Windows writes the per-user `Run` key and is available only in the packaged `.exe`.
3. **Profiles** — title with **+ New profile** (accent); one card per profile: avatar (40), name, `RUNNING` / `DEFAULT` tags, folder path, *Reveal folder*, **Edit**, *Delete* (red; disabled per B-7).

### 5.4 Profile editor

Title **New profile** / **Edit profile**, then one card with sentence-case labels: **Name** · **Color** (8 round swatches) · **Data folder (--user-data-dir)** (hidden for Default; placeholder "Leave empty to create one in Claudou/profiles", **Choose…**) · **Launch command** (monospace; hint "Generated from …" or "Edited by hand — used exactly as written."; **Regenerate** appears only when edited). Below the card: **Cancel** / **Save** (accent, disabled while name is empty).

### 5.5 Branding

`assets/logo.png` is the app icon and header logo; `assets/logo-menubar.png` is the monochrome glyph for template-style tray icons (macOS). Windows/Linux tray icons use `logo.png`.

## 6. Platform mapping

| Concern | macOS | Windows | Linux (planned) |
|---|---|---|---|
| Stack | Swift 5.9 / SwiftUI (macOS 13+, macOS 26 look) | Python 3.12 / customtkinter | Python 3 / GTK4 + libadwaita |
| Launcher surface | `MenuBarExtra` popover | Compact window + system tray | AppIndicator menu |
| Process discovery | `ps` command lines | `psutil` | `/proc/*/cmdline` (psutil) |
| Show | `NSRunningApplication.activate` | `SetForegroundWindow` | re-run command (Electron single-instance) / `wmctrl` on X11 |
| Quit | `NSRunningApplication.terminate` | `WM_CLOSE` → terminate tree | `SIGTERM` → `SIGKILL` |
| Launch at startup | `SMAppService.mainApp` | `HKCU\\…\\Run` value (packaged exe) | autostart `.desktop` entry |
| Package | `build_app.sh` → `.app` | `build_exe.ps1` → `.exe` | `.deb` |

## 7. Feature parity matrix

Update this table in **every** PR that adds or changes a feature. Status: ✅ done · 🟡 partial/untested · ⏳ planned · ➖ not applicable.

| ID | Feature | macOS | Windows | Linux |
|---|---|---|---|---|
| F-01 | Parallel profiles via `--user-data-dir` (B-1) | ✅ | 🟡 untested on a real install | ⏳ |
| F-02 | Default profile uses Claude's own folder (B-6) | ✅ | 🟡 | ⏳ |
| F-03 | Running detection per profile (B-2) | ✅ | 🟡 (unit-tested matching) | ⏳ |
| F-04 | Open / Show / Quit this Claude (B-3, B-4) | ✅ | 🟡 | ⏳ |
| F-05 | Profile CRUD in Settings (B-7, B-8) | ✅ | 🟡 | ⏳ |
| F-06 | Editable saved launch command (B-5) | ✅ | 🟡 | ⏳ |
| F-07 | Claude path setting + auto-detect | ✅ | 🟡 | ⏳ |
| F-08 | Native look, English strings (§5) | ✅ macOS 26 | 🟡 Windows 11 style, UI untested | ⏳ |
| F-09 | Tray / menu bar presence | ✅ menu bar | 🟡 tray (needs `pystray`) | ⏳ |
| F-10 | App icon + branding | ✅ | 🟡 | ⏳ |
| F-11 | Shared `config.json` schema (§4) | ✅ | ✅ | ⏳ |
| F-12 | Single `VERSION` file | ✅ | ✅ | ⏳ |
| F-13 | Launch at startup switch (§5.3) | ✅ `SMAppService` | 🟡 `Run` key, packaged exe only | ⏳ |
