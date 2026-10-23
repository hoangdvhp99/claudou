# Claudou 🚀

> Multi-account manager for Claude Desktop on Windows (macOS & Linux coming soon).

Claudou allows you to manage and switch between multiple Claude Desktop accounts seamlessly on a single computer without losing your sessions or settings.

---

## 💻 Platforms

- **[Windows](window/)**: Available now (Supports standard installer and Microsoft Store MSIX edition).
- **macOS**: Planned.
- **Linux**: Planned.

---

## 🛠️ Windows Features

- **Profile Isolation**: Each profile retains its own login session, chat history, and MCP configurations independently using Windows directory junctions.
- **Auto-detection**: Automatically finds Claude Desktop installations (MSIX Store package / native executable).
- **Process Management**: Safely and automatically terminates running instances when switching profiles to prevent lock conflicts.
- **Customization**: Assign distinct display names, emojis, and color markers to each account.
- **No Console Flashing**: Integrates natively with Windows Win32 APIs for background status polling.

---

## 🚀 Quick Start (Windows)

See the **[Windows README](window/README.md)** for detailed setup instructions and build steps.

### Run from Source:
```powershell
cd window
pip install -r requirements.txt
python claudou.py
```

### Build Single Executable (.exe):
```powershell
cd window
.\build_exe.ps1 -Install
```

---

## 📄 License

MIT License.
