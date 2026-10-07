"""Open only LearnCpp article URLs, without blocking the terminal."""

from __future__ import annotations

import shutil
import subprocess
import sys
from urllib.parse import urlsplit


def launch_browser(url: str) -> subprocess.Popen[bytes]:
    """Hand a verified lesson URL to the desktop without taking over the TUI."""
    target = urlsplit(url)
    if (
        target.scheme != "https"
        or target.netloc != "www.learncpp.com"
        or not target.path.startswith("/cpp-tutorial/")
    ):
        raise ValueError("This lesson does not have a valid LearnCpp article link.")
    if sys.platform == "darwin" and (opener := shutil.which("open")):
        command = [opener, url]
    elif opener := shutil.which("xdg-open"):
        command = [opener, url]
    elif opener := shutil.which("gio"):
        command = [opener, "open", url]
    else:
        command = [sys.executable, "-m", "webbrowser", "-t", url]
    return subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )
