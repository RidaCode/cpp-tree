"""Drive actual curses sessions through a pseudoterminal, including saves."""

import fcntl
import os
import pty
import select
import struct
import subprocess
import sys
import tempfile
import termios
import time
import unittest
from pathlib import Path

from cpp_tree.storage import read_snapshot

ROOT = Path(__file__).resolve().parents[1]


class TerminalTests(unittest.TestCase):
    def test_interactive_search_notes_save_and_terminal_modes(self):
        for mode in ("truecolor", "256"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as work:
                master, slave = pty.openpty()
                state = Path(work) / "progress.json"
                fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 140, 0, 0))
                process = subprocess.Popen(
                    [sys.executable, "-m", "cpp_tree", "--state", str(state), "--color", mode],
                    cwd=ROOT,
                    stdin=slave,
                    stdout=slave,
                    stderr=slave,
                    env={**os.environ, "TERM": "xterm-256color"},
                )
                os.close(slave)
                transcript = bytearray()

                def read_until(marker, timeout=8):
                    deadline = time.monotonic() + timeout
                    while marker not in transcript and time.monotonic() < deadline:
                        readable, _, _ = select.select([master], [], [], 0.1)
                        if readable:
                            try:
                                transcript.extend(os.read(master, 65536))
                            except OSError:
                                break
                        if process.poll() is not None:
                            break
                    self.assertIn(marker, transcript, transcript[-2000:])

                try:
                    read_until(b"CORE TALENTS")
                    os.write(master, b"/4.9\nfe")
                    read_until(b"NOTES")
                    os.write(master, b"Terminal integration test\x13 q")
                    read_until(b"Progress saved")
                    self.assertEqual(process.wait(timeout=5), 0)
                    data = read_snapshot(state)
                    self.assertEqual(data["focus"], "4:4.9")
                    self.assertIn("4:4.9", data["completed"])
                    self.assertEqual(data["notes"]["lesson:4:4.9"], "Terminal integration test")
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
                    os.close(master)
