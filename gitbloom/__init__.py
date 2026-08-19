"""gitbloom: turn a git commit history into a procedurally grown garden."""

from .extractor import CommitStats, GitLogError, get_commit_stats
from .garden import compose_garden_svg
from .plant import PlantParams, derive_plant_params, generate_plant_svg, render_plant_svg

__all__ = [
    "CommitStats",
    "GitLogError",
    "get_commit_stats",
    "PlantParams",
    "derive_plant_params",
    "generate_plant_svg",
    "render_plant_svg",
    "compose_garden_svg",
]
