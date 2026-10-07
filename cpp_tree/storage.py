"""Versioned JSON state, exclusive writer locks, and atomic backups."""

from __future__ import annotations

import datetime as dt
import fcntl
import json
import os
import tempfile
from pathlib import Path
from typing import TextIO, cast, final

from .curriculum import CHAPTERS, GROUPS, group_keys
from .models import JsonValue, StateData


def default_state() -> StateData:
    return {
        "version": 1,
        "completed": [],
        "notes": {},
        "focus": None,
        "name": "C++ ADVENTURER",
        "view": {"group": "main", "chapter": None, "index": 0, "stream": False},
    }


def parse_state(raw: JsonValue) -> StateData:
    """Validate saved JSON before it enters the typed application state."""
    if not isinstance(raw, dict) or type(raw.get("version")) is not int or raw.get("version") != 1:
        raise ValueError("unsupported progress format")
    completed = raw.get("completed")
    if not isinstance(completed, list):
        raise ValueError("completed must be a list of lesson IDs")
    done: list[str] = []
    for key in completed:
        if not isinstance(key, str):
            raise ValueError("completed must be a list of lesson IDs")
        done.append(key)
    focus = raw.get("focus")
    if focus is not None and not isinstance(focus, str):
        raise ValueError("focus must be a lesson ID or null")
    name = raw.get("name", "C++ ADVENTURER")
    view = raw.get("view", {})
    if not isinstance(name, str) or not isinstance(view, dict):
        raise ValueError("invalid profile or view")
    raw_notes = raw.get("notes", {})
    if not isinstance(raw_notes, dict):
        raise ValueError("notes must map lesson or chapter IDs to text")
    notes: dict[str, str] = {}
    for key, value in raw_notes.items():
        if not isinstance(value, str):
            raise ValueError("notes must map lesson or chapter IDs to text")
        notes[key] = value

    # View preferences are optional. Normalize old or invalid values safely.
    group = view.get("group", "main")
    chapter = view.get("chapter")
    index = view.get("index", 0)
    return {
        "version": 1,
        "completed": done,
        "notes": notes,
        "focus": focus,
        "name": name,
        "view": {
            "group": group if isinstance(group, str) and group in GROUPS else "main",
            "chapter": chapter if isinstance(chapter, str) and chapter in CHAPTERS else None,
            "index": max(0, index) if type(index) is int else 0,
            "stream": view.get("stream") is True,
        },
    }


class StateError(Exception):
    """Progress could not be read or locked; the original file is preserved."""


def read_snapshot(path: Path) -> StateData:
    """Read an atomic snapshot without creating files or taking a writer lock."""
    try:
        return parse_state(cast(JsonValue, json.loads(path.read_text(encoding="utf-8"))))
    except FileNotFoundError:
        return default_state()
    except (OSError, ValueError) as exc:
        raise StateError(f"Could not read progress: {path}\n{exc}") from exc


@final
class Store:
    """One writer; atomic replacement and a previous-good-state backup."""

    def __init__(self, path: str | Path, demo: bool = False) -> None:
        self.path, self.demo = Path(path), demo
        self.lock: TextIO | None = None
        self.data = default_state()
        self.extra: dict[str, JsonValue] = {}
        if demo:
            self.data["name"] = "C++ ADVENTURER"
            self.data["completed"] = group_keys("main")[:43]
            self.data["focus"] = "3:3.6"
            self.data["notes"] = {
                "chapter:3": "Use small experiments to practice stepping and breakpoints.\nKeep the debugger open while tracing function calls.",
                "lesson:3:3.6": "Step into follows a function call. Step over runs it without entering.\nTry both on a small program.",
            }
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.lock = open(str(self.path) + ".lock", "a+", encoding="utf-8")
            fcntl.flock(self.lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError) as exc:
            self.close()
            raise StateError(
                "Cannot lock progress. Another cpp-tree may be open, or the folder is not writable.\n"
                + f"File: {self.path}\n{exc}"
            ) from exc
        try:
            if self.path.exists():
                raw = cast(JsonValue, json.loads(self.path.read_text(encoding="utf-8")))
                self.data = parse_state(raw)
                if isinstance(raw, dict):
                    self.extra = {key: value for key, value in raw.items() if key not in self.data}
        except (OSError, ValueError) as exc:
            self.close()
            raise StateError(
                f"Could not read progress: {self.path}\n{exc}\n"
                + f"Your file was left untouched. A previous save may be available at {self.path}.bak.\n"
                + "Use --state /another/path.json to start a separate profile."
            ) from exc

    @staticmethod
    def atomic_write(path: Path, data: bytes) -> None:
        tmp = None
        try:
            fd, tmp = tempfile.mkstemp(prefix=".cpp-tree-", dir=path.parent)
            with os.fdopen(fd, "wb") as f:
                _ = f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        finally:
            if tmp and os.path.exists(tmp):
                os.unlink(tmp)

    def save(self) -> None:
        if self.demo:
            return
        payload: dict[str, object] = {
            **self.extra,
            **self.data,
            "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
        encoded = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        if self.path.exists():
            self.atomic_write(Path(str(self.path) + ".bak"), self.path.read_bytes())
        self.atomic_write(self.path, encoded)

    def close(self) -> None:
        if self.lock:
            self.lock.close()
            self.lock = None
