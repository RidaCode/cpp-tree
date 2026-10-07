#!/usr/bin/env python3
"""Install from a source checkout without pip, sudo, or runtime dependencies."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bin-dir",
        type=Path,
        default=Path(os.environ.get("CPP_TREE_BIN_DIR") or Path.home() / ".local" / "bin"),
    )
    args = parser.parse_args()
    if sys.version_info < (3, 10) or sys.platform == "win32":
        parser.error("Python 3.10+ on Linux/macOS (or Linux inside WSL) is required.")
    try:
        import curses  # noqa: F401
        import fcntl  # noqa: F401
    except ImportError:
        parser.error("This Python build must include curses and fcntl.")
    from build import build_archive

    from cpp_tree.installation import install_archive

    destination = args.bin_dir.expanduser().absolute() / "cpp-tree"
    try:
        with tempfile.TemporaryDirectory(prefix="cpp-tree-") as work:
            archive = build_archive(Path(work) / "cpp-tree.pyz")
            # Catch missing resources and packaging mistakes before replacing an install.
            subprocess.run(
                [sys.executable, str(archive), "--demo", "--summary"],
                check=True,
                stdout=subprocess.DEVNULL,
            )
            install_archive(archive, destination)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Install failed: {exc}", file=sys.stderr)
        return 1
    print(f"Installed {destination}")
    print("Run: cpp-tree")
    print("Uninstall: cpp-tree --uninstall (keeps progress and notes)")
    if str(destination.parent) not in os.environ.get("PATH", "").split(os.pathsep):
        print(f"Add {destination.parent} to your PATH, or run the executable by its full path.")
        print('For the default location in bash/zsh: export PATH="$HOME/.local/bin:$PATH"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
