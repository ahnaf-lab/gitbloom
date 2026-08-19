"""Golden-file tests for gitbloom.garden.

Mirrors the approach in ``tests/test_plant.py``: fixed, hand-built commit
lists exercise the composer (no commits, one commit, several commits with
very different shapes), and the expected SVG for each is checked into
``tests/golden_garden/``. A failure here means the deterministic layout
changed, which should only happen deliberately.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gitbloom.extractor import CommitStats
from gitbloom.garden import (
    EMPTY_GARDEN_HEIGHT,
    EMPTY_GARDEN_WIDTH,
    PLANT_SPACING,
    compose_garden_svg,
)
from gitbloom.plant import CANVAS_HEIGHT, CANVAS_WIDTH

GOLDEN_DIR = Path(__file__).resolve().parent / "golden_garden"

TINY_COMMIT = CommitStats(
    commit_hash="0" * 40,
    author="Nobody",
    timestamp=0,
    subject="",
    message_length=0,
    files=0,
    insertions=0,
    deletions=0,
)

TYPICAL_COMMIT = CommitStats(
    commit_hash="a1b2c3d4" + "e" * 32,
    author="Ada Lovelace",
    timestamp=1_700_000_000,
    subject="add flowering behaviour",
    message_length=len("add flowering behaviour"),
    files=3,
    insertions=42,
    deletions=5,
)

HUGE_COMMIT = CommitStats(
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
)

WILTED_COMMIT = CommitStats(
    commit_hash="deadbeef" + "0" * 32,
    author="Margaret Hamilton",
    timestamp=1_700_200_000,
    subject="remove dead code",
    message_length=len("remove dead code"),
    files=2,
    insertions=1,
    deletions=199,
)

SAMPLE_GARDENS = {
    "empty_garden": [],
    "single_plant_garden": [TYPICAL_COMMIT],
    "four_plant_garden": [TINY_COMMIT, TYPICAL_COMMIT, HUGE_COMMIT, WILTED_COMMIT],
}


class TestGardenGolden(unittest.TestCase):
    def test_golden_fixtures_exist_for_every_sample(self):
        for name in SAMPLE_GARDENS:
            self.assertTrue(
                (GOLDEN_DIR / f"{name}.svg").exists(),
                f"missing golden file for {name}",
            )

    def test_matches_golden_output(self):
        for name, commits in SAMPLE_GARDENS.items():
            with self.subTest(name=name):
                expected = (GOLDEN_DIR / f"{name}.svg").read_text()
                actual = compose_garden_svg(commits)
                self.assertEqual(actual, expected)

    def test_output_is_deterministic_across_calls(self):
        commits = SAMPLE_GARDENS["four_plant_garden"]
        first = compose_garden_svg(commits)
        second = compose_garden_svg(commits)
        self.assertEqual(first, second)


class TestGardenLayout(unittest.TestCase):
    def test_empty_garden_has_no_plants_but_is_valid_svg(self):
        svg = compose_garden_svg([])
        self.assertTrue(svg.startswith("<svg"))
        self.assertTrue(svg.endswith("</svg>"))
        self.assertIn('data-plant-count="0"', svg)
        self.assertNotIn("data-commit=", svg)

    def test_empty_garden_matches_declared_constants(self):
        svg = compose_garden_svg([])
        self.assertIn(f'width="{EMPTY_GARDEN_WIDTH}"', svg)
        self.assertIn(f'height="{EMPTY_GARDEN_HEIGHT}"', svg)

    def test_width_grows_by_exactly_one_spacing_unit_per_commit(self):
        one = compose_garden_svg([TYPICAL_COMMIT])
        two = compose_garden_svg([TYPICAL_COMMIT, HUGE_COMMIT])
        three = compose_garden_svg([TYPICAL_COMMIT, HUGE_COMMIT, WILTED_COMMIT])

        def _width(svg: str) -> int:
            start = svg.index('width="') + len('width="')
            end = svg.index('"', start)
            return int(svg[start:end])

        self.assertEqual(_width(two) - _width(one), PLANT_SPACING)
        self.assertEqual(_width(three) - _width(two), PLANT_SPACING)

    def test_height_is_independent_of_commit_count(self):
        one = compose_garden_svg([TYPICAL_COMMIT])
        four = compose_garden_svg([TINY_COMMIT, TYPICAL_COMMIT, HUGE_COMMIT, WILTED_COMMIT])
        self.assertIn(f'height="{EMPTY_GARDEN_HEIGHT}"', one)
        self.assertIn(f'height="{EMPTY_GARDEN_HEIGHT}"', four)

    def test_each_commit_gets_one_nested_plant_tagged_with_its_hash(self):
        commits = [TINY_COMMIT, TYPICAL_COMMIT, HUGE_COMMIT]
        svg = compose_garden_svg(commits)
        for commit in commits:
            self.assertIn(f'data-commit="{commit.commit_hash[:8]}"', svg)
        self.assertEqual(svg.count("data-commit="), len(commits))

    def test_plants_are_positioned_left_to_right_in_commit_order(self):
        commits = [TINY_COMMIT, TYPICAL_COMMIT, HUGE_COMMIT]
        svg = compose_garden_svg(commits)
        positions = [svg.index(f'data-commit="{c.commit_hash[:8]}"') for c in commits]
        self.assertEqual(positions, sorted(positions))

    def test_single_plant_garden_uses_plant_canvas_dimensions(self):
        svg = compose_garden_svg([TYPICAL_COMMIT])
        self.assertIn(f'width="{CANVAS_WIDTH}"', svg)  # the nested plant <svg>
        self.assertIn(f'height="{CANVAS_HEIGHT}"', svg)


if __name__ == "__main__":
    unittest.main()
