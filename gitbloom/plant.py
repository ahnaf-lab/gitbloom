"""Turn a single commit's stats into a deterministic SVG plant.

This module is a pure function: the same :class:`~gitbloom.extractor.CommitStats`
always renders to the exact same SVG string, byte for byte. That determinism is
what makes ``garden.svg`` reproducible from a commit history and what makes the
golden-file tests in ``tests/test_plant.py`` meaningful.

Mapping from stats to shape, all deliberately simple and monotonic:

* ``insertions + deletions`` (total churn)  -> stem height. Bigger changes grow
  taller plants.
* ``files``                                 -> number of leaves, one per file
  touched, capped so a 200-file commit doesn't blow the canvas.
* ``message_length``                        -> number of flower petals. A
  longer commit message blooms a fuller flower.
* ``deletions / (insertions + deletions)``  -> how "wilted" (brown vs. green)
  the leaves are. A commit that is mostly deletions grows a browner plant.
* ``commit_hash``                           -> flower hue and a small stable
  rotation offset for the petals, so two commits with identical stats still
  look like different plants.

No randomness is used anywhere. Anything that needs to vary "randomly" per
commit is derived from a hash of the commit hash instead, so it is the same on
every run.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

from .extractor import CommitStats

CANVAS_WIDTH = 160
CANVAS_HEIGHT = 220
GROUND_Y = 200
STEM_X = CANVAS_WIDTH // 2

MIN_STEM_HEIGHT = 30
MAX_STEM_HEIGHT = 160

MIN_LEAVES = 0
MAX_LEAVES = 6

MIN_PETALS = 3
MAX_PETALS = 12

FLOWER_RADIUS = 6
PETAL_RADIUS = 5
PETAL_ORBIT = 11


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def _seed(commit_hash: str) -> int:
    """A stable, non-cryptographic integer derived from a commit hash.

    Used only to pick a hue and rotation so plants with identical stats but
    different commits don't render identically. Not used for anything
    security-sensitive.
    """
    digest = hashlib.sha256(commit_hash.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


@dataclass(frozen=True)
class PlantParams:
    """Fully-resolved, deterministic parameters for one plant.

    Splitting derivation (stats -> numbers) from rendering (numbers -> SVG
    text) keeps each half independently testable.
    """

    stem_height: int
    leaf_count: int
    petal_count: int
    wilt_percent: int  # 0 (lush green) .. 100 (fully brown)
    hue: int  # 0..359
    rotation: int  # 0..359, petal ring rotation offset

    def to_dict(self) -> dict:
        return {
            "stem_height": self.stem_height,
            "leaf_count": self.leaf_count,
            "petal_count": self.petal_count,
            "wilt_percent": self.wilt_percent,
            "hue": self.hue,
            "rotation": self.rotation,
        }


def derive_plant_params(stats: CommitStats) -> PlantParams:
    """Pure function: :class:`CommitStats` -> :class:`PlantParams`."""

    churn = stats.insertions + stats.deletions
    stem_height = _clamp(MIN_STEM_HEIGHT + 4 * churn, MIN_STEM_HEIGHT, MAX_STEM_HEIGHT)

    leaf_count = _clamp(stats.files, MIN_LEAVES, MAX_LEAVES)

    petal_count = _clamp(
        MIN_PETALS + stats.message_length // 6, MIN_PETALS, MAX_PETALS
    )

    if churn > 0:
        wilt_percent = _clamp(round(100 * stats.deletions / churn), 0, 100)
    else:
        wilt_percent = 0

    seed = _seed(stats.commit_hash) if stats.commit_hash else 0
    hue = seed % 360
    rotation = (seed // 360) % 360

    return PlantParams(
        stem_height=stem_height,
        leaf_count=leaf_count,
        petal_count=petal_count,
        wilt_percent=wilt_percent,
        hue=hue,
        rotation=rotation,
    )


def _leaf_color(wilt_percent: int) -> str:
    """Interpolate integer-only from lush green to dead brown."""
    green = (34, 139, 34)
    brown = (139, 90, 43)
    t = wilt_percent / 100
    r = round(green[0] + (brown[0] - green[0]) * t)
    g = round(green[1] + (brown[1] - green[1]) * t)
    b = round(green[2] + (brown[2] - green[2]) * t)
    return f"rgb({r},{g},{b})"


def _render_stem(params: PlantParams) -> str:
    top_y = GROUND_Y - params.stem_height
    return (
        f'<line x1="{STEM_X}" y1="{GROUND_Y}" x2="{STEM_X}" y2="{top_y}" '
        f'stroke="#3a5f0b" stroke-width="3" stroke-linecap="round"/>'
    )

def _render_leaves(params: PlantParams) -> list[str]:
    if params.leaf_count == 0:
        return []
    color = _leaf_color(params.wilt_percent)
    top_y = GROUND_Y - params.stem_height
    # Spread leaves evenly along the stem, alternating left and right.
    step = params.stem_height / (params.leaf_count + 1)
    leaves = []
    for i in range(params.leaf_count):
        y = round(GROUND_Y - step * (i + 1))
        side = 1 if i % 2 == 0 else -1
        cx = STEM_X + side * 10
        leaves.append(
            f'<ellipse cx="{cx}" cy="{y}" rx="9" ry="5" fill="{color}" '
            f'transform="rotate({side * 30} {cx} {y})"/>'
        )
    return leaves


def _render_flower(params: PlantParams) -> list[str]:
    cx = STEM_X
    cy = GROUND_Y - params.stem_height
    petal_fill = f"hsl({params.hue},70%,60%)"
    center_fill = f"hsl({(params.hue + 40) % 360},80%,50%)"

    parts = []
    for i in range(params.petal_count):
        angle_deg = params.rotation + i * (360 / params.petal_count)
        angle_rad = math.radians(angle_deg)
        px = round(cx + PETAL_ORBIT * math.cos(angle_rad))
        py = round(cy + PETAL_ORBIT * math.sin(angle_rad))
        parts.append(
            f'<circle cx="{px}" cy="{py}" r="{PETAL_RADIUS}" fill="{petal_fill}"/>'
        )
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{FLOWER_RADIUS}" fill="{center_fill}"/>')
    return parts


def render_plant_svg(
    params: PlantParams,
    commit_hash: str = "",
    x: int | None = None,
    y: int | None = None,
) -> str:
    """Pure function: :class:`PlantParams` -> an SVG document string.

    ``x``/``y``, when given, are emitted as attributes on the outer ``<svg>``
    tag. That is meaningless for a standalone document but lets this same
    element be nested inside a parent ``<svg>`` (as :mod:`gitbloom.garden`
    does) and positioned there without any extra wrapper element. Omitting
    them (the default) reproduces the exact standalone-document output the
    golden-file tests in ``tests/test_plant.py`` pin.
    """

    body_parts = [_render_stem(params)]
    body_parts.extend(_render_leaves(params))
    body_parts.extend(_render_flower(params))
    body = "".join(body_parts)

    label = commit_hash[:8] if commit_hash else "unknown"
    position = ""
    if x is not None:
        position += f' x="{x}"'
    if y is not None:
        position += f' y="{y}"'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_WIDTH}" '
        f'height="{CANVAS_HEIGHT}" viewBox="0 0 {CANVAS_WIDTH} {CANVAS_HEIGHT}"{position} '
        f'data-commit="{label}">{body}</svg>'
    )


def generate_plant_svg(stats: CommitStats) -> str:
    """Pure function: :class:`CommitStats` -> a deterministic SVG plant string.

    Calling this twice with equal ``stats`` always produces the identical
    string; nothing here reads the clock, the filesystem, or any random
    source.
    """
    params = derive_plant_params(stats)
    return render_plant_svg(params, commit_hash=stats.commit_hash)
