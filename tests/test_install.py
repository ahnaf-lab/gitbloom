"""Tests for gitbloom.install, run against real throwaway git repos."""

import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gitbloom.install import (
    MARKER,
    HookConflictError,
    NotAGitRepoError,
    hook_path,
    install_hook,
    is_installed,
    uninstall_hook,
)


def _run(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)


class TestInstallHook(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = self._tmp.name
        _run(["git", "init", "-q"], cwd=self.repo)

    def tearDown(self):
        self._tmp.cleanup()

    def test_install_writes_hook_containing_marker(self):
        path = install_hook(self.repo)
        self.assertTrue(path.exists())
        self.assertIn(MARKER, path.read_text())

    def test_install_writes_to_expected_hooks_path(self):
        path = install_hook(self.repo)
        self.assertEqual(path, hook_path(self.repo))
        self.assertEqual(path.parent.name, "hooks")

    def test_install_makes_hook_executable(self):
        path = install_hook(self.repo)
        mode = path.stat().st_mode
        self.assertTrue(mode & stat.S_IXUSR)

    def test_is_installed_reflects_state(self):
        self.assertFalse(is_installed(self.repo))
        install_hook(self.repo)
        self.assertTrue(is_installed(self.repo))

    def test_install_is_idempotent(self):
        first = install_hook(self.repo)
        second = install_hook(self.repo)
        self.assertEqual(first.read_text(), second.read_text())

    def test_install_refuses_to_clobber_foreign_hook(self):
        path = hook_path(self.repo)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("#!/bin/sh\necho not gitbloom\n")

        with self.assertRaises(HookConflictError):
            install_hook(self.repo)
        # the foreign hook must be untouched
        self.assertIn("not gitbloom", path.read_text())

    def test_install_force_overwrites_foreign_hook(self):
        path = hook_path(self.repo)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("#!/bin/sh\necho not gitbloom\n")

        install_hook(self.repo, force=True)
        self.assertIn(MARKER, path.read_text())

    def test_uninstall_removes_installed_hook(self):
        install_hook(self.repo)
        removed = uninstall_hook(self.repo)
        self.assertTrue(removed)
        self.assertFalse(hook_path(self.repo).exists())

    def test_uninstall_on_missing_hook_returns_false(self):
        removed = uninstall_hook(self.repo)
        self.assertFalse(removed)

    def test_uninstall_refuses_to_remove_foreign_hook(self):
        path = hook_path(self.repo)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("#!/bin/sh\necho not gitbloom\n")

        with self.assertRaises(HookConflictError):
            uninstall_hook(self.repo)
        self.assertTrue(path.exists())

    def test_non_repo_path_raises(self):
        with tempfile.TemporaryDirectory() as not_a_repo:
            with self.assertRaises(NotAGitRepoError):
                install_hook(not_a_repo)


if __name__ == "__main__":
    unittest.main()
