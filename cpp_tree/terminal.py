"""Curses input and RGB/indexed-color display backends."""

from __future__ import annotations

import curses
import os
import sys

from .app import App
from .canvas import Canvas
from .theme import PALETTE


def nearest_color(hex_color: str, count: int) -> int:
    rgb = tuple(int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    if count < 256:
        ansi = [
            (0, 0, 0),
            (180, 40, 40),
            (50, 180, 100),
            (200, 170, 70),
            (90, 130, 230),
            (180, 90, 190),
            (70, 180, 190),
            (220, 225, 235),
        ]
        return min(
            range(min(count, len(ansi))),
            key=lambda i: sum((rgb[j] - ansi[i][j]) ** 2 for j in range(3)),
        )
    levels = (0, 95, 135, 175, 215, 255)
    rr, gg, bb = [min(range(6), key=lambda i: abs(levels[i] - v)) for v in rgb]
    cube = 16 + 36 * rr + 6 * gg + bb
    gray_idx = max(0, min(23, round((sum(rgb) / 3 - 8) / 10)))
    gray = 8 + 10 * gray_idx
    cube_dist = sum((rgb[i] - levels[n]) ** 2 for i, n in enumerate((rr, gg, bb)))
    gray_dist = sum((v - gray) ** 2 for v in rgb)
    return 232 + gray_idx if gray_dist < cube_dist else cube


def use_truecolor(mode: str = "auto") -> bool:
    if mode != "auto":
        return mode == "truecolor"
    term = os.environ.get("TERM", "").lower()
    if term in ("dumb", "linux"):
        return False
    return (
        os.environ.get("COLORTERM", "").lower() in ("truecolor", "24bit")
        or bool(os.environ.get("KONSOLE_VERSION"))
        or "direct" in term
        or getattr(curses, "COLORS", 0) >= 16777216
        or curses.tigetflag("RGB") == 1
        or curses.tigetflag("Tc") == 1
    )


def rgb_style(style: str) -> str:
    fg, bg, bold = PALETTE[style]
    foreground = ";".join(str(int(fg[i : i + 2], 16)) for i in (1, 3, 5))
    background = ";".join(str(int(bg[i : i + 2], 16)) for i in (1, 3, 5))
    return f"\x1b[0;{1 if bold else 22};38;2;{foreground};48;2;{background}m"


RGB_STYLES = {name: rgb_style(name) for name in PALETTE}


def truecolor_frame(frame: Canvas, previous: Canvas | None = None) -> str:
    """Draw exact RGB cells; do not round dark blues to indexed grays.

    Curses still handles key decoding, raw mode, resize and terminal restoration.
    We keep its window untouched so get_wch cannot repaint over these cells.
    """
    parts: list[str] = []
    for y, row in enumerate(frame.cells):
        if previous and (previous.w, previous.h) == (frame.w, frame.h) and previous.cells[y] == row:
            continue
        parts.append(f"\x1b[{y + 1};1H")
        x = 0
        while x < frame.w:
            style = row[x][1]
            end = x + 1
            while end < frame.w and row[end][1] == style:
                end += 1
            parts.append(RGB_STYLES[style])
            parts.append("".join(ch for ch, _ in row[x:end]))
            x = end
    if not parts:
        return ""
    # Temporarily disable wrapping so painting the bottom-right cell cannot scroll.
    return "\x1b[?7l" + "".join(parts) + "\x1b[0m\x1b[H\x1b[?7h"


def terminal(stdscr: curses.window, app: App) -> None:
    try:
        _ = curses.curs_set(0)
    except curses.error:
        pass
    if hasattr(curses, "set_escdelay"):
        curses.set_escdelay(30)
    stdscr.keypad(True)
    curses.raw()
    stdscr.timeout(120)
    styles: dict[str, int] = {}
    if curses.has_colors():
        curses.start_color()
        for i, (name, (fg, bg, bold)) in enumerate(PALETTE.items(), 1):
            if i < curses.COLOR_PAIRS:
                curses.init_pair(
                    i,
                    nearest_color(fg, curses.COLORS),
                    nearest_color(bg, curses.COLORS),
                )
                styles[name] = curses.color_pair(i) | (curses.A_BOLD if bold else 0)
            else:
                styles[name] = curses.A_BOLD if bold else 0
    else:
        styles = {name: curses.A_BOLD if bold else 0 for name, (_, _, bold) in PALETTE.items()}
    exact_rgb = use_truecolor(app.args.color)
    if exact_rgb:
        stdscr.leaveok(True)
        stdscr.refresh()
    else:
        stdscr.bkgd(" ", styles.get("base", 0))
    previous = None
    while app.running:
        app.poll_browser()
        height, width = stdscr.getmaxyx()
        frame = app.render(width, height)
        if previous is None or (previous.w, previous.h) != (width, height):
            if not exact_rgb:
                stdscr.erase()
            previous = None
        if exact_rgb:
            output = truecolor_frame(frame, previous)
            if output:
                _ = sys.stdout.write(output)
                _ = sys.stdout.flush()
            stdscr.untouchwin()
            stdscr.clearok(False)
        else:
            for y, row in enumerate(frame.cells):
                if previous and previous.cells[y] == row:
                    continue
                x = 0
                while x < width:
                    style = row[x][1]
                    end = x + 1
                    while end < width and row[end][1] == style:
                        end += 1
                    try:
                        stdscr.addstr(
                            y,
                            x,
                            "".join(ch for ch, _ in row[x:end]),
                            styles.get(style, 0),
                        )
                    except curses.error:
                        # A concurrent resize or the terminal's bottom-right cell.
                        pass
                    x = end
            stdscr.noutrefresh()
            curses.doupdate()
        previous = frame
        try:
            key = stdscr.get_wch()
        except curses.error:
            continue
        if key == curses.KEY_RESIZE:
            previous = None
            continue
        if width < 72 or height < 22:
            if key in ("q", "\x03"):
                app.running = False
            continue
        app.handle(key)
