"""Tests for gitbloom.extractor, run against a real throwaway git repo."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gitbloom.extractor import CommitStats, GitLogError, get_commit_stats


def _run(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)


class TestExtractor(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = self._tmp.name
        _run(["git", "init", "-q"], cwd=self.repo)
        _run(["git", "config", "user.email", "test@example.com"], cwd=self.repo)
        _run(["git", "config", "user.name", "Test User"], cwd=self.repo)

        # First commit: one new file, three lines added.
        Path(self.repo, "a.txt").write_text("one\ntwo\nthree\n")
        _run(["git", "add", "a.txt"], cwd=self.repo)
        _run(["git", "commit", "-q", "-m", "add a.txt"], cwd=self.repo)

        # Second commit: modify a.txt (remove a line, add two) and add b.txt.
        Path(self.repo, "a.txt").write_text("one\ntwo\nthree\nfour\nfive\n")
        Path(self.repo, "b.txt").write_text("hello\n")
        _run(["git", "add", "-A"], cwd=self.repo)
        _run(["git", "commit", "-q", "-m", "grow the garden a little"], cwd=self.repo)

    def tearDown(self):
        self._tmp.cleanup()

    def test_returns_one_entry_per_commit(self):
        commits = get_commit_stats(self.repo)
        self.assertEqual(len(commits), 2)
        self.assertTrue(all(isinstance(c, CommitStats) for c in commits))

    def test_oldest_first_ordering(self):
        commits = get_commit_stats(self.repo, oldest_first=True)
        self.assertEqual(commits[0].subject, "add a.txt")
        self.assertEqual(commits[1].subject, "grow the garden a little")

    def test_first_commit_stats(self):
        commits = get_commit_stats(self.repo, oldest_first=True)
        first = commits[0]
        self.assertEqual(first.files, 1)
        self.assertEqual(first.insertions, 3)
        self.assertEqual(first.deletions, 0)
        self.assertEqual(first.message_length, len("add a.txt"))
        self.assertEqual(len(first.commit_hash), 40)

    def test_second_commit_touches_two_files(self):
        commits = get_commit_stats(self.repo, oldest_first=True)
        second = commits[1]
        self.assertEqual(second.files, 2)
        self.assertEqual(second.insertions, 3)  # 2 lines in a.txt + 1 in b.txt
        self.assertEqual(second.deletions, 0)

    def test_rejects_option_like_rev_range(self):
        with self.assertRaises(ValueError):
            get_commit_stats(self.repo, rev_range="--upload-pack=evil")

    def test_bad_repo_path_raises_git_log_error(self):
        with tempfile.TemporaryDirectory() as not_a_repo:
            with self.assertRaises(GitLogError):
                get_commit_stats(not_a_repo)

    def test_to_dict_round_trips_fields(self):
        commits = get_commit_stats(self.repo)
        as_dict = commits[0].to_dict()
        self.assertEqual(
            set(as_dict.keys()),
            {
                "commit_hash",
                "author",
                "timestamp",
                "subject",
                "message_length",
                "files",
                "insertions",
                "deletions",
            },
        )


if __name__ == "__main__":
    unittest.main()
