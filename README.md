<p align="center"><img src="assets/logo.png" width="120" alt="Claudou"></p>

# Claudou

Run several Claude Desktop accounts on one computer. Each account gets its own profile with its own login session, chat history and MCP configuration.

Each platform has its own native implementation; no code is shared between them, but behavior is. The shared specification is [docs/SPEC.md](docs/SPEC.md), and [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) explains how features are rolled out to every OS.

## Download

Get the latest build from **[GitHub Releases](https://github.com/hoangdvhp99/claudou/releases/latest)**. Claude Desktop must already be installed.

| OS | File | Requirements |
|---|---|---|
| Windows | `Claudou.exe` | Windows 10/11 |
| macOS | `Claudou-macOS.zip` (universal: Apple silicon + Intel) | macOS 13 or later |

### Windows

1. Download `Claudou.exe` and put it anywhere (for example `C:\Tools\Claudou`). It is a single portable file: no installer, no administrator rights.
2. Double-click it. Windows SmartScreen may say *"Windows protected your PC"* because the app is not code-signed yet: click **More info → Run anyway**.
3. Open **Settings** from the tray window and check that the status says **Claude found** (it auto-detects the Microsoft Store, per-user and Program Files installs; use **Browse…** otherwise).
4. Optional: turn on **Launch at startup** (works from the `.exe`).

### macOS

1. Download `Claudou-macOS.zip`, unzip it and drag **Claudou.app** to **Applications**.
2. The app is not notarized. On first launch **right-click → Open → Open** (or *System Settings → Privacy & Security → Open Anyway*). If macOS says the app is damaged, run `xattr -cr /Applications/Claudou.app` once.
3. Claudou lives in the menu bar. Open **Settings…** to check the path to `Claude.app` and manage profiles.

### Using it

- **New profile** in Settings → give it a name and a color → **Open** it from the launcher → sign in to that account once. Every profile keeps its own login, chat history and MCP configuration.
- **Open** starts a profile, **Show** brings a running one to the front, **✕** quits only that Claude. Profiles run in parallel.
- The **Default** profile is your normal Claude (nothing is moved or copied), and you can reorder profiles in Settings (Windows).
- Deleting a profile that Claudou created erases its folder after confirmation; profiles that use a folder you chose are only removed from the list.

## Platforms

| Platform | Status | Stack | How it switches accounts |
|---|---|---|---|
| [macOS](macOS/) | Available | Swift / SwiftUI menu bar app (macOS 26 look) | Parallel instances via `--user-data-dir` |
| [Windows](window/) | Available (tested on Windows 11) | Python / customtkinter + tray, light/dark | Parallel instances via `--user-data-dir` |
| [Linux](docs/linux-tech-stack.md) | Planned (stack proposed) | Python / GTK4 + libadwaita | Parallel instances via `--user-data-dir` |

Each platform has its own native implementation; no code is shared between them, but behavior is. The shared specification is [docs/SPEC.md](docs/SPEC.md), and [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) explains how features are rolled out to every OS.

## Build from source

```bash
# macOS
cd macOS/Claudou && ./build_app.sh && open build/Claudou.app
```

```powershell
# Windows
cd window; .\build_exe.ps1 -Install      # -> window\dist\Claudou.exe
```

Details: [macOS/README.md](macOS/README.md) · [window/README.md](window/README.md).

## Publishing a release (maintainers)

1. Bump `VERSION` and merge to `main`.
2. Tag and push: `git tag v1.0.1 && git push origin v1.0.1`.
3. The [Release workflow](.github/workflows/release.yml) builds both apps and attaches `Claudou.exe` and `Claudou-macOS.zip` to a GitHub Release.

## Repository layout

```
assets/    logo and menu bar glyph
macOS/     Swift package + build script
window/    Python app + tests + PyInstaller build script
linux/     placeholder (see docs/linux-tech-stack.md)
docs/      SPEC.md (source of truth), CONTRIBUTING.md, linux-tech-stack.md
VERSION    single version number read by every build
```

## License

MIT
