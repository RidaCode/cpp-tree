"""A terminal-independent grid of characters and named styles."""

from __future__ import annotations

from typing import final

from .text import clean, clip
from .theme import ASCII_MAP


@final
class Canvas:
    def __init__(self, width: int, height: int, ascii_mode: bool = False) -> None:
        self.w, self.h, self.ascii = width, height, ascii_mode
        self.cells = [[(" ", "base") for _ in range(width)] for _ in range(height)]

    def text(
        self, x: int, y: int, value: object, style: str = "base", width: int | None = None
    ) -> None:
        if y < 0 or y >= self.h:
            return
        value = clean(value)
        if width is not None:
            value = clip(value, width)
        if self.ascii:
            value = value.translate(ASCII_MAP).encode("ascii", "replace").decode("ascii")
        for i, ch in enumerate(value):
            if 0 <= x + i < self.w:
                self.cells[y][x + i] = (ch, style)

    def fill(self, x: int, y: int, width: int, height: int, style: str = "panel") -> None:
        for yy in range(max(0, y), min(self.h, y + height)):
            self.text(x, yy, " " * max(0, width), style)

    def hline(self, x1: int, x2: int, y: int, style: str = "faint", char: str = "─") -> None:
        self.text(x1, y, char * max(0, x2 - x1 + 1), style)

    def vline(self, x: int, y1: int, y2: int, style: str = "faint") -> None:
        for yy in range(y1, y2 + 1):
            self.text(x, yy, "│", style)

    def box(
        self, x: int, y: int, width: int, height: int, style: str = "faint", fill: str | None = None
    ) -> None:
        if fill:
            self.fill(x, y, width, height, fill)
        self.text(x, y, "╭" + "─" * (width - 2) + "╮", style)
        self.text(x, y + height - 1, "╰" + "─" * (width - 2) + "╯", style)
        for yy in range(y + 1, y + height - 1):
            self.text(x, yy, "│", style)
            self.text(x + width - 1, yy, "│", style)

    def center(self, x: int, y: int, width: int, value: object, style: str = "base") -> None:
        value = clip(value, width)
        self.text(x + max(0, (width - len(value)) // 2), y, value, style)

    def blit(self, source: Canvas, x: int, y: int, top: int = 0, height: int | None = None) -> None:
        for yy in range(height if height is not None else source.h):
            sy, dy = top + yy, y + yy
            if 0 <= sy < source.h and 0 <= dy < self.h:
                for xx in range(source.w):
                    if 0 <= x + xx < self.w:
                        self.cells[dy][x + xx] = source.cells[sy][xx]
