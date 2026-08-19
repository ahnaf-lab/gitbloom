"""Tests for gitbloom.render, run against real throwaway git repos."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gitbloom.readme import END_MARKER, START_MARKER, SyncStatus
from gitbloom.render import NotAGitRepoError, render


def _run(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)


class TestRender(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = self._tmp.name
        _run(["git", "init", "-q"], cwd=self.repo)
        _run(["git", "config", "user.email", "test@example.com"], cwd=self.repo)
        _run(["git", "config", "user.name", "Test User"], cwd=self.repo)
        Path(self.repo, "a.txt").write_text("one\n")
        _run(["git", "add", "a.txt"], cwd=self.repo)
        _run(["git", "commit", "-q", "-m", "add a.txt"], cwd=self.repo)

    def tearDown(self):
        self._tmp.cleanup()

    def test_render_writes_garden_svg(self):
        result = render(self.repo)
        self.assertTrue(result.garden_path.exists())

    def test_render_without_readme_reports_no_readme(self):
        result = render(self.repo)
        self.assertEqual(result.readme.status, SyncStatus.NO_README)

    def test_render_updates_readme_markers(self):
        Path(self.repo, "README.md").write_text(f"{START_MARKER}\n{END_MARKER}\n")
        result = render(self.repo)
        self.assertEqual(result.readme.status, SyncStatus.UPDATED)
        text = Path(self.repo, "README.md").read_text()
        self.assertIn("garden.svg", text)

    def test_render_with_update_readme_false_skips_readme(self):
        Path(self.repo, "README.md").write_text(f"{START_MARKER}\n{END_MARKER}\n")
        result = render(self.repo, update_readme=False)
        self.assertEqual(result.readme.status, SyncStatus.SKIPPED)
        text = Path(self.repo, "README.md").read_text()
        self.assertNotIn("garden.svg", text)

    def test_render_on_non_repo_raises(self):
        with tempfile.TemporaryDirectory() as not_a_repo:
            with self.assertRaises(NotAGitRepoError):
                render(not_a_repo)


if __name__ == "__main__":
    unittest.main()
