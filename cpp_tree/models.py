"""Shared data types; saved IDs are part of the compatibility contract."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Literal, TypedDict, final


class LessonNote(TypedDict, total=False):
    note: str


class Lesson(LessonNote):
    id: str
    key: str
    title: str
    url: str


class Chapter(TypedDict):
    id: str
    title: str
    group: str
    lessons: list[Lesson]


class ViewState(TypedDict):
    group: str
    chapter: str | None
    index: int
    stream: bool


class StateData(TypedDict):
    version: int
    completed: list[str]
    notes: dict[str, str]
    focus: str | None
    name: str
    view: ViewState


@final
class Options(argparse.Namespace):
    """Typed command-line values; argparse fills these from the declared flags."""

    name: str | None = None
    state: Path
    demo: bool = False
    stream: bool = False
    ascii: bool = False
    color: str = "auto"
    summary: bool = False
    state_path: bool = False
    uninstall: bool = False

    def __init__(self, state: Path) -> None:
        super().__init__()
        self.state = state


Node = Lesson | Chapter
Modal = (
    tuple[Literal["notes", "notes_confirm"], str, str, str]
    | tuple[Literal["bulk"], str]
    | tuple[Literal["search"]]
    | tuple[Literal["help"]]
)
JsonValue = bool | int | float | str | None | list["JsonValue"] | dict[str, "JsonValue"]
NoteRow = tuple[int, int, str]
BrowserJob = tuple[subprocess.Popen[bytes], str]
