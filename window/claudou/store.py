"""Profile model, persistence and settings. Config schema: docs/SPEC.md (shared with macOS)."""
from __future__ import annotations

import json
import os
import re
import shutil
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import launcher
from .theme import PROFILE_COLORS

DEFAULT_ID = "default"


def claudou_root() -> Path:
    override = os.environ.get("CLAUDOU_HOME")
    if override:
        return Path(override)
    return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "Claudou"


def profiles_dir() -> Path:
    return claudou_root() / "profiles"


def default_data_dir() -> Path:
    """Claude's own data folder, used by the Default profile (launched without flags)."""
    return Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming") / "Claude"


def slug(name: str) -> str:
    s = unicodedata.normalize("NFKD", name.replace("đ", "d").replace("Đ", "D"))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z0-9\-]+", "_", s).strip("_")
    return s or "profile"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Profile:
    id: str
    name: str
    color_hex: str
    last_used: str | None = None
    data_dir: str | None = None       # None → profiles/<id> (or Claude's own folder for "default")
    command: str | None = None        # used verbatim only when command_edited
    command_edited: bool = False

    @property
    def is_default(self) -> bool:
        return self.id == DEFAULT_ID

    @property
    def initial(self) -> str:
        n = self.name.strip()
        return n[0].upper() if n else "?"

    @property
    def dir(self) -> Path:
        if self.is_default:
            return default_data_dir()
        return Path(self.data_dir) if self.data_dir else profiles_dir() / self.id

    def to_json(self) -> dict:
        d = {"id": self.id, "name": self.name, "colorHex": self.color_hex,
             "commandEdited": self.command_edited}
        for key, val in (("lastUsed", self.last_used), ("dataDir", self.data_dir), ("command", self.command)):
            if val:
                d[key] = val
        return d

    @classmethod
    def from_json(cls, d: dict) -> "Profile":
        return cls(id=d["id"], name=d["name"], color_hex=d.get("colorHex", PROFILE_COLORS[0]),
                   last_used=d.get("lastUsed"), data_dir=d.get("dataDir"), command=d.get("command"),
                   command_edited=bool(d.get("commandEdited", False)))


class ProfileStore:
    def __init__(self):
        profiles_dir().mkdir(parents=True, exist_ok=True)
        self.profiles: list[Profile] = []
        self._load()
        if not any(p.is_default for p in self.profiles):
            self.profiles.insert(0, Profile(DEFAULT_ID, "Default", PROFILE_COLORS[0]))
            self._save()

    # ── Settings: path of claude.exe ──

    @property
    def _settings_file(self) -> Path:
        return claudou_root() / "settings.json"

    @property
    def exe_path(self) -> str:
        try:
            saved = json.loads(self._settings_file.read_text(encoding="utf-8")).get("claudeExePath", "")
        except (OSError, ValueError):
            saved = ""
        return saved or launcher.detect_claude_exe()

    @exe_path.setter
    def exe_path(self, value: str):
        self._settings_file.write_text(json.dumps({"claudeExePath": value.strip()}, indent=2), encoding="utf-8")

    # ── Persistence ──

    def _load(self):
        try:
            raw = json.loads((claudou_root() / "config.json").read_text(encoding="utf-8"))
            self.profiles = [Profile.from_json(d) for d in raw]
        except (OSError, ValueError, KeyError):
            self.profiles = []

    def _save(self):
        (claudou_root() / "config.json").write_text(
            json.dumps([p.to_json() for p in self.profiles], indent=2, ensure_ascii=False), encoding="utf-8")

    # ── Queries ──

    def get(self, pid: str) -> Profile | None:
        return next((p for p in self.profiles if p.id == pid), None)

    def effective_command(self, p: Profile) -> str:
        if p.command_edited and p.command:
            return p.command
        return launcher.build_command(self.exe_path, None if p.is_default else str(p.dir))

    def is_owned_folder(self, p: Profile) -> bool:
        return p.data_dir is None

    def can_delete(self, p: Profile, running: dict[str, int]) -> bool:
        return not p.is_default and p.id not in running

    def running_spec(self) -> list[tuple[str, str | None]]:
        return [(p.id, None if p.is_default else str(p.dir)) for p in self.profiles]

    # ── CRUD ──

    def create(self, name: str, color_hex: str, data_dir: str | None = None,
               command: str | None = None, command_edited: bool = False) -> Profile:
        base = new_id = slug(name)
        i = 2
        while self.get(new_id):
            new_id, i = f"{base}_{i}", i + 1
        p = Profile(new_id, name, color_hex, None, data_dir or None, command, command_edited)
        p.dir.mkdir(parents=True, exist_ok=True)
        self.profiles.append(p)
        self._save()
        return p

    def update(self, p: Profile):
        for i, existing in enumerate(self.profiles):
            if existing.id == p.id:
                self.profiles[i] = p
        self._save()

    def mark_used(self, pid: str):
        p = self.get(pid)
        if p:
            p.last_used = _now()
            self._save()

    def delete(self, p: Profile, running: dict[str, int]):
        """Erases Claudou-owned folders only; folders chosen by the user are just un-listed."""
        if not self.can_delete(p, running):
            return
        if self.is_owned_folder(p):
            shutil.rmtree(p.dir, ignore_errors=True)
        self.profiles = [x for x in self.profiles if x.id != p.id]
        self._save()
