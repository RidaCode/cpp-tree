#!/bin/sh
# One-command bootstrap. Local installs use: python3 scripts/install.py
set -eu

main() {
    command -v python3 >/dev/null 2>&1 || {
        printf '%s\n' 'cpp-tree requires Python 3.10+. Install Python, then retry.' >&2
        return 1
    }
    python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' || {
        printf '%s\n' 'cpp-tree requires Python 3.10 or newer.' >&2
        return 1
    }
    # Read, validate, and extract only the application/build files. No tar extraction
    # to arbitrary paths, symlinks, privileged writes, or changes to shell profiles.
    python3 - "$@" <<'PY'
import io
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile
import tempfile
from urllib.parse import quote
from urllib.request import urlopen

repo = os.environ.get("CPP_TREE_REPO", "RidaCode/cpp-tree")
ref = os.environ.get("CPP_TREE_REF", "main")
limit = 10 * 1024 * 1024

def bootstrap():
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo) or not ref:
        raise ValueError("Invalid CPP_TREE_REPO or CPP_TREE_REF.")
    # A supplied archive makes the same bootstrap testable without network access.
    local = os.environ.get("CPP_TREE_ARCHIVE")
    if local:
        with open(local, "rb") as response:
            payload = response.read(limit + 1)
    else:
        url = "https://codeload.github.com/" + repo + "/tar.gz/" + quote(ref, safe="")
        print("Downloading " + repo + " (" + ref + ")...", flush=True)
        with urlopen(url, timeout=30) as response:
            payload = response.read(limit + 1)
    if len(payload) > limit:
        raise ValueError("Source archive exceeds 10 MiB.")
    with tempfile.TemporaryDirectory(prefix="cpp-tree-source-") as work:
        root = Path(work)
        seen = set()
        total = 0
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
            for member in archive:
                name = PurePosixPath(member.name)
                if name.is_absolute() or ".." in name.parts:
                    raise ValueError("Unsafe source archive path.")
                if member.isdir():
                    continue
                if not member.isfile():
                    raise ValueError("Source archive contains a link or special file.")
                if len(name.parts) < 2:
                    continue
                relative = PurePosixPath(*name.parts[1:])
                selected = (
                    relative.parts[0] == "cpp_tree" and relative.suffix in (".py", ".json")
                    or str(relative) in ("scripts/build.py", "scripts/install.py", "LICENSE", "NOTICE.md")
                )
                if not selected:
                    continue
                total += member.size
                if relative in seen or total > limit:
                    raise ValueError("Duplicate files or oversized source contents.")
                seen.add(relative)
                destination = root.joinpath(*relative.parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                stream = archive.extractfile(member)
                if stream is None:
                    raise ValueError("Could not read source file.")
                with stream:
                    destination.write_bytes(stream.read())
        result = subprocess.run([sys.executable, str(root / "scripts/install.py"), *sys.argv[1:]])
        return result.returncode

try:
    raise SystemExit(bootstrap())
except (OSError, ValueError, tarfile.TarError) as exc:
    print("cpp-tree install failed: " + str(exc), file=sys.stderr)
    raise SystemExit(1)
PY
}
# Defining the entire function before invocation avoids running a truncated download.
main "$@"
