"""Interaction-level checks: navigation, saves, search, notes, and stream privacy."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cpp_tree.app import App
from cpp_tree.curriculum import CHAPTERS, chapter_keys
from cpp_tree.models import Options
from cpp_tree.storage import Store, read_snapshot


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "progress.json"
        self.store = Store(self.path)
        self.addCleanup(self.store.close)
        self.app = App(self.store, Options(self.path))

    def test_toggle_undo_redo_are_persisted(self):
        app = self.app
        app.handle("\n")
        self.assertEqual(app.chapter, "0")
        app.handle(" ")
        self.assertIn("0:0.1", read_snapshot(self.path)["completed"])
        app.handle("u")
        self.assertNotIn("0:0.1", app.done)
        app.handle("r")
        self.assertIn("0:0.1", read_snapshot(self.path)["completed"])

    def test_bulk_confirm_cancel_and_undo_preserve_other_ids(self):
        app = self.app
        app.done = {"future:lesson"}
        app.handle("b")
        app.handle("n")
        self.assertEqual(app.done, {"future:lesson"})
        app.handle("b")
        app.handle("y")
        self.assertEqual(app.done, chapter_keys(CHAPTERS["0"]) | {"future:lesson"})
        app.handle("u")
        self.assertEqual(app.done, {"future:lesson"})

    def test_pin_and_jump_work_across_trees_and_search(self):
        app = self.app
        app.handle("\n")
        app.handle("f")
        app.handle("\t")
        app.handle("F")
        self.assertEqual((app.group, app.chapter, app.index), ("main", "0", 0))
        app.handle("/")
        app.query = "boolean"
        self.assertEqual(app.results()[0][2]["id"], "4.9")
        app.handle("\x06")
        self.assertIsNone(app.modal)
        self.assertEqual(app.selected()["key"], "0:0.1")
        self.assertEqual(read_snapshot(self.path)["focus"], "0:0.1")

    def test_search_opens_selected_lesson_without_leaving_search(self):
        app = self.app
        app.handle("/")
        app.query = "4.9"
        with patch.object(app, "open_lesson") as open_lesson:
            app.handle("\x0f")
        self.assertEqual(open_lesson.call_args.args[0]["key"], "4:4.9")
        self.assertEqual(app.modal, ("search",))

    def test_notes_save_cancel_and_stream_view_hide_contents(self):
        app = self.app
        app.handle("\n")
        app.handle("e")
        app.note_buffer = "PRIVATE NOTE CONTENT\nsecond line"
        app.handle("\x13")
        self.assertEqual(read_snapshot(self.path)["notes"]["lesson:0:0.1"], app.note_buffer)
        app.handle("e")
        app.note_buffer = "Discard this"
        app.handle("\x1b")
        app.handle("d")
        self.assertNotEqual(app.notes["lesson:0:0.1"], "Discard this")
        app.handle("s")
        app.handle("e")
        self.assertIsNone(app.modal)
        text = "\n".join("".join(ch for ch, _ in row) for row in app.render(160, 52).cells)
        self.assertNotIn("PRIVATE NOTE CONTENT", text)
        self.assertNotIn("PRIVATE NOTE CONTENT", self.path.with_name("stream.txt").read_text())

    def test_unsaved_lesson_and_chapter_notes_can_resume_and_save(self):
        app = self.app
        app.handle("\n")
        for shortcut, note_key in (("e", "lesson:0:0.1"), ("E", "chapter:0")):
            with self.subTest(shortcut=shortcut):
                app.handle(shortcut)
                for key in "Draft notes":
                    app.handle(key)
                editor = app.modal
                position = (app.note_cursor, app.note_offset)
                for resume in ("\x1b", "\n", "c"):
                    app.handle("\x1b")
                    self.assertIsNotNone(app.modal)
                    text = "\n".join(
                        "".join(ch for ch, _ in row) for row in app.render(72, 22).cells
                    )
                    self.assertIn("UNSAVED NOTE CHANGES", text)
                    self.assertIn("Save and close", text)
                    self.assertIn("Discard changes", text)
                    self.assertIn("Keep editing", text)
                    self.assertNotIn(note_key, read_snapshot(self.path)["notes"])
                    app.handle(resume)
                    self.assertEqual(app.modal, editor)
                    self.assertEqual(app.note_buffer, "Draft notes")
                    self.assertEqual((app.note_cursor, app.note_offset), position)
                app.handle("!")
                app.handle("\x1b")
                app.handle("s" if shortcut == "e" else "\x13")
                self.assertIsNone(app.modal)
                self.assertEqual(read_snapshot(self.path)["notes"][note_key], "Draft notes!")
                app.handle(shortcut)
                self.assertEqual(app.note_buffer, "Draft notes!")
                app.handle("\x1b")
                self.assertIsNone(app.modal)

    def test_discarding_edits_or_deletion_keeps_previous_note(self):
        app = self.app
        app.handle("\n")
        for shortcut, note_key in (("e", "lesson:0:0.1"), ("E", "chapter:0")):
            with self.subTest(shortcut=shortcut):
                app.handle(shortcut)
                app.note_buffer = "Previously saved"
                app.handle("\x13")
                for draft in ("Replacement", ""):
                    app.handle(shortcut)
                    app.note_buffer = draft
                    app.handle("\x1b")
                    self.assertIsNotNone(app.modal)
                    app.handle("d")
                    self.assertIsNone(app.modal)
                    self.assertEqual(
                        read_snapshot(self.path)["notes"][note_key], "Previously saved"
                    )
                    app.handle(shortcut)
                    self.assertEqual(app.note_buffer, "Previously saved")
                    app.handle("\x1b")
                app.handle(shortcut)
                app.note_buffer = ""
                app.handle("\x1b")
                app.handle("s")
                self.assertIsNone(app.modal)
                self.assertNotIn(note_key, read_snapshot(self.path)["notes"])

    def test_unchanged_notes_close_without_prompt_or_write(self):
        app = self.app
        app.handle("\n")
        for shortcut in ("e", "E"):
            with self.subTest(shortcut=shortcut), patch.object(self.store, "save") as save:
                app.handle(shortcut)
                app.handle("x")
                app.handle("\x7f")
                app.handle("\x1b")
                self.assertIsNone(app.modal)
                save.assert_not_called()

    def test_confirmation_save_failure_keeps_draft_and_allows_retry(self):
        app = self.app
        app.handle("\n")
        app.handle("e")
        app.note_buffer = "Original note"
        app.handle("\x13")
        app.handle("e")
        editor = app.modal
        app.note_buffer = "Keep this draft"
        with patch.object(self.store, "save", side_effect=OSError("disk full")):
            app.handle("\x1b")
            app.handle("s")
        self.assertEqual(app.modal, editor)
        self.assertEqual(app.note_buffer, "Keep this draft")
        self.assertEqual(app.notes["lesson:0:0.1"], "Original note")
        self.assertEqual(read_snapshot(self.path)["notes"]["lesson:0:0.1"], "Original note")
        text = "\n".join("".join(ch for ch, _ in row) for row in app.render(72, 22).cells)
        self.assertIn("Save failed. Text kept in editor.", text)
        app.handle("\x13")
        self.assertIsNone(app.modal)
        self.assertEqual(read_snapshot(self.path)["notes"]["lesson:0:0.1"], "Keep this draft")

    def test_demo_notes_confirmation_does_not_write_to_disk(self):
        path = Path(self.temp.name) / "demo" / "progress.json"
        app = App(Store(path, demo=True), Options(path))
        app.handle("E")
        app.note_buffer = "Demo draft"
        app.handle("\x1b")
        app.handle("s")
        self.assertIsNone(app.modal)
        self.assertEqual(app.notes["chapter:0"], "Demo draft")
        self.assertFalse(path.parent.exists())

    def test_failed_save_rolls_back_progress_focus_and_notes(self):
        app = self.app
        app.handle("\n")
        with patch.object(self.store, "save", side_effect=OSError("disk full")):
            app.handle(" ")
            self.assertEqual(app.done, set())
            app.handle("f")
            self.assertIsNone(app.focus)
            app.handle("e")
            app.note_buffer = "keep me in editor"
            app.handle("\x13")
            self.assertEqual(app.notes, {})
            self.assertEqual(app.note_buffer, "keep me in editor")
            self.assertIsNotNone(app.modal)

    def test_stream_status_uses_pin_then_next_incomplete_lesson(self):
        app = self.app
        app.chapter, app.index = "4", 8
        app.handle("f")
        self.assertEqual(
            self.path.with_name("stream.txt").read_text(),
            "Fundamental Data Types\nBoolean values\n",
        )
        app.focus = None
        app.done = {"0:0.1"}
        self.assertIn("Introduction to programs", app.stream_status())

    def test_render_at_supported_and_small_sizes_with_all_modals(self):
        app = self.app
        for size in ((1, 1), (60, 18), (72, 22), (100, 30), (160, 52)):
            for modal in (
                None,
                ("search",),
                ("help",),
                ("bulk", "0"),
                ("notes", "chapter:0", "CHAPTER 0", "Notes"),
                ("notes_confirm", "chapter:0", "CHAPTER 0", "Notes"),
            ):
                with self.subTest(size=size, modal=modal):
                    app.modal = modal
                    frame = app.render(*size)
                    self.assertEqual(len(frame.cells), size[1])
                    self.assertTrue(all(len(row) == size[0] for row in frame.cells))
        app.args.ascii = True
        self.assertTrue(all(ch.isascii() for row in app.render(100, 30).cells for ch, _ in row))
