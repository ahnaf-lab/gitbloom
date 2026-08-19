"""Compose every commit's plant into one deterministic, growing garden.svg.

This module is the packing/layout half of gitbloom: :mod:`gitbloom.extractor`
turns a repo into :class:`~gitbloom.extractor.CommitStats`, :mod:`gitbloom.plant`
turns one commit's stats into one plant, and this module lines every plant up
along a single ground line into one wide SVG "garden" — oldest commit on the
left, newest on the right, so the garden reads left-to-right the same way the
repo's history does.

Layout is intentionally simple and fully deterministic:

* Plants are placed at fixed, evenly-spaced x-offsets. There is no bin
  packing, no collision search, nothing stats-dependent about *position* —
  only each plant's own shape depends on its commit.
* Because the garden always grows by ``PLANT_SPACING`` per commit, the whole
  image gets wider (never taller) as the repo grows, which is what makes it
  natural to embed in a README inside a horizontally scrollable container.
* Each plant is nested as a child ``<svg>`` with its own ``x``, so no
  coordinate inside :mod:`gitbloom.plant` has to know about composition —
  a plant is still rendered exactly as it would be standalone.

Nothing here reads the clock, the filesystem, or any random source: the same
list of :class:`~gitbloom.extractor.CommitStats` always produces the exact
same ``garden.svg`` bytes, which is what the golden-file tests in
``tests/test_garden.py`` check.
"""

from __future__ import annotations

from .extractor import CommitStats
from .plant import CANVAS_HEIGHT, CANVAS_WIDTH, derive_plant_params, render_plant_svg

# Horizontal distance between one plant's origin and the next. Deliberately
# smaller than CANVAS_WIDTH so neighbouring plants overlap a little at the
# base, the way real garden foliage does, rather than sitting in isolated
# boxes with visible gaps.
PLANT_SPACING = 90

MARGIN_X = 20
MARGIN_TOP = 16
MARGIN_BOTTOM = 20

SKY_COLOR = "#eaf6ff"
GROUND_COLOR = "#6b8e4e"
GROUND_HEIGHT = 14

# The ground line each plant is drawn against, in the *plant's own* local
# coordinate system (see gitbloom.plant.GROUND_Y). Used to line up the strip
# of ground drawn behind every plant with where their stems actually end.
_PLANT_GROUND_Y = 200

EMPTY_GARDEN_WIDTH = MARGIN_X * 2 + CANVAS_WIDTH
EMPTY_GARDEN_HEIGHT = MARGIN_TOP + CANVAS_HEIGHT + MARGIN_BOTTOM


def _garden_width(commit_count: int) -> int:
    if commit_count == 0:
        return EMPTY_GARDEN_WIDTH
    return MARGIN_X * 2 + CANVAS_WIDTH + PLANT_SPACING * (commit_count - 1)


def _background(width: int, height: int) -> str:
    ground_y = MARGIN_TOP + _PLANT_GROUND_Y
    return (
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="{SKY_COLOR}"/>'
        f'<rect x="0" y="{ground_y}" width="{width}" height="{GROUND_HEIGHT}" '
        f'fill="{GROUND_COLOR}"/>'
    )


def compose_garden_svg(commits: list[CommitStats]) -> str:
    """Pure function: every commit's stats -> one deterministic garden SVG.

    ``commits`` should be oldest-first (the order :func:`gitbloom.extractor.
    get_commit_stats` returns by default), so the garden grows left-to-right
    in the same direction as the repo's history. An empty list renders a
    bare garden (sky and ground, no plants) rather than erroring, so a
    freshly-initialised repo still gets a valid ``garden.svg``.
    """

    width = _garden_width(len(commits))
    height = EMPTY_GARDEN_HEIGHT

    parts = [_background(width, height)]
    for i, stats in enumerate(commits):
        params = derive_plant_params(stats)
        x = MARGIN_X + i * PLANT_SPACING
        parts.append(
            render_plant_svg(params, commit_hash=stats.commit_hash, x=x, y=MARGIN_TOP)
        )
    body = "".join(parts)

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" data-plant-count="{len(commits)}">{body}</svg>'
    )
