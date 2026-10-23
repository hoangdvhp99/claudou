<p align="center"><img src="assets/logo.png" width="120" alt="Claudou"></p>

# Claudou

Run several Claude Desktop accounts on one computer. Each account gets its own profile with its own login session, chat history and MCP configuration.

Each platform has its own native implementation; no code is shared between them, but behavior is. The shared specification is [docs/SPEC.md](docs/SPEC.md), and [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) explains how features are rolled out to every OS.

| Platform | Status | Stack | How it switches accounts |
|---|---|---|---|
| [macOS](macOS/) | Available | Swift / SwiftUI menu bar app | Parallel instances via `--user-data-dir` |
| [Windows](window/) | Available (UI untested on real Windows yet) | Python / customtkinter + tray | Parallel instances via `--user-data-dir` |
| [Linux](docs/linux-tech-stack.md) | Planned (stack proposed) | Python / GTK4 + libadwaita | Parallel instances via `--user-data-dir` |

## Quick start (macOS)

```bash
cd macOS/Claudou
./build_app.sh
open build/Claudou.app
```

See [macOS/README.md](macOS/README.md) for details. Windows instructions are in [window/README.md](window/README.md).

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
