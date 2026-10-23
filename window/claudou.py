"""
Claudou - Claude Desktop Multi-Account Manager for Windows
Hỗ trợ mở nhiều tài khoản Claude Desktop trên một máy Windows.

Cơ chế:
  - Claude Desktop (MSIX) lưu data tại: %LOCALAPPDATA%/Claude-Data/claude_pzs8sxrjxfjjc/
  - Claudou tạo nhiều folder profile riêng tại: %LOCALAPPDATA%/Claudou/profiles/<tên>/
  - Khi launch một profile: tạo Directory Junction từ claude_pzs8sxrjxfjjc -> profile_dir
  - Mỗi profile có session, login, config riêng biệt hoàn toàn
"""

import sys
import os
import json
import re
import shutil
import subprocess
import ctypes
from ctypes import wintypes
import threading
from pathlib import Path
from datetime import datetime

import customtkinter as ctk
from tkinter import messagebox, simpledialog
import tkinter as tk
from tkinter import font as tkfont


# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────
APP_NAME = "Claudou"
APP_VERSION = "1.0.0"

# Claude paths (MSIX install)
CLAUDE_DATA_ROOT = Path(os.environ["LOCALAPPDATA"]) / "Claude-Data"
CLAUDE_DATA_FOLDER_NAME = "claude_pzs8sxrjxfjjc"
CLAUDE_DATA_LINK = CLAUDE_DATA_ROOT / CLAUDE_DATA_FOLDER_NAME  # junction target

# Claudou storage
CLAUDOU_ROOT = Path(os.environ["LOCALAPPDATA"]) / "Claudou"
PROFILES_DIR = CLAUDOU_ROOT / "profiles"
CONFIG_FILE = CLAUDOU_ROOT / "config.json"

# Claude exe (dynamic discovery)
_CLAUDE_EXE_CACHE: Path | None = None

# Colors
C_BG = "#1a1a2e"
C_CARD = "#16213e"
C_ACCENT = "#e8602c"
C_ACCENT_HOVER = "#c94e22"
C_TEXT = "#e8e8e8"
C_DIM = "#8a8a9a"
C_SUCCESS = "#4caf50"
C_WARNING = "#ff9800"
C_DANGER = "#f44336"
C_BORDER = "#0f3460"
C_HOVER = "#1e2d5e"
C_INPUT = "#0d1a36"

PROFILE_COLORS = ["#e8602c", "#4caf50", "#2196f3", "#9c27b0",
                  "#ff9800", "#00bcd4", "#f44336", "#607d8b"]
PROFILE_EMOJIS = ["👤", "🎯", "💼", "🚀", "⚡", "🌙", "🔥", "🎨", "🎮", "📚"]


# ─────────────────────────────────────────────
# Profile Manager
# ─────────────────────────────────────────────
class ProfileManager:
    def __init__(self):
        CLAUDOU_ROOT.mkdir(parents=True, exist_ok=True)
        PROFILES_DIR.mkdir(parents=True, exist_ok=True)
        self._config = self._load_config()

    def _load_config(self) -> dict:
        if CONFIG_FILE.exists():
            try:
                return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"profiles": {}}

    def _save_config(self):
        CONFIG_FILE.write_text(
            json.dumps(self._config, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def get_profiles(self) -> list[dict]:
        profiles = []
        for name, meta in self._config.get("profiles", {}).items():
            profiles.append({
                "name": name,
                "display_name": meta.get("display_name", name),
                "color": meta.get("color", C_ACCENT),
                "emoji": meta.get("emoji", "👤"),
                "created_at": meta.get("created_at", ""),
                "last_used": meta.get("last_used", ""),
                "path": str(PROFILES_DIR / name),
            })
        return profiles

    def create_profile(self, name: str, display_name: str = "",
                       color: str = C_ACCENT, emoji: str = "👤") -> dict:
        safe = re.sub(r"[^\w\-]", "_", name).strip("_") or "profile"
        orig, i = safe, 2
        while safe in self._config.get("profiles", {}):
            safe = f"{orig}_{i}"; i += 1
        (PROFILES_DIR / safe).mkdir(parents=True, exist_ok=True)
        self._config.setdefault("profiles", {})[safe] = {
            "display_name": display_name or name,
            "color": color, "emoji": emoji,
            "created_at": datetime.now().isoformat(), "last_used": "",
        }
        self._save_config()
        return self.get_profile(safe)

    def get_profile(self, name: str) -> dict | None:
        return next((p for p in self.get_profiles() if p["name"] == name), None)

    def delete_profile(self, name: str, delete_data: bool = True):
        d = PROFILES_DIR / name
        if delete_data and d.exists():
            shutil.rmtree(d, ignore_errors=True)
        self._config.get("profiles", {}).pop(name, None)
        self._save_config()

    def update_meta(self, name: str, **kw):
        if name in self._config.get("profiles", {}):
            self._config["profiles"][name].update(kw)
            self._save_config()

    def mark_used(self, name: str):
        self.update_meta(name, last_used=datetime.now().isoformat())


# ─────────────────────────────────────────────
# Claude Launcher
# ─────────────────────────────────────────────
class ClaudeLauncher:
    @staticmethod
    def _get_process_list():
        kernel32 = ctypes.windll.kernel32
        TH32CS_SNAPPROCESS = 0x00000002

        class PROCESSENTRY32W(ctypes.Structure):
            _fields_ = [
                ('dwSize', wintypes.DWORD),
                ('cntUsage', wintypes.DWORD),
                ('th32ProcessID', wintypes.DWORD),
                ('th32DefaultHeapID', ctypes.c_size_t),
                ('th32ModuleID', wintypes.DWORD),
                ('cntThreads', wintypes.DWORD),
                ('th32ParentProcessID', wintypes.DWORD),
                ('pcPriClassBase', wintypes.LONG),
                ('dwFlags', wintypes.DWORD),
                ('szExeFile', wintypes.WCHAR * 260)
            ]

        hSnapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if hSnapshot == -1:
            return []
        pe = PROCESSENTRY32W()
        pe.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        procs = []
        if kernel32.Process32FirstW(hSnapshot, ctypes.byref(pe)):
            while True:
                procs.append((pe.th32ProcessID, pe.szExeFile))
                if not kernel32.Process32NextW(hSnapshot, ctypes.byref(pe)):
                    break
        kernel32.CloseHandle(hSnapshot)
        return procs

    @classmethod
    def is_running(cls) -> bool:
        """Check if Claude is running silently using Win32 API (no cmd flash)."""
        procs = cls._get_process_list()
        return any(name.lower() == "claude.exe" for _, name in procs)

    @classmethod
    def kill_claude(cls) -> int:
        """Terminate all claude.exe processes cleanly."""
        kernel32 = ctypes.windll.kernel32
        procs = cls._get_process_list()
        killed = 0
        for pid, name in procs:
            if name.lower() == "claude.exe":
                hProc = kernel32.OpenProcess(0x0001, False, pid)  # PROCESS_TERMINATE
                if hProc:
                    kernel32.TerminateProcess(hProc, 0)
                    kernel32.CloseHandle(hProc)
                    killed += 1
        return killed

    @staticmethod
    def find_exe() -> Path | None:
        global _CLAUDE_EXE_CACHE
        if _CLAUDE_EXE_CACHE and _CLAUDE_EXE_CACHE.exists():
            return _CLAUDE_EXE_CACHE
        # Scan WindowsApps
        win_apps = Path(r"C:\Program Files\WindowsApps")
        if win_apps.exists():
            try:
                for d in win_apps.glob("Claude_*_x64__*"):
                    exe = d / "app" / "claude.exe"
                    if exe.exists():
                        _CLAUDE_EXE_CACHE = exe
                        return exe
            except PermissionError:
                pass
        # Fallback from registry
        try:
            result = subprocess.run(
                ["reg", "query",
                 r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\claude.exe",
                 "/ve"],
                capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            for line in result.stdout.splitlines():
                if "REG_SZ" in line:
                    path = Path(line.split("REG_SZ")[-1].strip())
                    if path.exists():
                        _CLAUDE_EXE_CACHE = path
                        return path
        except Exception:
            pass
        return None

    @staticmethod
    def is_junction(path: Path) -> bool:
        try:
            s = os.lstat(str(path))
            return bool(s.st_file_attributes & 0x400)
        except Exception:
            return False

    @staticmethod
    def _remove_junction(path: Path):
        """Remove a junction without deleting its contents."""
        try:
            subprocess.run(
                ["cmd", "/c", "rmdir", str(path)],
                capture_output=True, check=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except Exception:
            pass

    @classmethod
    def set_active_profile(cls, profile_dir: Path) -> tuple[bool, str]:
        """Point the Claude data junction to profile_dir."""
        profile_dir.mkdir(parents=True, exist_ok=True)

        # 1. Đảm bảo Claude đã tắt hẳn trước khi đụng vào folder
        if cls.is_running():
            cls.kill_claude()
            import time
            time.sleep(1)

        # 2. Xử lý folder data
        if CLAUDE_DATA_LINK.exists() or cls.is_junction(CLAUDE_DATA_LINK):
            if cls.is_junction(CLAUDE_DATA_LINK):
                cls._remove_junction(CLAUDE_DATA_LINK)
            else:
                # Nếu là thư mục thật (dữ liệu ban đầu của máy)
                backup = CLAUDE_DATA_ROOT / f"{CLAUDE_DATA_FOLDER_NAME}_original_backup"
                if not backup.exists():
                    try:
                        # Copy nội dung sang profile "default" nếu profile default đang rỗng
                        default_profile_dir = PROFILES_DIR / "default"
                        if default_profile_dir.exists() and not any(default_profile_dir.iterdir()):
                            try:
                                shutil.copytree(str(CLAUDE_DATA_LINK), str(default_profile_dir), dirs_exist_ok=True)
                            except Exception:
                                pass
                        CLAUDE_DATA_LINK.rename(backup)
                    except PermissionError:
                        return False, (
                            "Không thể di chuyển thư mục dữ liệu gốc (Access is denied).\n\n"
                            "Nguyên nhân: Claude Desktop hoặc một tiến trình liên quan vẫn đang khóa thư mục.\n"
                            "Hãy thử tắt Claude Desktop trong Task Manager và nhấn Mở lại."
                        )
                    except Exception as e:
                        return False, (
                            f"Không thể backup thư mục gốc: {e}\n"
                            f"Đường dẫn: {CLAUDE_DATA_LINK}"
                        )
                else:
                    # Đã có backup rồi, thư mục thật này có thể xóa
                    try:
                        shutil.rmtree(str(CLAUDE_DATA_LINK))
                    except Exception:
                        cls._remove_junction(CLAUDE_DATA_LINK)

        # 3. Tạo junction trỏ sang profile được chọn
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J",
             str(CLAUDE_DATA_LINK), str(profile_dir)],
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if result.returncode != 0:
            return False, (
                f"Không thể tạo junction:\n{result.stderr or result.stdout}\n\n"
                "Vui lòng chạy Claudou với quyền Administrator."
            )
        return True, ""

    @classmethod
    def launch(cls, profile_dir: Path) -> tuple[bool, str]:
        ok, err = cls.set_active_profile(profile_dir)
        if not ok:
            return False, err
        try:
            # 1. Thử mở bằng Windows App Protocol / Explorer (chuẩn cho WindowsApps MSIX)
            # Claude_pzs8sxrjxfjjc!Claude
            os.system('start shell:AppsFolder\\Claude_pzs8sxrjxfjjc!Claude')
            return True, ""
        except Exception as e:
            # 2. Dự phòng bằng đường dẫn exe trực tiếp
            exe = cls.find_exe()
            if exe and exe.exists():
                try:
                    subprocess.Popen(
                        [str(exe)],
                        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                        close_fds=True
                    )
                    return True, ""
                except Exception as ex:
                    return False, f"Lỗi khởi động Claude: {ex}"
            return False, f"Lỗi khởi động Claude: {e}"


# ─────────────────────────────────────────────
# UI: Create/Edit Profile Dialog
# ─────────────────────────────────────────────
class ProfileDialog(ctk.CTkToplevel):
    def __init__(self, parent, existing: dict = None):
        super().__init__(parent)
        self.result: dict | None = None
        self.existing = existing
        self._sel_color = existing["color"] if existing else PROFILE_COLORS[0]
        self._sel_emoji = existing["emoji"] if existing else PROFILE_EMOJIS[0]
        self._emoji_btns: list[ctk.CTkButton] = []
        self._color_btns: list[ctk.CTkButton] = []

        self.title("Tạo Profile" if not existing else "Sửa Profile")
        self.geometry("460x520")
        self.resizable(False, False)
        self.configure(fg_color=C_BG)
        self.grab_set()  # modal
        self._build()

    def _build(self):
        pad = {"padx": 24, "pady": (12, 4)}

        # Title
        ctk.CTkLabel(
            self, text="Tạo Profile Mới" if not self.existing else "Chỉnh sửa Profile",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=C_TEXT
        ).pack(fill="x", padx=24, pady=(24, 4))

        ctk.CTkLabel(self, text="Chọn biểu tượng:", text_color=C_DIM,
                     font=ctk.CTkFont(size=12)).pack(anchor="w", **pad)

        # Emoji grid
        emoji_frame = ctk.CTkFrame(self, fg_color="transparent")
        emoji_frame.pack(fill="x", padx=24, pady=(0, 12))
        for i, em in enumerate(PROFILE_EMOJIS):
            selected = em == self._sel_emoji
            btn = ctk.CTkButton(
                emoji_frame, text=em, width=40, height=40,
                font=ctk.CTkFont(size=20),
                fg_color=C_HOVER if selected else C_CARD,
                border_color=C_ACCENT if selected else C_BORDER,
                border_width=2,
                hover_color=C_HOVER,
                corner_radius=8,
                command=lambda e=em: self._pick_emoji(e)
            )
            btn.grid(row=0, column=i, padx=3)
            self._emoji_btns.append(btn)

        ctk.CTkLabel(self, text="Màu sắc:", text_color=C_DIM,
                     font=ctk.CTkFont(size=12)).pack(anchor="w", **pad)

        # Color dots
        color_frame = ctk.CTkFrame(self, fg_color="transparent")
        color_frame.pack(fill="x", padx=24, pady=(0, 16))
        for i, col in enumerate(PROFILE_COLORS):
            selected = col == self._sel_color
            btn = ctk.CTkButton(
                color_frame, text="✓" if selected else "",
                width=36, height=36, corner_radius=18,
                fg_color=col, hover_color=col,
                text_color="white",
                font=ctk.CTkFont(size=14, weight="bold"),
                border_width=3 if selected else 0,
                border_color="white",
                command=lambda c=col: self._pick_color(c)
            )
            btn.grid(row=0, column=i, padx=4)
            self._color_btns.append(btn)

        ctk.CTkLabel(self, text="Tên profile:", text_color=C_DIM,
                     font=ctk.CTkFont(size=12)).pack(anchor="w", **pad)

        self._name_var = ctk.StringVar(
            value=self.existing["display_name"] if self.existing else ""
        )
        self._name_entry = ctk.CTkEntry(
            self, textvariable=self._name_var,
            placeholder_text="Ví dụ: Cá nhân, Công ty A, Dự án X...",
            height=42, font=ctk.CTkFont(size=14),
            fg_color=C_INPUT, border_color=C_BORDER,
            text_color=C_TEXT, placeholder_text_color=C_DIM,
            corner_radius=8
        )
        self._name_entry.pack(fill="x", padx=24, pady=(0, 20))
        self._name_entry.focus()

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=24, pady=(0, 24))
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=0)

        ctk.CTkButton(
            btn_frame, text="Hủy", width=100, height=40,
            fg_color=C_CARD, hover_color=C_HOVER,
            text_color=C_DIM, border_color=C_BORDER, border_width=1,
            corner_radius=8, command=self.destroy
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            btn_frame, text="✓  Lưu", width=120, height=40,
            fg_color=C_ACCENT, hover_color=C_ACCENT_HOVER,
            text_color="white", corner_radius=8,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._on_ok
        ).grid(row=0, column=1, sticky="e")

    def _pick_emoji(self, em: str):
        self._sel_emoji = em
        for btn in self._emoji_btns:
            is_sel = btn.cget("text") == em
            btn.configure(
                fg_color=C_HOVER if is_sel else C_CARD,
                border_color=C_ACCENT if is_sel else C_BORDER
            )

    def _pick_color(self, col: str):
        self._sel_color = col
        for i, btn in enumerate(self._color_btns):
            is_sel = PROFILE_COLORS[i] == col
            btn.configure(
                text="✓" if is_sel else "",
                border_width=3 if is_sel else 0
            )

    def _on_ok(self):
        name = self._name_var.get().strip()
        if not name:
            messagebox.showwarning("Thiếu tên", "Vui lòng nhập tên profile.", parent=self)
            return
        self.result = {
            "display_name": name,
            "color": self._sel_color,
            "emoji": self._sel_emoji,
        }
        self.destroy()


# ─────────────────────────────────────────────
# UI: Profile Card
# ─────────────────────────────────────────────
class ProfileCard(ctk.CTkFrame):
    def __init__(self, parent, profile: dict,
                 on_launch, on_edit, on_delete, **kw):
        super().__init__(parent, fg_color=C_CARD, corner_radius=12,
                         border_color=C_BORDER, border_width=1, **kw)
        self._profile = profile
        self._on_launch = on_launch
        self._on_edit = on_edit
        self._on_delete = on_delete
        self._build()
        self.bind("<Double-Button-1>", lambda _: on_launch(profile["name"]))

    def _build(self):
        p = self._profile

        # Left: avatar (blend color with dark bg for a muted bg effect)
        def _muted(hex_color: str) -> str:
            """Blend hex color with dark background ~20% opacity."""
            h = hex_color.lstrip("#")
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            br, bg_, bb = 0x1a, 0x1a, 0x2e  # C_BG
            mr = int(r * 0.25 + br * 0.75)
            mg = int(g * 0.25 + bg_ * 0.75)
            mb = int(b * 0.25 + bb * 0.75)
            return f"#{mr:02x}{mg:02x}{mb:02x}"

        avatar = ctk.CTkLabel(
            self, text=p["emoji"], width=52, height=52,
            font=ctk.CTkFont(size=26),
            fg_color=_muted(p["color"]),
            corner_radius=26, text_color=C_TEXT
        )
        avatar.pack(side="left", padx=(14, 10), pady=12)
        avatar.bind("<Double-Button-1>", lambda _: self._on_launch(p["name"]))

        # Middle: info
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, pady=10)

        ctk.CTkLabel(
            info_frame, text=p["display_name"],
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=C_TEXT, anchor="w"
        ).pack(anchor="w")

        last_used = p.get("last_used", "")
        if last_used:
            try:
                dt = datetime.fromisoformat(last_used)
                sub = f"Lần cuối: {dt.strftime('%d/%m/%Y %H:%M')}"
            except Exception:
                sub = f"Lần cuối: {last_used}"
        else:
            sub = "Chưa sử dụng"
        ctk.CTkLabel(
            info_frame, text=sub,
            font=ctk.CTkFont(size=11), text_color=C_DIM, anchor="w"
        ).pack(anchor="w")

        # Right: buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(side="right", padx=(0, 12), pady=12)

        ctk.CTkButton(
            btn_frame, text="▶  Mở", width=80, height=34,
            fg_color=p["color"], hover_color=p["color"] + "cc",
            text_color="white", corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: self._on_launch(p["name"])
        ).pack(side="left", padx=(0, 6))

        # Menu button (using OptionMenu workaround)
        menu_btn = ctk.CTkButton(
            btn_frame, text="⋮", width=30, height=34,
            fg_color="transparent", hover_color=C_HOVER,
            text_color=C_DIM, corner_radius=6,
            font=ctk.CTkFont(size=18),
            command=self._show_menu
        )
        menu_btn.pack(side="left")
        self._menu_btn_ref = menu_btn

    def _show_menu(self):
        p = self._profile
        menu = tk.Menu(self, tearoff=False,
                       bg=C_CARD, fg=C_TEXT,
                       activebackground=C_HOVER, activeforeground=C_TEXT,
                       borderwidth=1, relief="flat")
        menu.add_command(label="✏️  Đổi tên / Sửa",
                         command=lambda: self._on_edit(p["name"]))
        menu.add_separator()
        menu.add_command(label="🗑️  Xóa profile",
                         command=lambda: self._on_delete(p["name"]))
        # Show at menu button position
        x = self._menu_btn_ref.winfo_rootx()
        y = self._menu_btn_ref.winfo_rooty() + self._menu_btn_ref.winfo_height()
        menu.tk_popup(x, y)


# ─────────────────────────────────────────────
# Main Window
# ─────────────────────────────────────────────
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.pm = ProfileManager()
        self._cards: list[ProfileCard] = []

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title(f"{APP_NAME} — Claude Desktop Multi-Account")
        self.geometry("640x620")
        self.minsize(560, 480)
        self.configure(fg_color=C_BG)

        self._build_ui()
        self._refresh()
        self._ensure_default_profile()

        # Status polling
        self._poll_status()

    # ── UI Construction ──

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=0, height=72)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        h_inner = ctk.CTkFrame(header, fg_color="transparent")
        h_inner.pack(fill="both", expand=True, padx=24)

        ctk.CTkLabel(h_inner, text="⚡", font=ctk.CTkFont(size=28),
                     text_color=C_ACCENT).pack(side="left", pady=16, padx=(0, 8))

        title_frame = ctk.CTkFrame(h_inner, fg_color="transparent")
        title_frame.pack(side="left", fill="y")
        ctk.CTkLabel(title_frame, text=APP_NAME,
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=C_TEXT).pack(anchor="sw", pady=(14, 0))
        ctk.CTkLabel(title_frame, text="Claude Desktop Multi-Account",
                     font=ctk.CTkFont(size=11), text_color=C_DIM).pack(anchor="nw")

        # Status
        self._status_lbl = ctk.CTkLabel(
            h_inner, text="● Đang kiểm tra...",
            font=ctk.CTkFont(size=11), text_color=C_DIM
        )
        self._status_lbl.pack(side="right", pady=20)

        # Separator line
        sep = ctk.CTkFrame(self, fg_color=C_BORDER, height=1, corner_radius=0)
        sep.pack(fill="x")

        # Body
        body = ctk.CTkFrame(self, fg_color=C_BG, corner_radius=0)
        body.pack(fill="both", expand=True, padx=24, pady=20)

        # Top row
        top = ctk.CTkFrame(body, fg_color="transparent")
        top.pack(fill="x", pady=(0, 14))

        ctk.CTkLabel(top, text="Profiles của bạn",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=C_TEXT).pack(side="left")

        ctk.CTkButton(
            top, text="＋  Tạo Profile Mới", height=38,
            fg_color=C_ACCENT, hover_color=C_ACCENT_HOVER,
            text_color="white", corner_radius=8,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_add
        ).pack(side="right")

        # Scrollable profile list
        self._scroll = ctk.CTkScrollableFrame(
            body, fg_color="transparent", corner_radius=0
        )
        self._scroll.pack(fill="both", expand=True)

        # Empty state label
        self._empty_lbl = ctk.CTkLabel(
            body,
            text="Chưa có profile nào.\nNhấn '＋ Tạo Profile Mới' để bắt đầu!",
            font=ctk.CTkFont(size=14), text_color=C_DIM
        )

        # Footer
        footer_sep = ctk.CTkFrame(self, fg_color=C_BORDER, height=1, corner_radius=0)
        footer_sep.pack(fill="x", side="bottom")

        footer = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=0, height=38)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        ctk.CTkLabel(footer, text=f"Claudou v{APP_VERSION}",
                     font=ctk.CTkFont(size=11), text_color=C_DIM
                     ).pack(side="left", padx=24)
        ctk.CTkLabel(footer, text="Double-click hoặc nhấn ▶ Mở để khởi động Claude",
                     font=ctk.CTkFont(size=11), text_color=C_DIM
                     ).pack(side="right", padx=24)

    # ── Profile Management ──

    def _ensure_default_profile(self):
        if not self.pm.get_profiles():
            self.pm.create_profile("default", "Default", C_ACCENT, "👤")
            self._refresh()

    def _refresh(self):
        # Clear old cards
        for card in self._cards:
            card.destroy()
        self._cards.clear()
        self._empty_lbl.pack_forget()
        self._scroll.pack_forget()

        profiles = self.pm.get_profiles()
        if not profiles:
            self._empty_lbl.pack(expand=True)
            return

        self._scroll.pack(fill="both", expand=True)
        for p in profiles:
            card = ProfileCard(
                self._scroll, p,
                on_launch=self._on_launch,
                on_edit=self._on_edit,
                on_delete=self._on_delete,
            )
            card.pack(fill="x", pady=(0, 10))
            self._cards.append(card)

    def _on_add(self):
        dlg = ProfileDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            r = dlg.result
            self.pm.create_profile(r["display_name"], r["display_name"],
                                   r["color"], r["emoji"])
            self._refresh()

    def _on_edit(self, name: str):
        p = self.pm.get_profile(name)
        if not p:
            return
        dlg = ProfileDialog(self, existing=p)
        self.wait_window(dlg)
        if dlg.result:
            r = dlg.result
            self.pm.update_meta(name, display_name=r["display_name"],
                                color=r["color"], emoji=r["emoji"])
            self._refresh()

    def _on_delete(self, name: str):
        p = self.pm.get_profile(name)
        if not p:
            return
        if messagebox.askyesno(
            "Xóa Profile",
            f"Bạn có chắc muốn xóa profile '{p['display_name']}'?\n\n"
            "Dữ liệu (session, lịch sử chat) sẽ bị xóa vĩnh viễn.",
            parent=self
        ):
            self.pm.delete_profile(name, delete_data=True)
            self._refresh()

    def _on_launch(self, name: str):
        p = self.pm.get_profile(name)
        if not p:
            return

        if ClaudeLauncher.is_running():
            ans = messagebox.askyesno(
                "Claude đang chạy",
                f"Claude Desktop đang mở trên máy.\n\n"
                f"Để mở profile '{p['display_name']}', Claudou cần đóng Claude đang chạy.\n\n"
                "Bạn có muốn Claudou tự động tắt Claude và tiếp tục mở không?",
                parent=self
            )
            if not ans:
                return
            # Auto kill claude processes cleanly
            ClaudeLauncher.kill_claude()
            import time
            time.sleep(1)

        def _do_launch():
            ok, err = ClaudeLauncher.launch(Path(p["path"]))
            if ok:
                self.pm.mark_used(name)
                self.after(0, self._refresh)
            else:
                self.after(0, lambda: messagebox.showerror(
                    "Lỗi khởi động",
                    f"Không thể mở Claude với profile '{p['display_name']}':\n\n{err}",
                    parent=self
                ))

        threading.Thread(target=_do_launch, daemon=True).start()

    # ── Status Polling ──

    def _poll_status(self):
        running = ClaudeLauncher.is_running()
        if running:
            self._status_lbl.configure(text="● Claude: Đang chạy",
                                       text_color=C_SUCCESS)
        else:
            self._status_lbl.configure(text="● Claude: Không chạy",
                                       text_color=C_DIM)
        self.after(3000, self._poll_status)


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────
def request_admin_if_needed():
    """Re-launch with admin rights if not already elevated (needed for mklink /J)."""
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        is_admin = False

    if not is_admin:
        # Re-launch as admin
        try:
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas",
                sys.executable,
                " ".join(f'"{a}"' for a in sys.argv),
                None, 1
            )
            if ret > 32:
                return False  # Successfully launched as admin, exit current process
        except Exception:
            pass
        # Admin elevation failed or user denied — show warning and continue
        messagebox.showwarning(
            "Cần quyền Administrator",
            "Claudou cần quyền Administrator để tạo directory junction.\n\n"
            "Một số tính năng có thể không hoạt động.\n"
            "Vui lòng chạy lại bằng cách click chuột phải → 'Run as administrator'."
        )
    return True  # Already admin or user accepted risk


def main():
    continue_run = request_admin_if_needed()
    if not continue_run:
        sys.exit(0)

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
