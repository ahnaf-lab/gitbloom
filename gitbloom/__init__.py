"""gitbloom: turn a git commit history into a procedurally grown garden."""

from .build import rebuild_garden
from .extractor import CommitStats, GitLogError, get_commit_stats
from .garden import compose_garden_svg
from .install import HookConflictError, install_hook, is_installed, uninstall_hook
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
    "rebuild_garden",
    "install_hook",
    "uninstall_hook",
    "is_installed",
    "HookConflictError",
]
