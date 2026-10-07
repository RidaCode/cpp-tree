#!/usr/bin/env python3
"""Build a reproducible, dependency-free executable Python archive."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cpp_tree.installation import MARKER, MARKER_NAME  # noqa: E402


def build_archive(destination: Path) -> Path:
    from cpp_tree.curriculum import CURRICULUM

    if not CURRICULUM:
        raise ValueError("The curriculum is empty.")
    destination = destination.absolute()
    destination.parent.mkdir(parents=True, exist_ok=True)
    entries = {
        path.relative_to(ROOT).as_posix(): path.read_bytes()
        for path in sorted((ROOT / "cpp_tree").rglob("*"))
        if path.is_file() and path.suffix in (".py", ".json") and "__pycache__" not in path.parts
    }
    entries["__main__.py"] = b"from cpp_tree.__main__ import main\nraise SystemExit(main())\n"
    entries[MARKER_NAME] = json.dumps(MARKER, sort_keys=True).encode()
    for filename in ("LICENSE", "NOTICE.md"):
        entries[filename] = (ROOT / filename).read_bytes()
    fd, temporary = tempfile.mkstemp(prefix=".cpp-tree-build-", dir=destination.parent)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(b"#!/usr/bin/env python3\n")
            with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for name, data in sorted(entries.items()):
                    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.create_system = 3
                    info.external_attr = 0o100644 << 16
                    archive.writestr(info, data)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, 0o755)
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "cpp-tree.pyz")
    args = parser.parse_args()
    print(build_archive(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
