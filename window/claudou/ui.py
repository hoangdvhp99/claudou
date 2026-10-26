"""Claudou UI (customtkinter): menu-style launcher, Settings (profile CRUD) and profile editor.

Mirrors the macOS app (menu bar popover + Settings); see docs/SPEC.md §5.
"""
from __future__ import annotations

import ctypes
import os
import queue
import subprocess
import tempfile
import threading
import tkinter as tk
from ctypes import wintypes
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFilter

from . import APP_NAME, APP_VERSION, launcher, startup
from . import theme as T
from .store import Profile, ProfileStore, profiles_dir, slug

try:
    import pystray
except Exception:  # tray is optional
    pystray = None

FONT = "Segoe UI"
RADIUS_CARD = 14
RADIUS_CONTROL = 8


def font(size: int, bold: bool = False) -> ctk.CTkFont:
    return ctk.CTkFont(family=FONT, size=size, weight="bold" if bold else "normal")


def button(parent, text, command, primary=False, width=0, height=32, **kw):
    """Rounded button: accent-filled when primary, neutral otherwise."""
    fg, hover, txt = (T.ACCENT, T.ACCENT_HOVER, "white") if primary else (T.BUTTON, T.BUTTON_HOVER, T.TEXT)
    return ctk.CTkButton(parent, text=text, command=command, width=width, height=height,
                         corner_radius=RADIUS_CONTROL, fg_color=fg, hover_color=hover, text_color=txt,
                         font=font(12, primary), **kw)


def pill(parent, text, command, color=T.ACCENT, hover=T.ACCENT_HOVER, width=52):
    """Small filled pill (Open / Show)."""
    return ctk.CTkButton(parent, text=text, command=command, width=width, height=24, corner_radius=12,
                         fg_color=color, hover_color=hover, text_color="white", font=font(12, True))


def entry(parent, var, placeholder="", mono=False, **kw):
    e = ctk.CTkEntry(parent, textvariable=var, height=32,
                     corner_radius=RADIUS_CONTROL, fg_color=T.INPUT, border_color=T.BORDER, border_width=1,
                     text_color=T.TEXT, font=ctk.CTkFont(family="Consolas" if mono else FONT, size=12), **kw)
    if placeholder:
        # CTkEntry never shows its own placeholder when a textvariable is bound, so overlay a label.
        hint = ctk.CTkLabel(e, text=placeholder, text_color=T.DIM, fg_color=T.INPUT, height=18,
                            font=ctk.CTkFont(family="Consolas" if mono else FONT, size=12), anchor="w")
        hint.bind("<Button-1>", lambda _: e.focus_set())

        def sync(*_):
            if var.get():
                hint.place_forget()
            else:
                hint.place(x=10, rely=0.5, anchor="w")
        var.trace_add("write", sync)
        sync()
    return e


def label(parent, text, size=12, color=T.TEXT, bold=False, **kw):
    return ctk.CTkLabel(parent, text=text, text_color=color, font=font(size, bold), **kw)


def card(parent, **kw):
    return ctk.CTkFrame(parent, fg_color=T.CARD, corner_radius=RADIUS_CARD, **kw)


def divider(parent):
    return ctk.CTkFrame(parent, fg_color=T.BORDER, height=1, corner_radius=0)


def avatar(parent, p: Profile, size: int):
    return label(parent, p.initial, int(size * 0.42), "white", True, width=size, height=size,
                 fg_color=p.color_hex, corner_radius=10 if size >= 40 else RADIUS_CONTROL)


def icon_frame(size: int) -> Image.Image:
    """Logo as a rounded-square icon on a transparent background (like the macOS app icon).

    Up to 48 px the full logo turns to mush, so small sizes use a tighter crop (hair, headband, eyes) that
    keeps the big shapes, box-resampled and sharpened so the pixel-art edges stay crisp."""
    src = Image.open(T.asset(T.LOGO)).convert("RGBA")
    if size <= 48:
        img = src.crop((130, 70, 1130, 1070)).resize((size, size), Image.BOX)
        img = img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=220, threshold=0))
    else:
        img = src.resize((size, size), Image.LANCZOS)
        if size <= 64:
            img = img.filter(ImageFilter.UnsharpMask(radius=0.8, percent=140, threshold=1))
    scale = 4
    mask = Image.new("L", (size * scale, size * scale), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size * scale - 1, size * scale - 1),
                                           radius=round(size * scale * 0.2), fill=255)
    img.putalpha(mask.resize((size, size), Image.LANCZOS))
    return img


def apply_icon(win) -> None:
    """customtkinter installs its blue default icon ~200 ms after a window opens; replace it with the logo."""
    def setup():
        try:
            if win.winfo_exists():
                win.iconbitmap(_icon_file())
        except Exception:
            pass
    win.after(300, setup)


def _icon_file() -> str:
    """Multi-size .ico built from hand-resampled frames (cached in the temp folder)."""
    ico = Path(tempfile.gettempdir()) / f"claudou_icon_{APP_VERSION}_l.ico"
    if not ico.exists():
        sizes = (256, 64, 48, 32, 24, 16)
        frames = [icon_frame(n) for n in sizes]
        frames[0].save(ico, format="ICO", sizes=[(n, n) for n in sizes], append_images=frames[1:])
    return str(ico)


def _logo(size: int, radius: int) -> ctk.CTkImage | None:
    """Logo with rounded corners (like the macOS app icon)."""
    try:
        img = Image.open(T.asset(T.LOGO)).convert("RGBA")
        scale = 4
        big = img.resize((size * scale, size * scale), Image.LANCZOS)
        mask = Image.new("L", big.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, *big.size), radius * scale, fill=255)
        big.putalpha(mask)
        return ctk.CTkImage(light_image=big, dark_image=big, size=(size, size))
    except Exception:
        return None


def _descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from _descendants(child)


def hover_highlight(row, color=T.CARD_HOVER):
    """Highlight `row` while the pointer is anywhere inside it, children included."""
    def inside() -> bool:
        x, y = row.winfo_pointerxy()
        return (row.winfo_rootx() <= x < row.winfo_rootx() + row.winfo_width()
                and row.winfo_rooty() <= y < row.winfo_rooty() + row.winfo_height())

    def on_enter(_):
        row.configure(fg_color=color)

    def on_leave(_):
        row.configure(fg_color=color if inside() else "transparent")

    for w in (row, *_descendants(row)):
        w.bind("<Enter>", on_enter, add="+")
        w.bind("<Leave>", on_leave, add="+")


# ───────────────────────── Profile editor ─────────────────────────

class EditorWindow(ctk.CTkToplevel):
    def __init__(self, app: "App", profile: Profile | None, on_saved):
        super().__init__(app.root)
        self.app, self.profile, self.on_saved = app, profile, on_saved
        self.title("Edit profile" if profile else "New profile")
        apply_icon(self)
        self.configure(fg_color=T.BG)
        self.resizable(False, False)

        self.name = ctk.StringVar(value=profile.name if profile else "")
        self.color = profile.color_hex if profile else T.PROFILE_COLORS[0]
        self.folder = ctk.StringVar(value=(profile.data_dir or "") if profile else "")
        self.command = ctk.StringVar()
        self.edited = profile.command_edited if profile else False
        self._syncing = False
        self._swatches: list[ctk.CTkButton] = []
        self._build()
        self.command.set(app.store.effective_command(profile) if profile else self._generated())
        self.name.trace_add("write", lambda *_: self._sync())
        self.folder.trace_add("write", lambda *_: self._sync())
        self.command.trace_add("write", lambda *_: self._on_command())
        self.after(120, self._focus)

    def _focus(self):
        self.lift()
        self.grab_set()

    # command preview: regenerated unless the user edited it by hand
    def _resolved_dir(self) -> str | None:
        if self.profile and self.profile.is_default:
            return None
        d = self.folder.get().strip()
        if d:
            return d
        ident = self.profile.id if self.profile else slug(self.name.get())
        return str(profiles_dir() / ident)

    def _generated(self) -> str:
        return launcher.build_command(self.app.store.exe_path, self._resolved_dir())

    def _sync(self):
        if not self.edited:
            self._syncing = True
            self.command.set(self._generated())
            self._syncing = False

    def _on_command(self):
        if self._syncing:
            return
        if self.command.get() != self._generated():
            self.edited = True
            self._refresh_hint()

    def _refresh_hint(self):
        self.hint.configure(text="Edited by hand — used exactly as written." if self.edited
                            else "Generated from the Claude path and data folder.")
        if self.edited:
            self.regen.pack(side="right")
        else:
            self.regen.pack_forget()

    def _regenerate(self):
        self.edited = False
        self._sync()
        self._refresh_hint()

    def _section(self, parent, title):
        label(parent, title, 13, T.TEXT, True).pack(anchor="w", pady=(12, 4))

    def _build(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=(20, 20))
        label(body, "Edit profile" if self.profile else "New profile", 22, T.TEXT, True).pack(anchor="w")

        box = card(body)
        box.pack(fill="x", pady=(14, 0))
        inner = ctk.CTkFrame(box, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=(0, 16))

        self._section(inner, "Name")
        e = entry(inner, self.name, "e.g. Personal, Company A", width=440)
        e.pack(fill="x")
        e.bind("<Return>", lambda _: self._save())

        self._section(inner, "Color")
        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(anchor="w")
        for c in T.PROFILE_COLORS:
            b = ctk.CTkButton(row, text="", width=24, height=24, corner_radius=12, fg_color=c, hover_color=c,
                              border_width=2 if c == self.color else 0, border_color=T.TEXT,
                              command=lambda c=c: self._pick(c))
            b.pack(side="left", padx=(0, 10))
            self._swatches.append(b)

        if not (self.profile and self.profile.is_default):
            self._section(inner, "Data folder (--user-data-dir)")
            r = ctk.CTkFrame(inner, fg_color="transparent")
            r.pack(fill="x")
            entry(r, self.folder, "Leave empty to create one in Claudou\\profiles", mono=True).pack(
                side="left", fill="x", expand=True)
            button(r, "Choose…", self._choose, width=84).pack(side="left", padx=(8, 0))

        self._section(inner, "Launch command")
        entry(inner, self.command, mono=True).pack(fill="x")
        h = ctk.CTkFrame(inner, fg_color="transparent")
        h.pack(fill="x", pady=(6, 0))
        self.hint = label(h, "", 11, T.DIM)
        self.hint.pack(side="left")
        self.regen = ctk.CTkButton(h, text="Regenerate", width=80, height=20, corner_radius=RADIUS_CONTROL,
                                   fg_color="transparent", hover_color=T.CARD_HOVER, text_color=T.ACCENT,
                                   font=font(11, True), command=self._regenerate)
        self._refresh_hint()

        btns = ctk.CTkFrame(body, fg_color="transparent")
        btns.pack(fill="x", pady=(16, 0))
        button(btns, "Cancel", self.destroy, width=84).pack(side="left")
        button(btns, "Save", self._save, primary=True, width=84).pack(side="right")

    def _pick(self, c):
        self.color = c
        for b, col in zip(self._swatches, T.PROFILE_COLORS):
            b.configure(border_width=2 if col == c else 0)

    def _choose(self):
        d = filedialog.askdirectory(parent=self, title="Choose data folder", mustexist=False)
        if d:
            self.folder.set(os.path.normpath(d))

    def _save(self):
        name = self.name.get().strip()
        if not name:
            return messagebox.showwarning("Name required", "Please enter a profile name.", parent=self)
        folder = self.folder.get().strip() or None
        cmd = self.command.get() if self.edited else None
        store = self.app.store
        if self.profile:
            p = self.profile
            p.name, p.color_hex = name, self.color
            if not p.is_default:
                p.data_dir = folder
            p.command, p.command_edited = cmd, self.edited
            store.update(p)
        else:
            store.create(name, self.color, folder, cmd, self.edited)
        self.on_saved()
        self.destroy()


# ───────────────────────── Settings (profile CRUD) ─────────────────────────

class SettingsWindow(ctk.CTkToplevel):
    ROW_H = 64

    def __init__(self, app: "App"):
        super().__init__(app.root)
        self.app = app
        self.title("Settings")
        apply_icon(self)
        self.configure(fg_color=T.BG)
        self.resizable(False, False)
        self.path = ctk.StringVar(value=app.store.exe_path)
        self.startup_var = ctk.BooleanVar(value=startup.is_enabled())
        self._logo = _logo(56, 13)
        self._build()
        self.path.trace_add("write", lambda *_: self._path_changed())
        self.refresh()

    def _build(self):
        pad = ctk.CTkFrame(self, fg_color="transparent")
        pad.pack(fill="both", expand=True, padx=12, pady=(8, 12))
        self.body = pad

        head = ctk.CTkFrame(pad, fg_color="transparent")
        head.pack(fill="x", padx=8, pady=(8, 14))
        if self._logo:
            ctk.CTkLabel(head, text="", image=self._logo).pack(side="left", padx=(0, 16))
        titles = ctk.CTkFrame(head, fg_color="transparent")
        titles.pack(side="left")
        label(titles, APP_NAME, 26, T.TEXT, True, anchor="w").pack(anchor="w")
        label(titles, "Run several Claude accounts side by side.", 13, T.DIM, anchor="w").pack(anchor="w")

        # Claude executable
        app_card = card(pad)
        app_card.pack(fill="x", padx=8)
        label(app_card, "Claude executable", 14, T.TEXT, True).pack(anchor="w", padx=16, pady=(14, 8))
        r = ctk.CTkFrame(app_card, fg_color="transparent")
        r.pack(fill="x", padx=16, pady=(0, 16))
        entry(r, self.path, "C:\\...\\claude.exe", mono=True).pack(side="left", fill="x", expand=True)
        button(r, "Browse…", self._browse, width=84).pack(side="left", padx=(8, 0))
        button(r, "Auto-detect", self._detect, width=96).pack(side="left", padx=(8, 0))

        self.banner = ctk.CTkFrame(pad, corner_radius=RADIUS_CARD, fg_color=T.SUCCESS_BG)
        self.banner.pack(fill="x", padx=8, pady=(10, 0))
        self.status = label(self.banner, "", 13, T.TEXT, True, anchor="w")
        self.status.pack(anchor="w", padx=16, pady=12)

        # Launch at startup
        st = card(pad)
        st.pack(fill="x", padx=8, pady=(10, 0))
        text = ctk.CTkFrame(st, fg_color="transparent")
        text.pack(side="left", padx=16, pady=14)
        label(text, "Launch at startup", 14, T.TEXT, True, anchor="w").pack(anchor="w")
        can = startup.supported()
        label(text, "Start Claudou in the tray when your computer starts." if can
              else "Available in the packaged Claudou.exe.", 12, T.DIM, anchor="w").pack(anchor="w")
        self.startup_switch = ctk.CTkSwitch(st, text="", variable=self.startup_var, command=self._toggle_startup,
                                            progress_color=T.ACCENT, state="normal" if can else "disabled")
        self.startup_switch.pack(side="right", padx=16)

        # Profiles
        ph = ctk.CTkFrame(pad, fg_color="transparent")
        ph.pack(fill="x", padx=8, pady=(18, 8))
        label(ph, "Profiles", 17, T.TEXT, True).pack(side="left")
        button(ph, "+ New profile", lambda: self.app.open_editor(None, self.refresh), primary=True,
               width=110).pack(side="right")
        self.list_host = ctk.CTkFrame(pad, fg_color="transparent")
        self.list_host.pack(fill="x", padx=8)
        self._path_changed(save=False)

    def _toggle_startup(self):
        want = self.startup_var.get()
        try:
            startup.set_enabled(want)
        except OSError as e:
            self.startup_var.set(startup.is_enabled())
            messagebox.showerror("Launch at startup", f"Could not change the startup setting: {e}", parent=self)

    def _path_changed(self, save=True):
        v = self.path.get().strip()
        if save:
            self.app.store.exe_path = v
        ok = bool(v) and os.path.exists(v)
        self.banner.configure(fg_color=T.SUCCESS_BG if ok else T.WARNING_BG)
        self.status.configure(text=("✔  Claude found" if ok else "⚠  Not found at this path"))
        self.app.refresh()

    def _browse(self):
        f = filedialog.askopenfilename(parent=self, title="Select claude.exe",
                                       filetypes=[("Executable", "*.exe"), ("All files", "*.*")])
        if f:
            self.path.set(os.path.normpath(f))

    def _detect(self):
        found = launcher.detect_claude_exe()
        if found:
            self.path.set(found)
        else:
            messagebox.showinfo("Not found", "Could not find Claude automatically. Use Browse…", parent=self)

    MAX_ROWS = 5            # more profiles than this scroll inside the list instead of growing the window

    def refresh(self):
        for w in self.list_host.winfo_children():
            w.destroy()
        profiles = self.app.store.profiles
        if len(profiles) > self.MAX_ROWS:
            self.list = ctk.CTkScrollableFrame(self.list_host, fg_color="transparent", corner_radius=0,
                                               scrollbar_button_color=T.BORDER,
                                               scrollbar_button_hover_color=T.ACCENT)
            self.list.configure(height=self.MAX_ROWS * (self.ROW_H + 8))
        else:
            self.list = ctk.CTkFrame(self.list_host, fg_color="transparent")
        self.list.pack(fill="x")
        for i, p in enumerate(profiles):
            self._row(p, i, len(profiles))
        self.update_idletasks()
        self.geometry(f"580x{self.winfo_reqheight()}")
        self.app.refresh()

    def _row(self, p: Profile, index: int, total: int):
        store, running = self.app.store, self.app.running
        row = card(self.list, height=self.ROW_H)
        row.pack(fill="x", pady=(0, 8))
        row.pack_propagate(False)
        order = ctk.CTkFrame(row, fg_color="transparent")
        order.pack(side="left", padx=(6, 0))
        for text, delta, enabled in (("▲", -1, index > 0), ("▼", 1, index < total - 1)):
            ctk.CTkButton(order, text=text, width=24, height=24, corner_radius=RADIUS_CONTROL,
                          fg_color="transparent", hover_color=T.CARD_HOVER, font=font(9),
                          text_color=T.DIM if enabled else T.BORDER, state="normal" if enabled else "disabled",
                          command=lambda d=delta: self._move(p, d)).pack()
        avatar(row, p, 40).pack(side="left", padx=(6, 12))
        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)
        tags = ctk.CTkFrame(info, fg_color="transparent")
        tags.pack(anchor="w")
        label(tags, p.name, 14, T.TEXT, True).pack(side="left")
        if p.id in running:
            label(tags, "  RUNNING", 9, T.SUCCESS, True).pack(side="left")
        if p.is_default:
            label(tags, "  DEFAULT", 9, T.DIM, True).pack(side="left")
        shown = str(p.dir).replace(os.path.expanduser("~"), "~")
        label(info, shown if len(shown) < 40 else "…" + shown[-39:], 11, T.DIM, anchor="w").pack(anchor="w")

        can_del = store.can_delete(p, running)
        ctk.CTkButton(row, text="🗑", width=28, height=28, corner_radius=RADIUS_CONTROL, fg_color="transparent",
                      hover_color=T.CARD_HOVER, text_color="#e03131" if can_del else T.BORDER,
                      state="normal" if can_del else "disabled", command=lambda: self._delete(p)
                      ).pack(side="right", padx=(0, 8))
        button(row, "Edit", lambda: self.app.open_editor(p, self.refresh), width=52, height=28
               ).pack(side="right", padx=4)
        ctk.CTkButton(row, text="📁", width=28, height=28, corner_radius=RADIUS_CONTROL, fg_color="transparent",
                      hover_color=T.CARD_HOVER, text_color=T.DIM,
                      command=lambda: self._reveal(p)).pack(side="right")

    def _move(self, p: Profile, delta: int):
        self.app.store.move(p.id, delta)
        self.refresh()

    def _reveal(self, p: Profile):
        p.dir.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["explorer", str(p.dir)])

    def _delete(self, p: Profile):
        owned = self.app.store.is_owned_folder(p)
        msg = (f"Delete “{p.name}”?\n\nSessions and chat history in this profile will be erased." if owned else
               f"Remove “{p.name}” from the list?\n\nThe data folder is kept; it is only removed from Claudou.")
        if messagebox.askyesno("Delete profile" if owned else "Remove profile", msg, parent=self):
            self.app.store.delete(p, self.app.running)
            self.refresh()


# ───────────────────────── Main (launcher) window ─────────────────────────

class App:
    ROW_H = 48
    WIDTH = 340

    def __init__(self):
        ctk.set_appearance_mode("system")
        self.root = ctk.CTk()
        self.root.title(APP_NAME)
        apply_icon(self.root)
        self.root.configure(fg_color=T.BG)
        self.root.resizable(False, False)
        self.store = ProfileStore()
        self.running: dict[str, int] = {}
        self.launching: str | None = None
        self._inbox: queue.Queue = queue.Queue()       # worker/tray → UI thread
        self._stop = threading.Event()
        self._settings: SettingsWindow | None = None
        self._tray = None
        self._logo = _logo(30, 7)

        self._build()
        self.refresh()
        threading.Thread(target=self._poll_loop, daemon=True).start()
        self._start_tray()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<Control-q>", lambda _: self.quit())
        self.root.after(400, self._tick)

    # ── layout ──

    def _build(self):
        head = ctk.CTkFrame(self.root, fg_color="transparent")
        head.pack(fill="x", padx=14, pady=(14, 12))
        if self._logo:
            ctk.CTkLabel(head, text="", image=self._logo).pack(side="left", padx=(0, 10))
        titles = ctk.CTkFrame(head, fg_color="transparent")
        titles.pack(side="left")
        label(titles, APP_NAME, 14, T.TEXT, True, anchor="w").pack(anchor="w")
        self.status = label(titles, "Idle", 12, T.DIM, True, anchor="w")
        self.status.pack(anchor="w")
        # Footer first, packed to the bottom: it keeps its space however small the window ends up.
        foot = ctk.CTkFrame(self.root, fg_color="transparent")
        foot.pack(fill="x", padx=8, pady=6, side="bottom")
        for text, cmd in (("Settings…", self.open_settings), ("Quit", self.quit)):
            ctk.CTkButton(foot, text=text, command=cmd, height=28, corner_radius=RADIUS_CONTROL,
                          fg_color="transparent", hover_color=T.CARD_HOVER, text_color=T.TEXT,
                          font=font(13), anchor="w").pack(fill="x")
        divider(self.root).pack(fill="x", padx=14, side="bottom")

        self.list = ctk.CTkScrollableFrame(self.root, fg_color="transparent", corner_radius=0,
                                           scrollbar_button_color=T.BORDER, scrollbar_button_hover_color=T.ACCENT)
        self.list.pack(fill="both", expand=True, padx=(8, 2), pady=(6, 6))

    def refresh(self):
        for w in self.list.winfo_children():
            w.destroy()
        for p in self.store.profiles:
            self._row(p)
        n = len(self.store.profiles)
        h = min(n * (self.ROW_H + 2), 330)
        self.list.configure(height=h)
        self.list._parent_frame.configure(height=h)      # the frame around the canvas keeps a 200 px minimum
        if n * (self.ROW_H + 2) > 330:
            self.list._scrollbar.grid()
        else:
            self.list._scrollbar.grid_remove()           # nothing to scroll
        running = len(self.running)
        self.status.configure(text=f"{running} running" if running else "Idle",
                              text_color=T.SUCCESS if running else T.DIM)
        self.root.update_idletasks()
        # Sum the stacked children by hand: the root's own request keeps the scrollable frame's 200 px minimum.
        total = sum((h if w is self.list._parent_frame else w.winfo_reqheight()) + _pady(w)
                    for w in self.root.winfo_children() if w.winfo_manager() == "pack")   # skip Toplevels
        self.root.geometry(f"{self.WIDTH}x{total}")
        self._place()

    def _place(self):
        """Dock the launcher in the bottom-right corner of the work area, so the taskbar never covers it."""
        self.root.update_idletasks()
        try:
            user32 = ctypes.windll.user32
            work = wintypes.RECT()
            user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(work), 0)       # SPI_GETWORKAREA
            frame = wintypes.RECT()
            user32.GetWindowRect(user32.GetParent(self.root.winfo_id()), ctypes.byref(frame))
            w, h = frame.right - frame.left, frame.bottom - frame.top
            x, y = work.right - w - 12, work.bottom - h - 12
        except Exception:
            x = self.root.winfo_screenwidth() - self.root.winfo_width() - 12
            y = self.root.winfo_screenheight() - self.root.winfo_height() - 64
        tk.Wm.wm_geometry(self.root, f"+{max(0, x)}+{max(0, y)}")       # raw pixels, no customtkinter scaling

    def _row(self, p: Profile):
        is_running = p.id in self.running
        row = ctk.CTkFrame(self.list, fg_color="transparent", corner_radius=RADIUS_CONTROL, height=self.ROW_H)
        row.pack(fill="x", pady=(0, 2))
        row.pack_propagate(False)

        avatar(row, p, 30).pack(side="left", padx=(12, 10))
        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)
        label(info, p.name, 13, T.TEXT, True, anchor="w").pack(anchor="w")
        sub = "Running" if is_running else ("Never opened" if not p.last_used else "Opened " + _fmt(p.last_used))
        label(info, sub, 11, T.SUCCESS if is_running else T.DIM, anchor="w").pack(anchor="w")

        # Fixed slot so Open/Show line up whether or not the quit button is shown.
        slot = ctk.CTkFrame(row, fg_color="transparent", width=28, height=28)
        slot.pack(side="right", padx=(0, 6))
        slot.pack_propagate(False)
        if is_running:
            ctk.CTkButton(slot, text="✕", width=24, height=24, corner_radius=RADIUS_CONTROL,
                          fg_color="transparent", hover_color=T.BUTTON, text_color=T.DIM,
                          command=lambda: self.quit_profile(p)).pack()
        if self.launching == p.id:
            label(row, "Opening…", 11, T.ACCENT).pack(side="right", padx=8)
        else:
            pill(row, "Show" if is_running else "Open", lambda: self.open_profile(p),
                 T.SUCCESS_STRONG if is_running else T.ACCENT,
                 T.SUCCESS_HOVER if is_running else T.ACCENT_HOVER).pack(side="right", padx=(0, 4))
        hover_highlight(row)
        for w in (row, *_descendants(row)):
            w.bind("<Double-Button-1>", lambda _, p=p: self.open_profile(p), add="+")

    # ── actions ──

    def open_profile(self, p: Profile):
        if p.id in self.running:
            return launcher.focus(self.running[p.id])
        if self.launching:
            return
        self.launching = p.id
        self.refresh()
        cmd, exe = self.store.effective_command(p), self.store.exe_path

        def work():
            try:
                launcher.run_command(cmd, exe)
                self._inbox.put(("launched", p.id, None))
            except Exception as e:
                self._inbox.put(("launched", p.id, str(e)))
        threading.Thread(target=work, daemon=True).start()

    def quit_profile(self, p: Profile):
        pid = self.running.get(p.id)
        if pid:
            threading.Thread(target=launcher.quit_pid, args=(pid,), daemon=True).start()

    def open_editor(self, profile: Profile | None, on_saved=None):
        def saved():
            self.refresh()
            if on_saved:
                on_saved()
        EditorWindow(self, profile, saved)

    def open_settings(self):
        if self._settings and self._settings.winfo_exists():
            self._settings.lift()
            return
        self._settings = SettingsWindow(self)

    def show(self):
        self.root.deiconify()
        self._place()
        self.root.lift()
        self.root.focus_force()

    # ── background work ──

    def _poll_loop(self):
        while not self._stop.is_set():
            try:
                self._inbox.put(("running", launcher.running_pids(self.store.running_spec()), None))
            except Exception:
                pass
            self._stop.wait(2)

    def _tick(self):
        dirty = False
        try:
            while True:
                kind, a, b = self._inbox.get_nowait()
                if kind == "running" and a != self.running:
                    self.running, dirty = a, True
                elif kind == "launched":
                    self.launching = None
                    dirty = True
                    if b:
                        messagebox.showerror("Error", b, parent=self.root)
                    else:
                        self.store.mark_used(a)
                elif kind == "show":
                    self.show()
                elif kind == "quit":
                    return self.quit()
        except queue.Empty:
            pass
        if dirty:
            self.refresh()
            if self._settings and self._settings.winfo_exists():
                self._settings.refresh()
        self.root.after(400, self._tick)

    # ── tray ──

    def _start_tray(self):
        if pystray is None:
            return
        try:
            img = icon_frame(64)
            menu = pystray.Menu(
                pystray.MenuItem("Show", lambda: self._inbox.put(("show", None, None)), default=True),
                pystray.MenuItem("Quit", lambda: self._inbox.put(("quit", None, None))))
            self._tray = pystray.Icon(APP_NAME, img, f"{APP_NAME} {APP_VERSION}", menu)
            self._tray.run_detached()
        except Exception:
            self._tray = None

    def _on_close(self):
        if self._tray:
            self.root.withdraw()      # keep running in the tray
        else:
            self.quit()

    def quit(self):
        self._stop.set()
        if self._tray:
            try:
                self._tray.stop()
            except Exception:
                pass
        self.root.destroy()


def _pady(widget) -> int:
    pad = widget.pack_info().get("pady", 0)
    return sum(pad) if isinstance(pad, (tuple, list)) else 2 * int(pad)


def _fmt(iso: str) -> str:
    from datetime import datetime, timezone
    try:
        d = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).astimezone()
        return d.strftime("%b %d, %H:%M")
    except ValueError:
        return iso


def main():
    App().root.mainloop()
