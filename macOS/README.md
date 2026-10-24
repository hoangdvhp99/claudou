# Claudou for macOS

A menu bar app (Swift + SwiftUI) that runs multiple Claude Desktop accounts side by side. Behavior and UI are defined in [docs/SPEC.md](../docs/SPEC.md); this is the reference implementation.

## How it works

Every profile is a separate Claude process started with its own data folder:

```
open -n -a '/Applications/Claude.app' --args --user-data-dir='<profile folder>'
```

- Profiles run **in parallel**; nothing needs to be quit first.
- The **Default** profile launches Claude without flags and uses Claude's own data folder (`~/Library/Application Support/Claude`). Claudou never moves or modifies it.
- Each profile saves its launch command. Unless you edit the command by hand, it is regenerated from the Claude.app path and the profile's data folder.
- A profile is shown as running when a Claude process with a matching `--user-data-dir` exists (detected with `ps`).

```
~/Library/Application Support/Claudou/
├── config.json        # profile list
└── profiles/<name>/   # data folder for profiles created by Claudou
```

## Build and run

Requirements: macOS 13+ (the macOS 26 look needs macOS 26), Xcode or a Swift toolchain. Rebuild with `./build_app.sh` after code changes: `swift build` alone does not update `build/Claudou.app`.

```bash
cd macOS/Claudou
./build_app.sh            # → build/Claudou.app (universal, ad-hoc signed)
open build/Claudou.app
```

During development: `swift run` (uses a fallback menu bar icon).

The app is not notarized; on first launch use right-click → Open if Gatekeeper complains.

## Usage

- **Menu bar popover** — a menu-style, launch-only list: **Open** / **Show** pills (Show brings a running profile to the front), ✕ to quit that Claude, then **Settings…** and **Quit** (⌘Q).
- **Settings**
  - Path to `Claude.app` (default `/Applications/Claude.app`).
  - **Launch at startup** switch (registers a login item with `SMAppService`; macOS may ask you to approve it in System Settings → General → Login Items). It only works from the built `.app`.
  - Profile management: **create, edit, delete**. A profile has a name, a color, a data folder (leave empty to create one under `Claudou/profiles`, or choose an existing folder such as `~/.claude-instances/work`) and an editable launch command.
- Sign in to the matching account the first time a new profile opens.

## Data safety

- Default profile data is never moved or deleted; the Default profile cannot be deleted.
- Deleting a profile that Claudou created erases its folder (after confirmation). Profiles that use a folder you chose are only removed from the list.
- A running profile cannot be deleted.
- "Quit this Claude" is a normal quit (⌘Q equivalent), forced only after 10 seconds.

## Source layout

| File | Purpose |
|---|---|
| `ClaudouApp.swift` | `MenuBarExtra` + editor and settings windows |
| `Launcher.swift` | Claude.app path, command building/running, process discovery, focus/quit |
| `ProfileStore.swift` | Profile model, persistence, running state |
| `MenuView.swift` | Menu-style popover |
| `SettingsView.swift`, `EditorView.swift` | Settings (path, startup, profile CRUD) and the profile editor |
| `Theme.swift` | Brand colors, `Card`, window vibrancy background, avatar |
| `scripts/make_icon.swift`, `scripts/make_menubar.swift` | Generate the app icon and the template menu bar glyph from `assets/` |

## Notes

- Instances share the Dock icon, so use the popover list to pick the right one.
- `claude://` links open in an arbitrary instance.
- The macOS Keychain entry "Claude Safe Storage" is shared by all profiles; this is expected.
