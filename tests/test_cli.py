"""Tests for the gitbloom.cli argv dispatch, run against a real throwaway repo."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gitbloom.cli import main
from gitbloom.install import hook_path, is_installed


def _run(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)


class TestCli(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = self._tmp.name
        _run(["git", "init", "-q"], cwd=self.repo)
        _run(["git", "config", "user.email", "test@example.com"], cwd=self.repo)
        _run(["git", "config", "user.name", "Test User"], cwd=self.repo)
        Path(self.repo, "a.txt").write_text("hello\n")
        _run(["git", "add", "a.txt"], cwd=self.repo)
        _run(["git", "commit", "-q", "-m", "add a.txt"], cwd=self.repo)

    def tearDown(self):
        self._tmp.cleanup()

    def test_install_subcommand_installs_hook(self):
        code = main(["install", self.repo])
        self.assertEqual(code, 0)
        self.assertTrue(is_installed(self.repo))

    def test_uninstall_subcommand_removes_hook(self):
        main(["install", self.repo])
        code = main(["uninstall", self.repo])
        self.assertEqual(code, 0)
        self.assertFalse(hook_path(self.repo).exists())

    def test_build_subcommand_writes_garden_svg(self):
        code = main(["build", self.repo, "--quiet"])
        self.assertEqual(code, 0)
        self.assertTrue(Path(self.repo, "garden.svg").exists())

    def test_install_on_non_repo_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as not_a_repo:
            code = main(["install", not_a_repo])
            self.assertEqual(code, 1)

    def test_missing_subcommand_errors(self):
        with self.assertRaises(SystemExit):
            main([])


if __name__ == "__main__":
    unittest.main()
