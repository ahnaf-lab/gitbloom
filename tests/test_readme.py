"""Tests for gitbloom.readme, the marker-based README sync."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gitbloom.readme import END_MARKER, START_MARKER, SyncStatus, sync_readme


class TestSyncReadme(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_readme_returns_no_readme(self):
        result = sync_readme(str(self.repo))
        self.assertEqual(result.status, SyncStatus.NO_README)
        self.assertFalse(result.updated)

    def test_readme_without_markers_returns_no_markers(self):
        (self.repo / "README.md").write_text("# hello\n\nno markers here\n")
        result = sync_readme(str(self.repo))
        self.assertEqual(result.status, SyncStatus.NO_MARKERS)

    def test_readme_without_markers_is_left_untouched(self):
        original = "# hello\n\nno markers here\n"
        (self.repo / "README.md").write_text(original)
        sync_readme(str(self.repo))
        self.assertEqual((self.repo / "README.md").read_text(), original)

    def test_inserts_image_between_markers(self):
        (self.repo / "README.md").write_text(f"# hello\n\n{START_MARKER}\n{END_MARKER}\n")
        result = sync_readme(str(self.repo))
        self.assertEqual(result.status, SyncStatus.UPDATED)
        text = (self.repo / "README.md").read_text()
        self.assertIn("![garden](garden.svg)", text)
        self.assertIn(START_MARKER, text)
        self.assertIn(END_MARKER, text)

    def test_preserves_content_outside_markers(self):
        (self.repo / "README.md").write_text(
            f"# hello\n\nintro text\n\n{START_MARKER}\n{END_MARKER}\n\noutro text\n"
        )
        sync_readme(str(self.repo))
        text = (self.repo / "README.md").read_text()
        self.assertIn("intro text", text)
        self.assertIn("outro text", text)

    def test_replaces_stale_content_between_markers(self):
        (self.repo / "README.md").write_text(
            f"{START_MARKER}\n![garden](old/path.svg)\n{END_MARKER}\n"
        )
        sync_readme(str(self.repo), image_relpath="garden.svg")
        text = (self.repo / "README.md").read_text()
        self.assertNotIn("old/path.svg", text)
        self.assertIn("garden.svg", text)

    def test_second_call_with_no_change_reports_unchanged(self):
        (self.repo / "README.md").write_text(f"{START_MARKER}\n{END_MARKER}\n")
        sync_readme(str(self.repo))
        result = sync_readme(str(self.repo))
        self.assertEqual(result.status, SyncStatus.UNCHANGED)

    def test_custom_image_path_is_used(self):
        (self.repo / "README.md").write_text(f"{START_MARKER}\n{END_MARKER}\n")
        sync_readme(str(self.repo), image_relpath="assets/garden.svg")
        text = (self.repo / "README.md").read_text()
        self.assertIn("![garden](assets/garden.svg)", text)


if __name__ == "__main__":
    unittest.main()
