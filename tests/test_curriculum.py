import copy
import unittest
from unittest.mock import patch

from cpp_tree.browser import launch_browser
from cpp_tree.curriculum import CURRICULUM, LESSONS, validate_curriculum


class CurriculumTests(unittest.TestCase):
    def test_all_indexed_lessons_have_unique_keys_and_valid_links(self):
        self.assertEqual(validate_curriculum(CURRICULUM), CURRICULUM)
        self.assertEqual(len(LESSONS), sum(len(c["lessons"]) for c in CURRICULUM))

    def test_duplicate_and_unsafe_entries_fail_validation(self):
        bad = copy.deepcopy(CURRICULUM)
        bad[0]["lessons"].append(bad[0]["lessons"][0])
        with self.assertRaisesRegex(ValueError, "duplicate lesson"):
            validate_curriculum(bad)
        bad = copy.deepcopy(CURRICULUM)
        bad[0]["lessons"][0]["url"] = "https://evil.example/cpp-tutorial/test"
        with self.assertRaises(ValueError):
            validate_curriculum(bad)

    def test_browser_rejects_invalid_urls_before_launch(self):
        with patch("cpp_tree.browser.subprocess.Popen") as popen:
            for url in (
                "file:///tmp/test",
                "https://www.learncpp.com.evil.test/cpp-tutorial/x",
                "https://www.learncpp.com@evil.test/cpp-tutorial/x",
                "http://www.learncpp.com/cpp-tutorial/x",
            ):
                with self.subTest(url=url), self.assertRaises(ValueError):
                    launch_browser(url)
            popen.assert_not_called()
