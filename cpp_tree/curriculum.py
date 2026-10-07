"""Load the bundled outline. Lesson keys remain stable across releases."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import cast
from urllib.parse import urlsplit

from .models import Chapter

GROUPS = ("main", "side", "archive")
GROUP_LABELS = {"main": "MAIN TREE", "side": "SIDE QUESTS", "archive": "ARCHIVE"}


def validate_curriculum(raw: object) -> list[Chapter]:
    """Reject broken links, duplicates, and invalid shapes before building indexes."""
    if not isinstance(raw, list) or not raw:
        raise ValueError("curriculum must be a nonempty list")
    chapters: set[str] = set()
    lessons: set[str] = set()
    groups: set[str] = set()
    for chapter in raw:
        if not isinstance(chapter, dict):
            raise ValueError("each chapter must be an object")
        for field in ("id", "title", "group"):
            if not isinstance(chapter.get(field), str) or not chapter[field]:
                raise ValueError(f"chapter needs a nonempty {field}")
        if chapter["id"] in chapters or chapter["group"] not in GROUPS:
            raise ValueError("duplicate chapter ID or unknown group")
        chapters.add(chapter["id"])
        groups.add(chapter["group"])
        entries = chapter.get("lessons")
        if not isinstance(entries, list) or not entries:
            raise ValueError("chapters must contain lessons")
        for lesson in entries:
            if not isinstance(lesson, dict):
                raise ValueError("each lesson must be an object")
            for field in ("id", "key", "title", "url"):
                if not isinstance(lesson.get(field), str) or not lesson[field]:
                    raise ValueError(f"lesson needs a nonempty {field}")
            if lesson["key"] != f"{chapter['id']}:{lesson['id']}":
                raise ValueError("lesson key must match its chapter and lesson IDs")
            if lesson["key"] in lessons:
                raise ValueError("duplicate lesson key")
            lessons.add(lesson["key"])
            if "note" in lesson and not isinstance(lesson["note"], str):
                raise ValueError("outline notes must be text")
            url = urlsplit(lesson["url"])
            if (
                url.scheme != "https"
                or url.netloc != "www.learncpp.com"
                or not url.path.startswith("/cpp-tutorial/")
            ):
                raise ValueError("lesson URL must be a LearnCpp HTTPS article")
    if groups != set(GROUPS):
        raise ValueError("each navigation group must contain a chapter")
    return cast(list[Chapter], raw)


CURRICULUM = validate_curriculum(
    json.loads(
        files("cpp_tree").joinpath("data").joinpath("learncpp.json").read_text(encoding="utf-8")
    )
)
CHAPTERS = {c["id"]: c for c in CURRICULUM}
LESSONS = {l["key"]: l for c in CURRICULUM for l in c["lessons"]}
LESSON_CHAPTERS = {l["key"]: c for c in CURRICULUM for l in c["lessons"]}

SHORT = {
    "0": "The starting zone",
    "1": "C++ basics",
    "2": "Functions & files",
    "3": "The debugger",
    "4": "Fundamental types",
    "5": "Constants & strings",
    "6": "Operators",
    "O": "Bit manipulation",
    "7": "Scope & linkage",
    "8": "Control flow",
    "9": "Error detection",
    "10": "Conversions & auto",
    "11": "Overloads & templates",
    "F": "Constexpr functions",
    "12": "References & pointers",
    "13": "Enums & structs",
    "14": "Classes",
    "15": "More on classes",
    "16": "Dynamic arrays",
    "17": "Fixed-size arrays",
    "18": "Iterators & algorithms",
    "19": "Dynamic allocation",
    "20": "Functions",
    "21": "Operator overloading",
    "22": "Move & smart pointers",
    "23": "Object relationships",
    "24": "Inheritance",
    "25": "Virtual functions",
    "26": "Templates & classes",
    "27": "Exceptions",
    "28": "Input & output",
    "A": "Libraries & FAQ",
    "B": "C++ updates",
    "C": "The end?",
    "D": "Deprecated articles",
}


def group_chapters(group: str) -> list[Chapter]:
    return [c for c in CURRICULUM if c["group"] == group]


def group_keys(group: str) -> list[str]:
    return [l["key"] for c in group_chapters(group) for l in c["lessons"]]


def chapter_keys(chapter: Chapter) -> set[str]:
    return {l["key"] for l in chapter["lessons"]}
