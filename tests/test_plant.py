"""Golden-file tests for gitbloom.plant.

Each fixture in ``tests/golden/`` is a fixed, hand-picked ``CommitStats``
record chosen to exercise a different part of the mapping (a tiny no-op
commit, a typical commit, a huge rewrite, a mostly-deletion commit). The
expected SVG for each was generated once with ``generate_plant_svg`` and
checked in; a test failure here means the deterministic stats->SVG mapping
changed, which should only happen deliberately.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gitbloom.extractor import CommitStats
from gitbloom.plant import derive_plant_params, generate_plant_svg

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"

# Fixed sample "logs": hand-built CommitStats, not read from a real repo, so
# the fixtures never change out from under the tests.
SAMPLE_COMMITS = {
    "empty_commit": CommitStats(
        commit_hash="0" * 40,
        author="Nobody",
        timestamp=0,
        subject="",
        message_length=0,
        files=0,
        insertions=0,
        deletions=0,
    ),
    "typical_commit": CommitStats(
        commit_hash="a1b2c3d4" + "e" * 32,
        author="Ada Lovelace",
        timestamp=1_700_000_000,
        subject="add flowering behaviour",
        message_length=len("add flowering behaviour"),
        files=3,
        insertions=42,
        deletions=5,
    ),
    "huge_rewrite": CommitStats(
        commit_hash="f" * 40,
        author="Grace Hopper",
        timestamp=1_700_100_000,
        subject="rewrite everything, again, with a much longer message this time",
        message_length=len(
            "rewrite everything, again, with a much longer message this time"
        ),
        files=250,
        insertions=9000,
        deletions=10,
    ),
    "mostly_deletions": CommitStats(
        commit_hash="deadbeef" + "0" * 32,
        author="Margaret Hamilton",
        timestamp=1_700_200_000,
        subject="remove dead code",
        message_length=len("remove dead code"),
        files=2,
        insertions=1,
        deletions=199,
    ),
}


class TestPlantGolden(unittest.TestCase):
    def test_golden_fixtures_exist_for_every_sample(self):
        for name in SAMPLE_COMMITS:
            self.assertTrue(
                (GOLDEN_DIR / f"{name}.svg").exists(),
                f"missing golden file for {name}",
            )

    def test_matches_golden_output(self):
        for name, stats in SAMPLE_COMMITS.items():
            with self.subTest(name=name):
                expected = (GOLDEN_DIR / f"{name}.svg").read_text()
                actual = generate_plant_svg(stats)
                self.assertEqual(actual, expected)

    def test_output_is_deterministic_across_calls(self):
        stats = SAMPLE_COMMITS["typical_commit"]
        first = generate_plant_svg(stats)
        second = generate_plant_svg(stats)
        self.assertEqual(first, second)


class TestPlantParams(unittest.TestCase):
    def test_empty_commit_has_minimum_stem_and_no_leaves(self):
        params = derive_plant_params(SAMPLE_COMMITS["empty_commit"])
        self.assertEqual(params.stem_height, 30)
        self.assertEqual(params.leaf_count, 0)
        self.assertEqual(params.wilt_percent, 0)

    def test_huge_rewrite_clamps_stem_height_and_leaf_count(self):
        params = derive_plant_params(SAMPLE_COMMITS["huge_rewrite"])
        # 250 files and 9000+ churn would blow past the canvas unclamped.
        self.assertEqual(params.stem_height, 160)
        self.assertEqual(params.leaf_count, 6)

    def test_mostly_deletions_is_heavily_wilted(self):
        params = derive_plant_params(SAMPLE_COMMITS["mostly_deletions"])
        self.assertGreater(params.wilt_percent, 90)

    def test_petal_count_scales_with_message_length(self):
        short = derive_plant_params(SAMPLE_COMMITS["mostly_deletions"])  # 17 chars
        long = derive_plant_params(SAMPLE_COMMITS["huge_rewrite"])  # 66 chars
        self.assertLess(short.petal_count, long.petal_count)

    def test_identical_stats_except_hash_render_different_hue(self):
        base = SAMPLE_COMMITS["typical_commit"]
        other = CommitStats(**{**base.to_dict(), "commit_hash": "1" * 40})
        params_a = derive_plant_params(base)
        params_b = derive_plant_params(other)
        self.assertNotEqual(params_a.hue, params_b.hue)

    def test_svg_is_well_formed_and_tagged_with_commit(self):
        stats = SAMPLE_COMMITS["typical_commit"]
        svg = generate_plant_svg(stats)
        self.assertTrue(svg.startswith("<svg"))
        self.assertTrue(svg.endswith("</svg>"))
        self.assertIn(f'data-commit="{stats.commit_hash[:8]}"', svg)


if __name__ == "__main__":
    unittest.main()
