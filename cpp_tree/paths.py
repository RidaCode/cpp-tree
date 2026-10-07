"""The legacy state location is retained so existing profiles keep working."""

import os
from pathlib import Path


def default_state_path() -> Path:
    configured = os.environ.get("XDG_STATE_HOME", "")
    root = Path(configured) if configured else Path.home() / ".local" / "state"
    # XDG paths must be absolute; a relative value must not scatter saves by cwd.
    if not root.is_absolute():
        root = Path.home() / ".local" / "state"
    return root / "cpp-tree" / "progress.json"
