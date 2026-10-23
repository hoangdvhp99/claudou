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

Language: **English only**. Style: **square corners everywhere**, dark-orange palette, compact density.

### 5.1 Palette

| Token | Hex | Token | Hex |
|---|---|---|---|
| accent | `#e8590c` | text | `#f5ece4` |
| accent hover | `#c94a08` | dim | `#a38f80` |
| background | `#140f0b` | success | `#5fb878` |
| surface | `#1b1410` | border | `#3a2b21` |
| card | `#241a14` | input | `#100b08` |
| card hover | `#2d2018` | | |

Profile colors: `#e8590c #f59f00 #d9480f #c2255c #7048e8 #1c7ed6 #0ca678 #868e96`.

### 5.2 Launcher (menu bar popover / tray window / tray menu)

Launch-only surface, ~300 pt wide.

- **Header:** logo (22), "Claudou", status text — `N running` (success color) or `Idle`.
- **Accent rule** (1 px) under the header.
- **Row** (44 px): square avatar (28, profile color, white initial) · name · subtitle (`Running` / `Never opened` / `Last opened MMM d, HH:mm`) · button **Open** (accent) or **Show** (success) · ✕ *Quit this Claude* only while running · double-click = Open/Show.
- **Footer:** **Settings** · **Quit Claudou**.

Linux may use a tray *menu* with the same entries because AppIndicator has no popover (see [linux-tech-stack.md](linux-tech-stack.md)).

### 5.3 Settings window

1. **Claude app/executable** — path field, **Browse…**, **Reset** (macOS) / **Auto-detect** (Windows, Linux); status line `Claude found` / `Not found at this path`. Saved automatically as you type.
2. **Profiles** — header with **+ New profile**; each row: avatar, name, `RUNNING` / `DEFAULT` tags, folder path, *Reveal folder*, **Edit**, *Delete* (disabled per B-7).

### 5.4 Profile editor

Fields in order: **Name** · **Color** (8 swatches) · **Data folder** (hidden for Default; placeholder "Leave empty to create one in Claudou/profiles", **Choose…**) · **Launch command** (monospace; hint "Generated from …" or "Edited by hand — used exactly as written."; **Regenerate** appears only when edited) · **Cancel** / **Save** (disabled while name is empty).

### 5.5 Branding

`assets/logo.png` is the app icon and header logo; `assets/logo-menubar.png` is the monochrome glyph for template-style tray icons (macOS). Windows/Linux tray icons use `logo.png`.

## 6. Platform mapping

| Concern | macOS | Windows | Linux (planned) |
|---|---|---|---|
| Stack | Swift 5.9 / SwiftUI | Python 3.12 / customtkinter | Python 3 / GTK4 + libadwaita |
| Launcher surface | `MenuBarExtra` popover | Compact window + system tray | AppIndicator menu |
| Process discovery | `ps` command lines | `psutil` | `/proc/*/cmdline` (psutil) |
| Show | `NSRunningApplication.activate` | `SetForegroundWindow` | re-run command (Electron single-instance) / `wmctrl` on X11 |
| Quit | `NSRunningApplication.terminate` | `WM_CLOSE` → terminate tree | `SIGTERM` → `SIGKILL` |
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
| F-08 | Square dark-orange UI, English strings (§5) | ✅ | 🟡 | ⏳ |
| F-09 | Tray / menu bar presence | ✅ menu bar | 🟡 tray (needs `pystray`) | ⏳ |
| F-10 | App icon + branding | ✅ | 🟡 | ⏳ |
| F-11 | Shared `config.json` schema (§4) | ✅ | ✅ | ⏳ |
| F-12 | Single `VERSION` file | ✅ | ✅ | ⏳ |
