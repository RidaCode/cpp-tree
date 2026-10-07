"""Render the tree and dialogs to a Canvas; never perform file or terminal I/O."""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING

from .canvas import Canvas
from .curriculum import (
    CHAPTERS,
    GROUP_LABELS,
    GROUPS,
    LESSONS,
    SHORT,
    chapter_keys,
    group_chapters,
    group_keys,
)
from .models import Node
from .text import wrapped

if TYPE_CHECKING:
    from .app import App


def bar(
    app: App,
    canvas: Canvas,
    x: int,
    y: int,
    width: int,
    count: int,
    total: int,
    style: str = "green",
) -> None:
    full = round(width * count / max(1, total))
    canvas.text(x, y, "━" * full, style)
    canvas.text(x + full, y, "─" * (width - full), "faint")


def draw_node(app: App, cv: Canvas, item: Node, x: int, y: int, width: int, selected: bool) -> None:
    if "key" in item:
        count, total = int(item["key"] in app.done), 1
        title, ident = item["title"], item["id"]
        pinned = item["key"] == app.focus
    else:
        keys = chapter_keys(item)
        count, total = len(keys & app.done), len(keys)
        title, ident = SHORT.get(item["id"], item["title"]), "CH " + item["id"]
        pinned = app.focus in keys
    complete, partial = count == total, 0 < count < total
    bg = "sel" if selected else "panel"
    edge = (
        "sel_gold"
        if selected
        else ("panel_green" if complete else "panel_blue" if partial else "panel_muted")
    )
    ink = "sel" if selected else "panel"
    accent = (
        "sel_green"
        if selected and complete
        else "panel_green"
        if complete
        else "sel_gold"
        if selected
        else "panel_blue"
        if partial
        else "panel_muted"
    )
    cv.box(x, y, width, 6, edge, bg)
    gem = "◆" if complete else "◈" if partial else "◇"
    cv.text(x + 2, y, f" {gem} {ident} ", edge)
    if selected:
        cv.text(x + width - 5, y, " <> ", edge)
    note_key = "lesson:" + item["key"] if "key" in item else "chapter:" + item["id"]
    if app.notes.get(note_key):
        cv.text(x + width - 8, y + 3, "[note]", accent)
    if pinned:
        cv.text(x + 2, y + 3, "* QUEST", accent)
    # Cards stay spacious; full, unabridged titles are in the detail area.
    for row, line in enumerate(wrapped(title, width - 4, 2)):
        cv.text(x + 2, y + 1 + row, line, ink)
    label = "UNLOCKED" if complete else "IN PROGRESS" if partial else "LOCKED"
    if app.chapter and re.search(r"\.[xXy]$", item["id"]):
        label = "QUIZ CLEARED" if complete else "CHECKPOINT"
    cv.text(x + 2, y + 4, gem + " " + label, accent, width - 9)
    rank = f"{count}/{total}"
    cv.text(x + width - len(rank) - 2, y + 4, rank, accent)


def tree(app: App, cv: Canvas, x: int, y: int, width: int, height: int) -> None:
    app.cols = 3 if width >= 86 else 2 if width >= 56 else 1
    gap = 4
    card_w = min(36, (width - gap * (app.cols - 1) - 2) // app.cols)
    group_w = app.cols * card_w + (app.cols - 1) * gap
    left = (width - group_w) // 2
    rows = (len(app.items()) + app.cols - 1) // app.cols
    total_h = rows * 9 + 1
    tc = Canvas(width, total_h, app.args.ascii)
    centers = [left + col * (card_w + gap) + card_w // 2 for col in range(app.cols)]
    for row in range(rows):
        start = row * app.cols
        amount = min(app.cols, len(app.items()) - start)
        yy = row * 9 + 3
        # Symmetric branch wiring: visual map, never enforced prerequisites.
        hub_y = yy - 2
        active = any(
            (i["key"] in app.done if "key" in i else bool(chapter_keys(i) & app.done))
            for i in app.items()[start : start + amount]
        )
        color = "green" if active else "faint"
        tc.hline(centers[0], centers[amount - 1], hub_y, color)
        for col in range(amount):
            xx = centers[col]
            tc.text(xx, hub_y, "┬", color)
            tc.vline(xx, hub_y + 1, yy - 1, color)
            if row:
                tc.vline(xx, hub_y - 1, hub_y - 1, color)
                tc.text(xx, hub_y, "┼", color)
        if row == 0:
            mid = (centers[0] + centers[amount - 1]) // 2
            tc.text(mid, 0, "◆", "gold")
            tc.text(mid, hub_y, "┴" if amount > 1 else "│", color)
        for col in range(amount):
            i = start + col
            draw_node(
                app,
                tc,
                app.items()[i],
                left + col * (card_w + gap),
                yy,
                card_w,
                i == app.index,
            )
    target_y = (app.index // app.cols) * 9 + 3
    if target_y < app.offset:
        app.offset = max(0, target_y - 3)
    if target_y + 6 > app.offset + height:
        app.offset = target_y + 6 - height
    app.offset = max(0, min(app.offset, max(0, total_h - height)))
    cv.blit(tc, x, y, app.offset, height)
    app.visible_rows = max(1, height // 9)
    if app.offset:
        cv.text(x + width - 2, y, "↑", "gold")
    if app.offset + height < total_h:
        cv.text(x + width - 2, y + height - 1, "↓", "gold")


def detail(app: App, cv: Canvas, x: int, y: int, width: int, height: int) -> None:
    cv.fill(x, y, width, height, "panel")
    item = app.selected()
    label = "SELECTED TALENT" if app.chapter else "SELECTED CHAPTER"
    cv.text(x + 2, y + 1, label, "panel_muted")
    ident = item["id"] if app.chapter else "CHAPTER " + item["id"]
    cv.text(x + 2, y + 3, ident, "panel_gold")
    lines = wrapped(item["title"], width - 4)
    for row, line in enumerate(lines):
        cv.text(x + 2, y + 5 + row, line, "panel")
    yy = y + 6 + len(lines)
    if "key" in item:
        learned = item["key"] in app.done
        status = "◆ UNLOCKED" if learned else "◇ LOCKED"
        cv.text(x + 2, yy, status, "panel_green" if learned else "panel_muted")
        yy += 2
        if not app.stream:
            cv.text(
                x + 2,
                yy,
                "Enter to " + ("lock" if learned else "unlock"),
                "panel_gold",
            )
        outline_note = item.get("note")
        if outline_note:
            cv.text(x + 2, yy + 1, "Outline: " + outline_note, "panel_muted", width - 4)
        if not app.stream:
            cv.text(x + 2, yy + 2, "o  open lesson in browser", "panel_blue", width - 4)
    else:
        keys = chapter_keys(item)
        cv.text(
            x + 2,
            yy,
            f"{len(keys & app.done)} / {len(keys)} talents unlocked",
            "panel_green",
        )
        yy += 2
        if not app.stream:
            cv.text(x + 2, yy, "Enter to open this tree", "panel_gold")
            cv.text(x + 2, yy + 2, "o  continue in browser", "panel_blue", width - 4)
    yy += 4
    note = app.notes.get(app.note_key(), "")
    if note and yy + 7 < y + height:
        cv.text(
            x + 2,
            yy,
            "NOTE ATTACHED" + (" · e to edit" if not app.stream else ""),
            "panel_gold",
            width - 4,
        )
        if not app.stream:
            for row, line in enumerate(wrapped(note, width - 4, 2)):
                cv.text(x + 2, yy + 1 + row, line, "panel_muted")
            yy += 4
        else:
            yy += 2
    # Show the selected chapter's next target, so the audience sees what is ahead.
    c = app.selected_chapter()
    pending = next((l for l in c["lessons"] if l["key"] not in app.done), None)
    if yy + 5 < y + height:
        cv.text(x + 2, yy, "NEXT IN THIS CHAPTER", "panel_muted")
        if pending:
            cv.text(x + 2, yy + 2, pending["id"], "panel_blue")
            for row, line in enumerate(wrapped(pending["title"], width - 4, 3)):
                cv.text(x + 2, yy + 3 + row, line, "panel")
        else:
            cv.text(x + 2, yy + 2, "◆ CHAPTER MASTERED", "panel_green")
    if not app.stream and height > 26:
        cv.text(
            x + 2,
            y + height - 3,
            "b  unlock whole chapter",
            "panel_muted",
            width - 4,
        )
        cv.text(
            x + 2,
            y + height - 2,
            "f pin quest · F return",
            "panel_muted",
            width - 4,
        )


def draw_modal(app: App, cv: Canvas) -> None:
    modal = app.modal
    if modal is None:
        return
    width = min(cv.w - 6, 82)
    x = (cv.w - width) // 2
    if modal[0] == "notes":
        height = min(cv.h - 2, 32)
        y = (cv.h - height) // 2
        cv.box(x, y, width, height, "panel_gold", "panel")
        dirty = app.note_buffer != app.notes.get(modal[1], "")
        cv.text(
            x + 3,
            y + 1,
            modal[2] + " NOTES" + ("  · unsaved" if dirty else ""),
            "panel_gold",
        )
        cv.text(x + 3, y + 3, modal[3], "panel_muted", width - 6)
        app.note_width = width - 6
        rows = app.note_layout(app.note_width)
        row, col = app.note_position(rows)
        slots = height - 9
        if row < app.note_offset:
            app.note_offset = row
        if row >= app.note_offset + slots:
            app.note_offset = row - slots + 1
        for i, (_, _, line) in enumerate(rows[app.note_offset : app.note_offset + slots]):
            cv.text(x + 3, y + 5 + i, line, "panel", width - 6)
        cursor_y = y + 5 + row - app.note_offset
        char = app.note_buffer[app.note_cursor : app.note_cursor + 1]
        cv.text(
            x + 3 + min(col, app.note_width - 1),
            cursor_y,
            " " if char in ("", "\n") else char,
            "sel_gold",
        )
        cv.text(
            x + 3,
            y + height - 3,
            "Ctrl-S save    Esc cancel    Enter newline    Arrows move",
            "panel_gold",
            width - 6,
        )
        cv.text(
            x + 3,
            y + height - 2,
            f"{len(app.note_buffer):,} / 20,000 characters · Notes are hidden in stream view",
            "panel_muted",
            width - 6,
        )
        if (
            app.toast_error
            and app.toast.startswith("SAVE FAILED")
            and time.monotonic() < app.toast_until
        ):
            cv.text(
                x + 3,
                y + height - 2,
                "Save failed. Text kept in editor. Check available disk space.",
                "panel_gold",
                width - 6,
            )
    elif modal[0] == "search":
        height = min(cv.h - 4, 24)
        y = (cv.h - height) // 2
        cv.box(x, y, width, height, "panel_gold", "panel")
        cv.text(x + 2, y + 1, "FIND A TALENT", "panel_gold")
        cv.text(
            x + 2,
            y + 3,
            "/ " + app.query[-(width - 7) :] + "_",
            "panel",
            width - 4,
        )
        matches = app.results()
        app.result_index = max(0, min(app.result_index, len(matches) - 1))
        slots = height - 8
        top = max(0, app.result_index - slots + 1)
        for row, (_, c, l) in enumerate(matches[top : top + slots]):
            selected = top + row == app.result_index
            learned = l["key"] in app.done
            sty = (
                ("sel_green" if selected else "panel_green")
                if learned
                else ("sel" if selected else "panel")
            )
            cv.fill(x + 1, y + 5 + row, width - 2, 1, sty)
            status = "◆" if learned else "◇"
            text = f"{status} {l['id']:5} {l['title']}"
            if c["group"] != "main":
                text = f"[{'D' if c['group'] == 'archive' else 'SIDE'}] " + text
            cv.text(x + 2, y + 5 + row, text, sty, width - 4)
        if not matches:
            cv.text(
                x + 2,
                y + 6,
                "No matches. Try a lesson ID or a shorter phrase.",
                "panel_muted",
                width - 4,
            )
        status_text = f"{len(matches)} results · ↑↓ / Ctrl-N/P · Enter jump"
        status_style = "panel_muted"
        if time.monotonic() < app.toast_until and app.toast.startswith(
            (
                "Opening ",
                "Browser could not open ",
                "Could not open browser:",
                "No current quest",
                "Pinned quest",
            )
        ):
            status_text = app.toast
            status_style = "panel_gold" if app.toast_error else "panel_green"
        cv.text(x + 2, y + height - 3, status_text, status_style, width - 4)
        cv.text(
            x + 2,
            y + height - 2,
            "Ctrl-O browser · Ctrl-F quest · Esc cancel",
            "panel_gold",
            width - 4,
        )
    elif modal[0] == "bulk":
        c = CHAPTERS[modal[1]]
        locked = chapter_keys(c) <= app.done
        height, y = 13, (cv.h - 13) // 2
        cv.box(x, y, width, height, "panel_gold", "panel")
        cv.text(
            x + 3,
            y + 2,
            ("LOCK" if locked else "UNLOCK") + " WHOLE CHAPTER?",
            "panel_gold",
        )
        cv.text(
            x + 3,
            y + 4,
            f"Chapter {c['id']} · {SHORT.get(c['id'], c['title'])}",
            "panel",
            width - 6,
        )
        count = len(chapter_keys(c) if locked else chapter_keys(c) - app.done)
        cv.text(
            x + 3,
            y + 6,
            f"This changes {count} lessons. You can undo with u.",
            "panel",
            width - 6,
        )
        cv.text(x + 3, y + 9, "Enter / y  confirm     Esc / n  cancel", "panel_gold")
    else:
        lines = [
            ("h j k l / arrows", "Move between talent nodes"),
            ("Enter / Space", "Open chapter; unlock / lock lesson"),
            ("o", "Open lesson in your browser"),
            ("Esc / Backspace", "Return to chapter map"),
            ("gg/G · Ctrl-D/U", "First/last · page down/up"),
            ("[ / ]", "Previous / next chapter"),
            ("Tab / Shift-Tab", "Main tree / side quests / archive"),
            ("/", "Search all lessons by title or ID"),
            ("n", "Jump to next locked talent"),
            ("f / F", "Pin quest / return to current quest"),
            ("e / E", "Lesson notes / chapter notes"),
            ("b", "Unlock / lock chapter (confirmation)"),
            ("u / r", "Undo / redo a progress change"),
            ("s", "Toggle stream view"),
            ("q", "Save view and quit"),
        ]
        height = min(cv.h - 2, 24)
        y = (cv.h - height) // 2
        cv.box(x, y, width, height, "panel_gold", "panel")
        cv.text(x + 3, y + 1, "YOUR KEYBINDS", "panel_gold")
        for i, (key, action) in enumerate(lines):
            cv.text(x + 3, y + 3 + i, key, "panel_gold", 21)
            cv.text(x + 25, y + 3 + i, action, "panel", width - 28)
        if height >= 23:
            cv.text(
                x + 3,
                y + height - 4,
                "Progress autosaves. Connections do not enforce prerequisites.",
                "panel_muted",
                width - 6,
            )
        cv.text(x + 3, y + height - 2, "Press any key to return", "panel_muted")


def render(app: App, width: int, height: int) -> Canvas:
    cv = Canvas(width, height, app.args.ascii)
    if width < 72 or height < 22:
        cv.text(2, 2, "C++ TALENT TREE", "gold", max(0, width - 4))
        cv.text(
            2,
            4,
            "Resize to at least 72 columns x 22 rows.",
            width=max(0, width - 4),
        )
        cv.text(2, 6, "Progress is safe. q to exit.", "muted", max(0, width - 4))
        return cv
    total_done, total = app.stats("main")
    mastered = sum(chapter_keys(c) <= app.done for c in group_chapters("main"))
    cv.text(2, 1, "◈  C++ TALENT TREE", "gold")
    right = (
        "DEMO · NOT SAVED"
        if app.store.demo
        else ("STREAM VIEW" if app.stream else app.name.upper())
    )
    cv.text(width - len(right) - 3, 1, right, "purple" if app.store.demo else "muted")
    cv.text(2, 3, f"{total_done:3} / {total}  CORE TALENTS", "green")
    cv.text(29, 3, f"{mastered:2} / {len(group_chapters('main'))}  CHAPTERS", "gold")
    percent = 100 * total_done / max(1, total)
    cv.text(width - 10, 3, f"{percent:5.1f}%", "white")
    bar(app, cv, 2, 4, width - 5, total_done, total)
    cv.hline(1, width - 2, 6)
    if app.chapter:
        c = CHAPTERS[app.chapter]
        breadcrumb = f"{GROUP_LABELS[app.group]}  /  CH {app.chapter}  /  {SHORT.get(app.chapter, c['title'])}"
        count = len(chapter_keys(c) & app.done)
        counter = f"{count}/{len(c['lessons'])} learned"
    else:
        breadcrumb = "   ".join(
            ("[ " + GROUP_LABELS[g] + " ]") if g == app.group else GROUP_LABELS[g] for g in GROUPS
        )
        count, group_total = app.stats()
        counter = f"{count}/{group_total} learned"
    cv.text(2, 6, " " + breadcrumb + " ", "gold", width - len(counter) - 8)
    cv.text(width - len(counter) - 3, 6, counter, "green")
    tree_h = height - 14
    sidebar = width >= 118
    side_w = 31 if width < 144 else 35
    main_w = width - side_w - 5 if sidebar else width - 3
    tree(app, cv, 1, 7, main_w, tree_h)
    if sidebar:
        detail(app, cv, width - side_w - 2, 8, side_w, tree_h - 1)
    yy = height - 7
    cv.hline(1, width - 2, yy)
    item = app.selected()
    full = f"{item['id']}  {item['title']}"
    lines = wrapped(full, width - 5, 2)
    for row, line in enumerate(lines):
        cv.text(2, yy + 1 + row, line, "white" if row == 0 else "base")
    quest = LESSONS.get(app.focus) if app.focus is not None else None
    if quest:
        prefix = "QUEST COMPLETE  " if quest["key"] in app.done else "CURRENT QUEST  "
        quest_line = prefix + quest["id"] + " · " + quest["title"]
    else:
        next_lesson = next((LESSONS[k] for k in group_keys("main") if k not in app.done), None)
        quest_line = (
            "UP NEXT  " + next_lesson["id"] + " · " + next_lesson["title"]
            if next_lesson
            else "ALL CORE TALENTS UNLOCKED"
        )
    cv.text(2, height - 4, quest_line, "blue", width - 5)
    if app.toast and time.monotonic() < app.toast_until:
        cv.text(
            2,
            height - 3,
            app.toast,
            "danger" if app.toast_error else "green",
            width - 5,
        )
    else:
        cv.text(
            2,
            height - 3,
            "◆ learned   ◈ in progress   ◇ ahead     * current quest",
            "muted",
            width - 20,
        )
        cv.text(
            width - 15,
            height - 3,
            "demo" if app.store.demo else "autosaved" if app.saved else "save failed",
            "muted" if app.saved or app.store.demo else "danger",
        )
    if not app.stream:
        action = (" unlock/lock" if app.chapter else " open") if width >= 100 else ""
        help_line = (
            "hjkl · Enter"
            + action
            + " · F quest · o browser · e notes · / search · ? help · q quit"
            if width >= 100
            else "hjkl · Enter · F quest · o web · e notes · / find · ? · q quit"
        )
        cv.text(2, height - 1, help_line, "muted", width - 4)
    else:
        cv.center(0, height - 1, width, "LEARN  ·  PRACTICE  ·  UNLOCK", "gold")
    if app.modal:
        draw_modal(app, cv)
    return cv
