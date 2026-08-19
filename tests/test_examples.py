"""Tests for examples/generate_example.py and the checked-in examples/garden.svg.

Guards the README's embedded preview against silent drift: if a change to
the extractor, plant generator or garden composer would alter the example's
output, this fails instead of the checked-in SVG quietly going stale.
"""

import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "examples"))

from generate_example import FIXTURE_COMMITS, build_fixture_repo, generate_svg
from gitbloom.extractor import get_commit_stats

EXAMPLE_SVG_PATH = _ROOT / "examples" / "garden.svg"


class TestExampleGarden(unittest.TestCase):
    def test_checked_in_example_exists(self):
        self.assertTrue(EXAMPLE_SVG_PATH.exists())

    def test_regenerated_matches_checked_in_example(self):
        self.assertEqual(generate_svg(), EXAMPLE_SVG_PATH.read_text())

    def test_example_has_one_plant_per_fixture_commit(self):
        svg = EXAMPLE_SVG_PATH.read_text()
        self.assertIn(f'data-plant-count="{len(FIXTURE_COMMITS)}"', svg)

    def test_generation_is_deterministic_across_separate_repos(self):
        # Two independently-built fixture repos, in different temp
        # directories, must still produce byte-identical output.
        with tempfile.TemporaryDirectory() as tmp_a, tempfile.TemporaryDirectory() as tmp_b:
            repo_a, repo_b = Path(tmp_a), Path(tmp_b)
            build_fixture_repo(repo_a)
            build_fixture_repo(repo_b)
            commits_a = get_commit_stats(str(repo_a))
            commits_b = get_commit_stats(str(repo_b))

        self.assertEqual(
            [c.commit_hash for c in commits_a], [c.commit_hash for c in commits_b]
        )

    def test_example_is_a_standalone_svg_document(self):
        svg = EXAMPLE_SVG_PATH.read_text()
        self.assertTrue(svg.startswith("<svg "))
        self.assertTrue(svg.endswith("</svg>"))


if __name__ == "__main__":
    unittest.main()
