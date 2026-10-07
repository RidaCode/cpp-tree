"""Command-line entry point, including a read-only progress summary."""

from __future__ import annotations

import argparse
import locale
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .curriculum import GROUP_LABELS, GROUPS, LESSONS, group_keys
from .models import Options
from .paths import default_state_path


def parse_args(argv: Sequence[str] | None = None) -> Options:
    default_path = default_state_path()
    parser = argparse.ArgumentParser(
        prog="cpp-tree",
        description="An offline C++ talent tree with Vim navigation and automatic progress saving.",
    )
    _ = parser.add_argument("--name", help="name shown in the header (remembered)")
    _ = parser.add_argument(
        "--state",
        type=Path,
        default=default_path,
        help="separate progress JSON file",
    )
    _ = parser.add_argument(
        "--demo",
        action="store_true",
        help="sample progress; never read or write your real save",
    )
    _ = parser.add_argument(
        "--stream",
        action="store_true",
        help="hide controls and note contents; s brings them back",
    )
    _ = parser.add_argument(
        "--ascii",
        action="store_true",
        help="plain ASCII borders for terminals without Unicode",
    )
    _ = parser.add_argument(
        "--color",
        choices=("auto", "truecolor", "256"),
        default="auto",
        help="auto-detect exact RGB colors, force truecolor, or use the indexed fallback",
    )
    actions = parser.add_mutually_exclusive_group()
    _ = actions.add_argument("--summary", action="store_true", help="print saved progress and exit")
    _ = actions.add_argument(
        "--state-path", action="store_true", help="print the progress file path and exit"
    )
    _ = actions.add_argument(
        "--uninstall", action="store_true", help="remove this installed executable; keep progress"
    )
    _ = parser.add_argument("--version", action="version", version="cpp-tree " + __version__)
    # argparse retains attributes already present on a supplied namespace.
    # Initialize it with the actual default, never a file in the working folder.
    return parser.parse_args(argv, namespace=Options(default_path))


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.uninstall:
        from .installation import uninstall

        try:
            uninstall(Path(sys.argv[0]))
            return 0
        except (OSError, ValueError) as exc:
            print(f"cpp-tree: {exc}", file=sys.stderr)
            return 1
    if args.state_path:
        print(args.state.expanduser().absolute())
        return 0
    try:
        import curses
    except ImportError:
        print(
            "cpp-tree needs Python's curses module. Use a Python build with curses support.",
            file=sys.stderr,
        )
        return 1
    from .storage import StateError, Store, read_snapshot

    if args.summary:
        try:
            data = (
                Store(args.state, demo=True).data
                if args.demo
                else read_snapshot(args.state.expanduser())
            )
        except StateError as exc:
            print(f"cpp-tree: {exc}", file=sys.stderr)
            return 1
        print("C++ Talent Tree" + (" [DEMO — not your saved progress]" if args.demo else ""))
        completed = set(data["completed"])
        for group in GROUPS:
            keys = set(group_keys(group))
            done, total = len(keys & completed), len(keys)
            print(
                f"{GROUP_LABELS[group]:12} {done:3}/{total:<3} ({100 * done / max(1, total):.1f}%)"
            )
        focus = data["focus"]
        if focus is not None and focus in LESSONS:
            lesson = LESSONS[focus]
            print(f"Current quest: {lesson['id']} {lesson['title']}")
        return 0
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("Run cpp-tree in an interactive terminal, or use --summary.", file=sys.stderr)
        return 1
    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error:
        pass
    from .app import App
    from .terminal import terminal

    store = None
    try:
        store = Store(args.state.expanduser(), args.demo)
        app = App(store, args)
        try:
            curses.wrapper(terminal, app)
        except KeyboardInterrupt:
            pass
        if not app.save():
            print(
                "Progress changes were saved when made, but the final view could not be saved.",
                file=sys.stderr,
            )
            return 1
        print(
            "Demo closed. Your real progress was not changed."
            if args.demo
            else f"Progress saved · {app.stats('main')[0]} core talents unlocked."
        )
        return 0
    except (StateError, OSError, curses.error) as exc:
        print(f"cpp-tree: {exc}", file=sys.stderr)
        return 1
    finally:
        if store:
            store.close()
