"""Sanitize and wrap display text without changing stored notes."""

import textwrap


def clean(s: object) -> str:
    return "".join(ch if ch.isprintable() else " " for ch in str(s))


def clip(s: object, width: int) -> str:
    s = clean(s)
    return s if len(s) <= width else s[: max(0, width - 1)] + ("…" if width else "")


def wrapped(s: object, width: int, limit: int | None = None) -> list[str]:
    lines = textwrap.wrap(clean(s), max(1, width), break_long_words=True) or [""]
    if limit is not None and len(lines) > limit:
        lines = lines[:limit]
        lines[-1] = clip(lines[-1], width - 1) + "…"
    return lines
