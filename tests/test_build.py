"""Tests for gitbloom.build, run against real throwaway git repos."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gitbloom.build import GARDEN_FILENAME, NotAGitRepoError, rebuild_garden
from gitbloom.extractor import get_commit_stats
from gitbloom.garden import compose_garden_svg


def _run(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)


class TestRebuildGarden(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = self._tmp.name
        _run(["git", "init", "-q"], cwd=self.repo)
        _run(["git", "config", "user.email", "test@example.com"], cwd=self.repo)
        _run(["git", "config", "user.name", "Test User"], cwd=self.repo)

        Path(self.repo, "a.txt").write_text("one\ntwo\nthree\n")
        _run(["git", "add", "a.txt"], cwd=self.repo)
        _run(["git", "commit", "-q", "-m", "add a.txt"], cwd=self.repo)

    def tearDown(self):
        self._tmp.cleanup()

    def test_writes_garden_svg_at_repo_root(self):
        out_path = rebuild_garden(self.repo)
        self.assertEqual(out_path.name, GARDEN_FILENAME)
        self.assertTrue(out_path.exists())

    def test_written_svg_matches_composer_output(self):
        out_path = rebuild_garden(self.repo)
        commits = get_commit_stats(self.repo)
        expected = compose_garden_svg(commits)
        self.assertEqual(out_path.read_text(), expected)

    def test_rebuild_picks_up_new_commits(self):
        rebuild_garden(self.repo)

        Path(self.repo, "b.txt").write_text("hello\n")
        _run(["git", "add", "b.txt"], cwd=self.repo)
        _run(["git", "commit", "-q", "-m", "add b.txt"], cwd=self.repo)

        out_path = rebuild_garden(self.repo)
        self.assertIn('data-plant-count="2"', out_path.read_text())

    def test_works_from_a_subdirectory(self):
        subdir = Path(self.repo, "sub")
        subdir.mkdir()
        out_path = rebuild_garden(str(subdir))
        self.assertEqual(out_path.resolve(), Path(self.repo, GARDEN_FILENAME).resolve())

    def test_non_repo_path_raises(self):
        with tempfile.TemporaryDirectory() as not_a_repo:
            with self.assertRaises(NotAGitRepoError):
                rebuild_garden(not_a_repo)


if __name__ == "__main__":
    unittest.main()
