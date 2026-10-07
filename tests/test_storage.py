"""Regression checks for the data that must survive upgrades and failures."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cpp_tree.storage import StateError, Store, default_state, parse_state, read_snapshot


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "profile" / "progress.json"

    def store(self):
        store = Store(self.path)
        self.addCleanup(store.close)
        return store

    def test_existing_format_roundtrips_unknown_ids_notes_and_fields(self):
        self.path.parent.mkdir()
        data = default_state()
        data.update(
            completed=["0:0.1", "future:lesson"],
            focus="0:0.1",
            notes={"lesson:0:0.1": "Hello\nمرحبا", "chapter:0": "Practice"},
            extension={"keep": True},
        )
        self.path.write_text(json.dumps(data))
        store = self.store()
        store.save()
        saved = json.loads(self.path.read_text())
        for key, value in data.items():
            self.assertEqual(saved[key], value)
        self.assertEqual(json.loads(Path(str(self.path) + ".bak").read_text()), data)

    def test_corrupt_file_is_preserved_and_lock_is_released(self):
        self.path.parent.mkdir()
        self.path.write_bytes(b"{broken")
        with self.assertRaises(StateError):
            self.store()
        self.assertEqual(self.path.read_bytes(), b"{broken")
        self.path.write_text(json.dumps(default_state()))
        self.store()

    def test_only_one_writer_but_snapshot_is_readable(self):
        store = self.store()
        store.save()
        with self.assertRaises(StateError):
            self.store()
        self.assertEqual(read_snapshot(self.path)["completed"], [])

    def test_atomic_write_failure_preserves_previous_save(self):
        store = self.store()
        store.save()
        before = self.path.read_bytes()
        real_replace = __import__("os").replace

        def fail_progress(source, destination):
            if Path(destination) == self.path:
                raise OSError("simulated disk failure")
            real_replace(source, destination)

        store.data["completed"] = ["0:0.1"]
        with patch("cpp_tree.storage.os.replace", side_effect=fail_progress):
            with self.assertRaises(OSError):
                store.save()
        self.assertEqual(self.path.read_bytes(), before)
        self.assertFalse(list(self.path.parent.glob(".cpp-tree-*")))

    def test_demo_and_missing_snapshot_create_nothing(self):
        store = Store(self.path, demo=True)
        store.save()
        store.close()
        self.assertEqual(read_snapshot(self.path), default_state())
        self.assertFalse(self.path.parent.exists())

    def test_optional_view_is_normalized_without_losing_progress(self):
        data = {
            "version": 1,
            "completed": ["0:0.1"],
            "view": {"group": "missing", "chapter": "missing", "index": -20, "stream": "false"},
        }
        parsed = parse_state(data)
        self.assertEqual(parsed["completed"], ["0:0.1"])
        self.assertEqual(parsed["view"], default_state()["view"])

    def test_invalid_formats_fail_instead_of_resetting_progress(self):
        for changes in (
            {"version": 2},
            {"version": True},
            {"completed": [1]},
            {"notes": {"lesson:0:0.1": 42}},
            {"focus": []},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                parse_state({**default_state(), **changes})
