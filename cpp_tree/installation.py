"""Recognize and remove one managed executable, never user state or directories."""

from __future__ import annotations

import json
import os
import zipfile
from pathlib import Path

MARKER_NAME = "cpp-tree-install.json"
MARKER = {"application": "cpp-tree", "format": 1}


def is_managed(path: Path) -> bool:
    if path.is_symlink() or not path.is_file():
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            return json.loads(archive.read(MARKER_NAME)) == MARKER
    except (OSError, ValueError, KeyError, zipfile.BadZipFile):
        return False


def uninstall(path: Path) -> None:
    # absolute() deliberately preserves symlinks; resolve() could delete their targets.
    path = path.absolute()
    if not is_managed(path):
        raise ValueError(
            "This is not an installer-managed cpp-tree executable. "
            "For pip/pipx installs, uninstall with the same package manager; "
            "for a source checkout, delete the checkout."
        )
    path.unlink()
    print(f"Removed {path}")
    print("Your progress, notes, backups, and stream.txt were kept.")


def install_archive(source: Path, destination: Path) -> None:
    """Publish a verified archive atomically; refuse unrelated files and symlinks."""
    import tempfile

    if not is_managed(source):
        raise ValueError("The build is not a valid cpp-tree archive.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if os.path.lexists(destination) and not is_managed(destination):
        raise ValueError(
            f"Refusing to overwrite {destination}: it is not managed by this installer. "
            "Rename the existing file, or choose another --bin-dir."
        )
    fd, temporary = tempfile.mkstemp(prefix=".cpp-tree-install-", dir=destination.parent)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(source.read_bytes())
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, 0o755)
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
