import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cpp_tree.storage import Store

ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = {**os.environ, "XDG_STATE_HOME": str(self.root / "state")}

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "cpp_tree", *args],
            cwd=ROOT,
            env=self.env,
            text=True,
            capture_output=True,
        )

    def test_help_version_summary_and_path_do_not_create_state(self):
        for flags in (
            ("--help",),
            ("--version",),
            ("--summary",),
            ("--demo", "--summary"),
            ("--state-path",),
        ):
            with self.subTest(flags=flags):
                result = self.run_cli(*flags)
                self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root / "state").exists())
        self.assertIn(
            str(self.root / "state" / "cpp-tree" / "progress.json"),
            self.run_cli("--state-path").stdout,
        )

    def test_summary_reads_while_app_is_open_without_changing_files(self):
        path = self.root / "progress.json"
        with_store = Store(path)
        self.addCleanup(with_store.close)
        with_store.data["completed"] = ["0:0.1"]
        with_store.save()
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.iterdir()}
        result = self.run_cli("--summary", "--state", str(path))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1/331", result.stdout)
        after = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.iterdir()}
        self.assertEqual(before, after)

    def test_bad_state_and_noninteractive_run_fail_clearly(self):
        path = self.root / "bad.json"
        path.write_text("{bad")
        result = self.run_cli("--summary", "--state", str(path))
        self.assertEqual(result.returncode, 1)
        self.assertIn("Could not read progress", result.stderr)
        self.assertEqual(path.read_text(), "{bad")
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn("interactive terminal", result.stderr)
        self.assertFalse((self.root / "state").exists())

    def test_source_checkout_cannot_uninstall_itself(self):
        result = self.run_cli("--uninstall")
        self.assertEqual(result.returncode, 1)
        self.assertIn("not an installer-managed", result.stderr)
        self.assertTrue((ROOT / "cpp_tree" / "__main__.py").exists())
