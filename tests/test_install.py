import io
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build import build_archive  # noqa: E402

from cpp_tree.installation import install_archive  # noqa: E402


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cpp tree test ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = build_archive(self.root / "app.pyz")
        self.target = self.root / "bin" / "cpp-tree"

    def test_build_is_reproducible_and_bundles_resources(self):
        second = build_archive(self.root / "second.pyz")
        self.assertEqual(self.archive.read_bytes(), second.read_bytes())
        with zipfile.ZipFile(self.archive) as archive:
            self.assertIn("cpp_tree/data/learncpp.json", archive.namelist())
            self.assertIn("LICENSE", archive.namelist())
            self.assertFalse(
                any("__pycache__" in name or name.endswith(".pyc") for name in archive.namelist())
            )
        result = subprocess.run(
            [sys.executable, str(self.archive), "--demo", "--summary"],
            cwd=self.root,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("43/331", result.stdout)

    def test_install_update_and_uninstall_keep_state_and_unrelated_files(self):
        profile = self.root / "state" / "cpp-tree"
        profile.mkdir(parents=True)
        (profile / "progress.json").write_text("user data")
        (profile / "stream.txt").write_text("current lesson")
        install_archive(self.archive, self.target)
        other = self.target.with_name("another-tool")
        other.write_text("keep")
        install_archive(self.archive, self.target)
        result = subprocess.run(
            [sys.executable, str(self.target), "--uninstall"],
            cwd=self.root,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.target.exists())
        self.assertEqual(other.read_text(), "keep")
        self.assertEqual((profile / "progress.json").read_text(), "user data")
        self.assertEqual((profile / "stream.txt").read_text(), "current lesson")

    def test_existing_file_and_symlinks_are_never_overwritten(self):
        self.target.parent.mkdir()
        self.target.write_text("legacy or unrelated executable")
        with self.assertRaises(ValueError):
            install_archive(self.archive, self.target)
        self.assertEqual(self.target.read_text(), "legacy or unrelated executable")
        self.target.unlink()
        self.target.symlink_to(self.root / "missing-target")
        with self.assertRaises(ValueError):
            install_archive(self.archive, self.target)
        self.assertTrue(self.target.is_symlink())

    def test_failed_install_leaves_existing_version_intact(self):
        install_archive(self.archive, self.target)
        before = self.target.read_bytes()
        with patch("cpp_tree.installation.os.replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                install_archive(self.archive, self.target)
        self.assertEqual(self.target.read_bytes(), before)
        self.assertFalse(list(self.target.parent.glob(".cpp-tree-install-*")))

    def source_archive(self):
        archive_path = self.root / "source.tar.gz"
        with tarfile.open(archive_path, "w:gz") as archive:
            for name in (
                "cpp_tree",
                "scripts/build.py",
                "scripts/install.py",
                "LICENSE",
                "NOTICE.md",
            ):
                path = ROOT / name
                paths = sorted(path.rglob("*")) if path.is_dir() else [path]
                for entry in paths:
                    if entry.is_file() and "__pycache__" not in entry.parts:
                        archive.add(entry, arcname="cpp-tree-main/" + str(entry.relative_to(ROOT)))
        return archive_path

    def test_bootstrap_installs_from_archive_with_space_in_destination(self):
        source = self.source_archive()
        result = subprocess.run(
            ["sh", str(ROOT / "install.sh"), "--bin-dir", str(self.target.parent)],
            env={**os.environ, "CPP_TREE_ARCHIVE": str(source)},
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run([str(self.target), "--version"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("cpp-tree", result.stdout)

    def test_bootstrap_rejects_traversal_and_links(self):
        for name, kind in (
            ("cpp-tree-main/../../escaped", tarfile.REGTYPE),
            ("cpp-tree-main/cpp_tree/bad.py", tarfile.SYMTYPE),
        ):
            with self.subTest(name=name):
                source = self.root / "bad.tar.gz"
                with tarfile.open(source, "w:gz") as archive:
                    info = tarfile.TarInfo(name)
                    info.type = kind
                    info.linkname = "/tmp/target" if kind == tarfile.SYMTYPE else ""
                    archive.addfile(info, io.BytesIO(b""))
                result = subprocess.run(
                    ["sh", str(ROOT / "install.sh"), "--bin-dir", str(self.target.parent)],
                    env={**os.environ, "CPP_TREE_ARCHIVE": str(source)},
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.target.exists())
                self.assertFalse((self.root / "escaped").exists())
