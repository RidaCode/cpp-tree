"""Application interactions. Rendering and terminal I/O live separately."""

from __future__ import annotations

import copy
import curses
import time
from collections.abc import Sequence
from typing import final

from .browser import launch_browser
from .canvas import Canvas
from .curriculum import (
    CHAPTERS,
    CURRICULUM,
    GROUPS,
    LESSON_CHAPTERS,
    LESSONS,
    chapter_keys,
    group_chapters,
    group_keys,
)
from .models import BrowserJob, Chapter, Lesson, Modal, Node, NoteRow, Options
from .storage import Store
from .text import clean


@final
class App:
    def __init__(self, store: Store, args: Options) -> None:
        self.store, self.args = store, args
        self.done = set(store.data["completed"])
        self.focus: str | None = store.data["focus"]
        self.notes = dict(store.data["notes"])
        self.note_buffer, self.note_cursor, self.note_offset = "", 0, 0
        self.note_width = 60
        self.name = clean(args.name or store.data["name"] or "C++ ADVENTURER")[:30]
        view = store.data["view"]
        self.group = view["group"]
        if self.group not in GROUPS:
            self.group = "main"
        self.chapter: str | None = view["chapter"]
        if self.chapter is not None and self.chapter not in CHAPTERS:
            self.chapter = None
        if self.chapter:
            self.group = CHAPTERS[self.chapter]["group"]
        self.index = view["index"]
        self.index = max(0, min(self.index, len(self.items()) - 1))
        self.stream = args.stream or view["stream"]
        self.offset, self.cols, self.visible_rows = 0, 3, 2
        self.undo_stack: list[set[str]] = []
        self.redo_stack: list[set[str]] = []
        self.modal: Modal | None = None
        self.query, self.result_index = "", 0
        self.toast, self.toast_until, self.toast_error = "", 0.0, False
        self.last_g = False
        self.running = True
        self.saved = not store.demo
        self.browser_jobs: list[BrowserJob] = []
        self.last_browser_open = float("-inf")
        try:
            self.sync_stream_status()
        except OSError as exc:
            self.notice(f"stream.txt could not update — {exc.strerror or exc}.", True)

    def items(self) -> Sequence[Node]:
        return CHAPTERS[self.chapter]["lessons"] if self.chapter else group_chapters(self.group)

    def selected(self) -> Node:
        return self.items()[self.index]

    def selected_chapter(self) -> Chapter:
        return CHAPTERS[self.chapter] if self.chapter else group_chapters(self.group)[self.index]

    def stats(self, group: str | None = None) -> tuple[int, int]:
        keys = set(group_keys(group or self.group))
        return len(keys & self.done), len(keys)

    def notice(self, text: str, error: bool = False) -> None:
        self.toast, self.toast_error = text, error
        self.toast_until = time.monotonic() + (30 if error else 3.5)

    def stream_status(self) -> str:
        """Return the two-line chapter and lesson label shown in OBS."""
        lesson = LESSONS.get(self.focus) if self.focus is not None else None
        if lesson is None:
            lesson = next(
                (LESSONS[key] for key in group_keys("main") if key not in self.done),
                None,
            )
        if lesson is None:
            return "C++ Learning\nAll core lessons complete\n"

        chapter = LESSON_CHAPTERS[lesson["key"]]
        return f"{chapter['title']}\n{lesson['title']}\n"

    def sync_stream_status(self) -> None:
        """Atomically refresh stream.txt beside the progress state file."""
        if self.store.demo:
            return
        path = self.store.path.with_name("stream.txt")
        path.parent.mkdir(parents=True, exist_ok=True)
        self.store.atomic_write(path, self.stream_status().encode("utf-8"))

    def save(self) -> bool:
        previous = copy.deepcopy(self.store.data)
        self.store.data.update(
            completed=sorted(self.done),
            notes=dict(self.notes),
            focus=self.focus,
            name=self.name,
            view={
                "group": self.group,
                "chapter": self.chapter,
                "index": self.index,
                "stream": self.stream,
            },
        )
        try:
            self.store.save()
            self.saved = not self.store.demo
        except OSError as exc:
            self.store.data = previous
            self.saved = False
            self.notice(f"SAVE FAILED — {exc.strerror or exc}. Change was not applied.", True)
            return False
        try:
            self.sync_stream_status()
        except OSError as exc:
            self.notice(
                f"Progress saved, but stream.txt could not update — {exc.strerror or exc}.",
                True,
            )
        return True

    def change(self, new_done: set[str], message: str) -> None:
        old = set(self.done)
        if old == new_done:
            return
        self.done = new_done
        if self.save():
            self.undo_stack.append(old)
            self.undo_stack = self.undo_stack[-100:]
            self.redo_stack.clear()
            self.notice(message + (" · demo only" if self.store.demo else " · saved"))
        else:
            self.done = old

    def toggle(self) -> None:
        item = self.selected()
        if "lessons" in item:
            self.chapter, self.index, self.offset = item["id"], 0, 0
            # Land on the first not-yet-learned lesson.
            self.index = next(
                (i for i, l in enumerate(item["lessons"]) if l["key"] not in self.done), 0
            )
            return
        key = item["key"]
        new = self.done ^ {key}
        self.change(new, ("TALENT UNLOCKED  " if key in new else "Talent locked  ") + item["id"])

    def bulk(self) -> None:
        chapter = self.selected_chapter()
        self.modal = ("bulk", chapter["id"])

    def undo(self, redo: bool = False) -> None:
        source = self.redo_stack if redo else self.undo_stack
        dest = self.undo_stack if redo else self.redo_stack
        if not source:
            self.notice("Nothing to redo." if redo else "Nothing to undo.")
            return
        old, self.done = self.done, set(source[-1])
        if self.save():
            _ = source.pop()
            dest.append(old)
            self.notice("Change redone · saved" if redo else "Change undone · saved")
        else:
            self.done = old

    def back(self) -> None:
        if self.chapter:
            cid = self.chapter
            self.chapter = None
            self.index = next(i for i, c in enumerate(self.items()) if c["id"] == cid)
            self.offset = 0

    def next_chapter(self, delta: int) -> None:
        chapters = group_chapters(self.group)
        pos = (
            next(i for i, c in enumerate(chapters) if c["id"] == self.chapter)
            if self.chapter
            else self.index
        )
        pos = max(0, min(len(chapters) - 1, pos + delta))
        if self.chapter:
            self.chapter, self.index = chapters[pos]["id"], 0
        else:
            self.index = pos
        self.offset = 0

    def jump_to_quest(self) -> None:
        for chapter in CURRICULUM:
            for index, lesson in enumerate(chapter["lessons"]):
                if lesson["key"] == self.focus:
                    self.group, self.chapter = chapter["group"], chapter["id"]
                    self.index, self.offset = index, 0
                    self.modal, self.last_g = None, False
                    self.notice(f"Back to current quest · {lesson['id']}")
                    return
        message = (
            "Pinned quest is not in this outline. Pin another lesson with f."
            if self.focus
            else "No current quest pinned. Use f on a lesson first."
        )
        self.notice(message, True)

    def browser_lesson(self) -> Lesson:
        item = self.selected()
        if "key" in item:
            return item
        lessons = item["lessons"]
        return next((lesson for lesson in lessons if lesson["key"] not in self.done), lessons[0])

    def open_lesson(self, lesson: Lesson | None = None) -> None:
        # Key repeat should not flood the browser with duplicate tabs.
        now = time.monotonic()
        if now - self.last_browser_open < 0.75:
            return
        if lesson is None:
            lesson = self.browser_lesson()
        try:
            process = launch_browser(lesson.get("url", ""))
        except (OSError, ValueError) as exc:
            self.notice(f"Could not open browser: {exc}", True)
            return
        self.last_browser_open = now
        self.browser_jobs.append((process, lesson["id"]))
        self.notice(f"Opening {lesson['id']} in your default browser")

    def poll_browser(self) -> None:
        pending: list[BrowserJob] = []
        for process, lesson_id in self.browser_jobs:
            code = process.poll()
            if code is None:
                pending.append((process, lesson_id))
            elif code != 0:
                shortcut = "Ctrl-O" if self.modal and self.modal[0] == "search" else "o"
                self.notice(
                    f"Browser could not open {lesson_id}. Check your default browser; {shortcut} to retry.",
                    True,
                )
        self.browser_jobs = pending

    def results(self) -> list[tuple[int, Chapter, Lesson]]:
        query = self.query.casefold().strip()
        tokens = query.split()
        found: list[tuple[int, Chapter, Lesson]] = []
        for c in CURRICULUM:
            for l in c["lessons"]:
                hay = f"{l['id']} {l['title']} {c['title']}".casefold()
                if all(t in hay for t in tokens):
                    score = (
                        0
                        if l["id"].casefold() == query
                        else (1 if l["title"].casefold().startswith(query) else 2)
                    )
                    found.append((score, c, l))
        return sorted(found, key=lambda x: x[0])

    def note_key(self, whole_chapter: bool = False) -> str:
        item = self.selected()
        if "key" in item and not whole_chapter:
            return "lesson:" + item["key"]
        return "chapter:" + self.selected_chapter()["id"]

    def open_note(self, whole_chapter: bool = False) -> None:
        if self.stream:
            self.notice("Notes are hidden in stream view. Press s, then e to edit.")
            return
        key = self.note_key(whole_chapter)
        item = CHAPTERS[self.chapter] if whole_chapter and self.chapter else self.selected()
        title = ("LESSON " if key.startswith("lesson:") else "CHAPTER ") + item["id"]
        self.modal = ("notes", key, title, item["title"])
        self.note_buffer = self.notes.get(key, "")
        self.note_cursor, self.note_offset = len(self.note_buffer), 0

    def note_layout(self, width: int) -> list[NoteRow]:
        # Retain character offsets so wrapping never changes the saved text.
        rows: list[NoteRow] = []
        start = 0
        for line in self.note_buffer.split("\n"):
            if not line:
                rows.append((start, start, ""))
            else:
                for pos in range(0, len(line), width):
                    piece = line[pos : pos + width]
                    rows.append((start + pos, start + pos + len(piece), piece))
                if len(line) % width == 0:
                    rows.append((start + len(line), start + len(line), ""))
            start += len(line) + 1
        return rows

    def note_position(self, rows: Sequence[NoteRow]) -> tuple[int, int]:
        chosen = 0
        for i, (start, end, _) in enumerate(rows):
            if start <= self.note_cursor:
                chosen = i
            if start <= self.note_cursor < end:
                break
        return chosen, self.note_cursor - rows[chosen][0]

    def save_note(self) -> None:
        modal = self.modal
        if modal is None or modal[0] not in ("notes", "notes_confirm"):
            return
        _, note_key, title, subtitle = modal
        old = dict(self.notes)
        if self.note_buffer.strip():
            self.notes[note_key] = self.note_buffer
        else:
            _ = self.notes.pop(note_key, None)
        if self.save():
            self.modal = None
            self.notice("Note saved" + (" · demo only" if self.store.demo else ""))
        else:
            self.notes = old
            self.modal = ("notes", note_key, title, subtitle)

    def edit_note(self, key: str | int) -> None:
        modal = self.modal
        if modal is None or modal[0] != "notes":
            return
        if key == "\x13":  # Ctrl-S; terminal is in raw mode, so no flow-control freeze.
            self.save_note()
            return
        if key == "\x1b":
            if self.note_buffer != self.notes.get(modal[1], ""):
                self.modal = ("notes_confirm", modal[1], modal[2], modal[3])
            else:
                self.modal = None
                self.notice("Note editor closed.")
            return
        pos = self.note_cursor
        if key in (curses.KEY_LEFT, "\x02"):
            self.note_cursor = max(0, pos - 1)
        elif key in (curses.KEY_RIGHT, "\x06"):
            self.note_cursor = min(len(self.note_buffer), pos + 1)
        elif key in (
            curses.KEY_UP,
            curses.KEY_DOWN,
            curses.KEY_PPAGE,
            curses.KEY_NPAGE,
        ):
            rows = self.note_layout(self.note_width)
            row, col = self.note_position(rows)
            delta = (
                -1
                if key == curses.KEY_UP
                else 1
                if key == curses.KEY_DOWN
                else -8
                if key == curses.KEY_PPAGE
                else 8
            )
            target = rows[max(0, min(len(rows) - 1, row + delta))]
            self.note_cursor = min(target[1], target[0] + col)
        elif key in (curses.KEY_HOME, "\x01"):
            self.note_cursor = self.note_buffer.rfind("\n", 0, pos) + 1
        elif key in (curses.KEY_END, "\x05"):
            end = self.note_buffer.find("\n", pos)
            self.note_cursor = len(self.note_buffer) if end == -1 else end
        elif key in (curses.KEY_BACKSPACE, "\x7f", "\b"):
            if pos:
                self.note_buffer = self.note_buffer[: pos - 1] + self.note_buffer[pos:]
                self.note_cursor -= 1
        elif key == curses.KEY_DC:
            self.note_buffer = self.note_buffer[:pos] + self.note_buffer[pos + 1 :]
        elif key == "\x15":
            start = self.note_buffer.rfind("\n", 0, pos) + 1
            self.note_buffer = self.note_buffer[:start] + self.note_buffer[pos:]
            self.note_cursor = start
        else:
            inserted = (
                "\n" if key in ("\n", "\r", curses.KEY_ENTER) else "  " if key == "\t" else key
            )
            if isinstance(inserted, str) and (inserted.isprintable() or inserted == "\n"):
                if len(self.note_buffer) + len(inserted) <= 20000:
                    self.note_buffer = self.note_buffer[:pos] + inserted + self.note_buffer[pos:]
                    self.note_cursor += len(inserted)

    def handle_modal(self, key: str | int) -> None:
        modal = self.modal
        if modal is None:
            return
        if modal[0] == "notes":
            self.edit_note(key)
            return
        if modal[0] == "notes_confirm":
            if key in ("s", "S", "\x13"):
                self.save_note()
            elif key in ("d", "D"):
                self.modal = None
                self.notice("Note editor closed. Unsaved edits discarded.")
            elif key in ("c", "C", "\x1b", "\n", "\r", curses.KEY_ENTER):
                self.modal = ("notes", modal[1], modal[2], modal[3])
            return
        if key == "\x1b":
            self.modal = None
            return
        if modal[0] == "help":
            self.modal = None
        elif modal[0] == "bulk":
            cid = modal[1]
            if key in ("y", "Y", "\n", "\r", curses.KEY_ENTER):
                keys = chapter_keys(CHAPTERS[cid])
                complete = keys <= self.done
                self.change(
                    self.done - keys if complete else self.done | keys,
                    f"Chapter {cid} " + ("locked" if complete else "unlocked"),
                )
                self.modal = None
            elif key in ("n", "N", "q"):
                self.modal = None
        elif modal[0] == "search":
            matches = self.results()
            if key in (curses.KEY_DOWN, "\x0e"):
                self.result_index = min(len(matches) - 1, self.result_index + 1)
                return
            if key in (curses.KEY_UP, "\x10", "\x0b"):
                self.result_index = max(0, self.result_index - 1)
            elif key == "\x0f":
                if matches:
                    lesson = matches[max(0, min(self.result_index, len(matches) - 1))][2]
                    self.open_lesson(lesson)
            elif key == "\x06":
                self.jump_to_quest()
            elif key in ("\n", "\r", curses.KEY_ENTER):
                if matches:
                    _, c, l = matches[max(0, min(self.result_index, len(matches) - 1))]
                    self.group, self.chapter = c["group"], c["id"]
                    self.index = c["lessons"].index(l)
                    self.offset, self.modal = 0, None
            elif key in (curses.KEY_BACKSPACE, "\x7f", "\b"):
                self.query = self.query[:-1]
                self.result_index = 0
            elif key == "\x15":
                self.query, self.result_index = "", 0
            elif isinstance(key, str) and key.isprintable() and len(self.query) < 100:
                self.query += key
                self.result_index = 0

    def handle(self, key: str | int) -> None:
        if self.modal:
            self.handle_modal(key)
            return
        if key in ("q", "\x03"):
            self.running = False
        elif key in ("\n", "\r", " ", curses.KEY_ENTER):
            self.toggle()
        elif key in ("\x1b", curses.KEY_BACKSPACE, "\x7f", "\b"):
            self.back()
        elif key in ("h", curses.KEY_LEFT):
            if self.index % self.cols:
                self.index -= 1
        elif key in ("l", curses.KEY_RIGHT):
            if self.index % self.cols < self.cols - 1:
                self.index = min(len(self.items()) - 1, self.index + 1)
        elif key in ("j", curses.KEY_DOWN):
            self.index = min(len(self.items()) - 1, self.index + self.cols)
        elif key in ("k", curses.KEY_UP):
            self.index = max(0, self.index - self.cols)
        elif key in ("\x04", curses.KEY_NPAGE):
            self.index = min(
                len(self.items()) - 1,
                self.index + self.cols * max(1, self.visible_rows - 1),
            )
        elif key in ("\x15", curses.KEY_PPAGE):
            self.index = max(0, self.index - self.cols * max(1, self.visible_rows - 1))
        elif key == "g":
            if self.last_g:
                self.index, self.offset = 0, 0
                self.last_g = False
                return
            self.last_g = True
            return
        elif key in ("G", curses.KEY_END):
            self.index = len(self.items()) - 1
        elif key == curses.KEY_HOME:
            self.index, self.offset = 0, 0
        elif key in ("\t", curses.KEY_BTAB):
            step = -1 if key == curses.KEY_BTAB else 1
            self.group = GROUPS[(GROUPS.index(self.group) + step) % len(GROUPS)]
            self.chapter, self.index, self.offset = None, 0, 0
        elif key == "]":
            self.next_chapter(1)
        elif key == "[":
            self.next_chapter(-1)
        elif key == "/":
            self.modal = ("search",)
            self.query, self.result_index = "", 0
        elif key == "?":
            self.modal = ("help",)
        elif key == "b":
            self.bulk()
        elif key == "o":
            self.open_lesson()
        elif key == "F":
            self.jump_to_quest()
        elif key in ("e", "E"):
            self.open_note(whole_chapter=key == "E")
        elif key == "u":
            self.undo()
        elif key in ("r", "\x12"):
            self.undo(redo=True)
        elif key == "s":
            self.stream = not self.stream
            self.notice("Stream view on · s to return" if self.stream else "Controls restored")
        elif key == "f":
            item = self.selected()
            if "key" in item:
                old = self.focus
                self.focus = item["key"]
                if not self.save():
                    self.focus = old
                else:
                    self.notice("Current quest pinned")
            else:
                self.notice("Open a chapter first, then press f on a lesson.")
        elif key == "n":
            items = self.items()
            for step in range(1, len(items) + 1):
                idx = (self.index + step) % len(items)
                item = items[idx]
                pending = (
                    item["key"] not in self.done
                    if "key" in item
                    else not chapter_keys(item) <= self.done
                )
                if pending:
                    self.index = idx
                    break
        self.last_g = False

    def render(self, width: int, height: int) -> Canvas:
        """Produce a frame without writing to the terminal."""
        from .views import render

        return render(self, width, height)
