"""Keep environment checks readable even on an unsupported Python version."""

import sys


def main():
    if sys.version_info < (3, 10):
        print("cpp-tree requires Python 3.10 or newer.", file=sys.stderr)
        return 1
    if sys.platform == "win32":
        print("Use cpp-tree inside WSL. Native Windows is not supported.", file=sys.stderr)
        return 1
    from .cli import main as run

    return run()


if __name__ == "__main__":
    raise SystemExit(main())
