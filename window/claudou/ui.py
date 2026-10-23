"""Claudou UI (customtkinter): compact launcher window, Settings (profile CRUD) and profile editor.

Mirrors the macOS app (menu bar popover + Settings); see docs/SPEC.md.
"""
from __future__ import annotations

import os
import queue
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

from . import APP_NAME, APP_VERSION, launcher
from . import theme as T
from .store import Profile, ProfileStore, profiles_dir, slug

try:
    import pystray
except Exception:  # tray is optional
    pystray = None

FONT = "Segoe UI"


def font(size: int, bold: bool = False) -> ctk.CTkFont:
    return ctk.CTkFont(family=FONT, size=size, weight="bold" if bold else "normal")


def accent_btn(parent, text, command, color=T.ACCENT, hover=T.ACCENT_HOVER, width=0, **kw):
    return ctk.CTkButton(parent, text=text, command=command, width=width, height=26, corner_radius=0,
                         fg_color=color, hover_color=hover, text_color="white", font=font(11, True), **kw)


def ghost_btn(parent, text, command, width=0, **kw):
    return ctk.CTkButton(parent, text=text, command=command, width=width, height=26, corner_radius=0,
                         fg_color="transparent", hover_color=T.CARD, text_color=T.DIM,
                         border_width=1, border_color=T.BORDER, font=font(11), **kw)


def entry(parent, var, placeholder="", mono=False, **kw):
    return ctk.CTkEntry(parent, textvariable=var, placeholder_text=placeholder, height=30, corner_radius=0,
                        fg_color=T.INPUT, border_color=T.BORDER, border_width=1, text_color=T.TEXT,
                        placeholder_text_color=T.DIM, font=ctk.CTkFont(family="Consolas" if mono else FONT, size=11 if mono else 12),
                        **kw)


def label(parent, text, size=11, color=T.DIM, bold=False, **kw):
    return ctk.CTkLabel(parent, text=text, text_color=color, font=font(size, bold), **kw)


def rule(parent, color=T.BORDER):
    return ctk.CTkFrame(parent, fg_color=color, height=1, corner_radius=0)


def _logo(size: int) -> ctk.CTkImage | None:
    try:
        img = Image.open(T.asset("logo.png")).convert("RGBA")
        return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
    except Exception:
        return None


# ───────────────────────── Profile editor ─────────────────────────

class EditorWindow(ctk.CTkToplevel):
    def __init__(self, app: "App", profile: Profile | None, on_saved):
        super().__init__(app.root)
        self.app, self.profile, self.on_saved = app, profile, on_saved
        self.title("Edit profile" if profile else "New profile")
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

    def _section(self, title):
        label(self.body, title, 10, T.DIM, True).pack(anchor="w", pady=(10, 4))

    def _build(self):
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=18, pady=16)
        label(self.body, "Edit profile" if self.profile else "New profile", 15, T.TEXT, True).pack(anchor="w")

        self._section("NAME")
        e = entry(self.body, self.name, "e.g. Personal, Company A", width=420)
        e.pack(fill="x")
        e.bind("<Return>", lambda _: self._save())

        self._section("COLOR")
        row = ctk.CTkFrame(self.body, fg_color="transparent")
        row.pack(anchor="w")
        for c in T.PROFILE_COLORS:
            b = ctk.CTkButton(row, text="", width=22, height=22, corner_radius=0, fg_color=c, hover_color=c,
                              border_width=2 if c == self.color else 0, border_color=T.TEXT,
                              command=lambda c=c: self._pick(c))
            b.pack(side="left", padx=(0, 8))
            self._swatches.append(b)

        if not (self.profile and self.profile.is_default):
            self._section("DATA FOLDER (--user-data-dir)")
            r = ctk.CTkFrame(self.body, fg_color="transparent")
            r.pack(fill="x")
            entry(r, self.folder, "Leave empty to create one in Claudou\\profiles", mono=True).pack(
                side="left", fill="x", expand=True)
            ghost_btn(r, "Choose…", self._choose, width=70).pack(side="left", padx=(6, 0))

        self._section("LAUNCH COMMAND")
        entry(self.body, self.command, mono=True).pack(fill="x")
        h = ctk.CTkFrame(self.body, fg_color="transparent")
        h.pack(fill="x", pady=(4, 0))
        self.hint = label(h, "", 10)
        self.hint.pack(side="left")
        self.regen = ctk.CTkButton(h, text="Regenerate", width=70, height=18, corner_radius=0,
                                   fg_color="transparent", hover_color=T.BG, text_color=T.ACCENT,
                                   font=font(10, True), command=self._regenerate)
        self._refresh_hint()

        btns = ctk.CTkFrame(self.body, fg_color="transparent")
        btns.pack(fill="x", pady=(16, 0))
        ghost_btn(btns, "Cancel", self.destroy, width=70).pack(side="left")
        accent_btn(btns, "Save", self._save, width=80).pack(side="right")

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
    ROW_H = 46

    def __init__(self, app: "App"):
        super().__init__(app.root)
        self.app = app
        self.title("Settings")
        self.configure(fg_color=T.BG)
        self.geometry("520x470")
        self.resizable(False, False)
        self.path = ctk.StringVar(value=app.store.exe_path)
        self._build()
        self.path.trace_add("write", lambda *_: self._path_changed())
        self.refresh()

    def _build(self):
        pad = ctk.CTkFrame(self, fg_color="transparent")
        pad.pack(fill="both", expand=True, padx=18, pady=16)

        label(pad, "CLAUDE EXECUTABLE", 10, T.DIM, True).pack(anchor="w")
        r = ctk.CTkFrame(pad, fg_color="transparent")
        r.pack(fill="x", pady=(6, 4))
        entry(r, self.path, "C:\\...\\claude.exe", mono=True).pack(side="left", fill="x", expand=True)
        ghost_btn(r, "Browse…", self._browse, width=70).pack(side="left", padx=(6, 0))
        ghost_btn(r, "Auto-detect", self._detect, width=84).pack(side="left", padx=(6, 0))
        self.status = label(pad, "", 10)
        self.status.pack(anchor="w")

        rule(pad).pack(fill="x", pady=14)

        head = ctk.CTkFrame(pad, fg_color="transparent")
        head.pack(fill="x")
        label(head, "PROFILES", 10, T.DIM, True).pack(side="left")
        accent_btn(head, "+ New profile", lambda: self.app.open_editor(None, self.refresh), width=100).pack(side="right")

        self.list = ctk.CTkScrollableFrame(pad, fg_color="transparent", corner_radius=0, border_width=1,
                                           border_color=T.BORDER, height=240,
                                           scrollbar_button_color=T.BORDER, scrollbar_button_hover_color=T.ACCENT)
        self.list.pack(fill="x", pady=(8, 0))
        self._path_changed(save=False)

    def _path_changed(self, save=True):
        v = self.path.get().strip()
        if save:
            self.app.store.exe_path = v
        ok = bool(v) and os.path.exists(v)
        self.status.configure(text=("✔ Claude found" if ok else "⚠ Not found at this path"),
                              text_color=T.SUCCESS if ok else T.ACCENT)
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

    def refresh(self):
        for w in self.list.winfo_children():
            w.destroy()
        for p in self.app.store.profiles:
            self._row(p)
        self.app.refresh()

    def _row(self, p: Profile):
        store, running = self.app.store, self.app.running
        row = ctk.CTkFrame(self.list, fg_color="transparent", corner_radius=0, height=self.ROW_H)
        row.pack(fill="x")
        row.pack_propagate(False)
        label(row, p.initial, 13, "white", True, width=28, height=28, fg_color=p.color_hex, corner_radius=0
              ).pack(side="left", padx=(4, 10))
        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)
        tags = ctk.CTkFrame(info, fg_color="transparent")
        tags.pack(anchor="w")
        label(tags, p.name, 12, T.TEXT, True).pack(side="left")
        if p.id in running:
            label(tags, "  RUNNING", 8, T.SUCCESS, True).pack(side="left")
        if p.is_default:
            label(tags, "  DEFAULT", 8, T.DIM, True).pack(side="left")
        shown = str(p.dir).replace(os.path.expanduser("~"), "~")
        label(info, shown if len(shown) < 48 else "…" + shown[-47:], 10, T.DIM, anchor="w").pack(anchor="w")

        can_del = store.can_delete(p, running)
        ctk.CTkButton(row, text="🗑", width=26, height=26, corner_radius=0, fg_color="transparent",
                      hover_color=T.CARD_HOVER, text_color=T.ACCENT if can_del else T.BORDER,
                      state="normal" if can_del else "disabled", command=lambda: self._delete(p)).pack(side="right")
        ghost_btn(row, "Edit", lambda: self.app.open_editor(p, self.refresh), width=46).pack(side="right", padx=4)
        ctk.CTkButton(row, text="📁", width=26, height=26, corner_radius=0, fg_color="transparent",
                      hover_color=T.CARD_HOVER, text_color=T.DIM,
                      command=lambda: self._reveal(p)).pack(side="right")
        rule(self.list).pack(fill="x")

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
    ROW_H = 44
    WIDTH = 300

    def __init__(self):
        ctk.set_appearance_mode("dark")
        self.root = ctk.CTk()
        self.root.title(APP_NAME)
        self.root.configure(fg_color=T.BG)
        self.root.resizable(False, False)
        self.store = ProfileStore()
        self.running: dict[str, int] = {}
        self.launching: str | None = None
        self._inbox: queue.Queue = queue.Queue()       # worker/tray → UI thread
        self._stop = threading.Event()
        self._settings: SettingsWindow | None = None
        self._tray = None
        self._logo = _logo(22)

        self._build()
        self.refresh()
        threading.Thread(target=self._poll_loop, daemon=True).start()
        self._start_tray()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(400, self._tick)

    # ── layout ──

    def _build(self):
        head = ctk.CTkFrame(self.root, fg_color=T.SURFACE, corner_radius=0, height=40)
        head.pack(fill="x")
        head.pack_propagate(False)
        if self._logo:
            ctk.CTkLabel(head, text="", image=self._logo).pack(side="left", padx=(12, 8))
        label(head, APP_NAME, 13, T.TEXT, True).pack(side="left")
        self.status = label(head, "Idle", 10, T.DIM, True)
        self.status.pack(side="right", padx=12)
        rule(self.root, T.ACCENT).pack(fill="x")

        self.list = ctk.CTkScrollableFrame(self.root, fg_color="transparent", corner_radius=0,
                                           scrollbar_button_color=T.BORDER, scrollbar_button_hover_color=T.ACCENT)
        self.list.pack(fill="both", expand=True)

        foot = ctk.CTkFrame(self.root, fg_color=T.SURFACE, corner_radius=0, height=34)
        foot.pack(fill="x", side="bottom")
        foot.pack_propagate(False)
        for text, cmd, side in (("⚙ Settings", self.open_settings, "left"), ("Quit Claudou", self.quit, "right")):
            ctk.CTkButton(foot, text=text, command=cmd, width=96, height=24, corner_radius=0, fg_color="transparent",
                          hover_color=T.CARD, text_color=T.DIM, font=font(11)).pack(side=side, padx=8)

    def refresh(self):
        for w in self.list.winfo_children():
            w.destroy()
        for p in self.store.profiles:
            self._row(p)
        n = len(self.store.profiles)
        self.list.configure(height=min(n * (self.ROW_H + 1), 330))
        running = len(self.running)
        self.status.configure(text=f"{running} running" if running else "Idle",
                              text_color=T.SUCCESS if running else T.DIM)
        self.root.update_idletasks()
        h = self.root.winfo_reqheight()
        if not getattr(self, "_placed", False):
            x = self.root.winfo_screenwidth() - self.WIDTH - 12
            y = self.root.winfo_screenheight() - h - 64
            self.root.geometry(f"{self.WIDTH}x{h}+{x}+{y}")
            self._placed = True
        else:
            self.root.geometry(f"{self.WIDTH}x{h}")

    def _row(self, p: Profile):
        is_running = p.id in self.running
        row = ctk.CTkFrame(self.list, fg_color="transparent", corner_radius=0, height=self.ROW_H)
        row.pack(fill="x")
        row.pack_propagate(False)
        row.bind("<Enter>", lambda _: row.configure(fg_color=T.CARD_HOVER))
        row.bind("<Leave>", lambda _: row.configure(fg_color="transparent"))
        row.bind("<Double-Button-1>", lambda _: self.open_profile(p))

        label(row, p.initial, 13, "white", True, width=28, height=28, fg_color=p.color_hex, corner_radius=0
              ).pack(side="left", padx=(10, 10))
        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)
        label(info, p.name, 12, T.TEXT, True, anchor="w").pack(anchor="w")
        sub = "Running" if is_running else ("Never opened" if not p.last_used else "Last opened " + _fmt(p.last_used))
        label(info, sub, 10, T.SUCCESS if is_running else T.DIM, anchor="w").pack(anchor="w")

        if is_running:
            ctk.CTkButton(row, text="✕", width=22, height=22, corner_radius=0, fg_color="transparent",
                          hover_color=T.CARD, text_color=T.DIM,
                          command=lambda: self.quit_profile(p)).pack(side="right", padx=(0, 8))
        if self.launching == p.id:
            label(row, "Opening…", 10, T.ACCENT).pack(side="right", padx=8)
        else:
            accent_btn(row, "Show" if is_running else "Open", lambda: self.open_profile(p),
                       T.SUCCESS if is_running else T.ACCENT, "#4a9c63" if is_running else T.ACCENT_HOVER,
                       width=52).pack(side="right", padx=(0, 6))
        rule(self.list).pack(fill="x")

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
            img = Image.open(T.asset("logo.png")).convert("RGBA").resize((64, 64), Image.NEAREST)
            menu = pystray.Menu(
                pystray.MenuItem("Show", lambda: self._inbox.put(("show", None, None)), default=True),
                pystray.MenuItem("Quit Claudou", lambda: self._inbox.put(("quit", None, None))))
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


def _fmt(iso: str) -> str:
    from datetime import datetime, timezone
    try:
        d = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).astimezone()
        return d.strftime("%b %d, %H:%M")
    except ValueError:
        return iso


def main():
    App().root.mainloop()
