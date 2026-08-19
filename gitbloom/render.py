"""``gitbloom render``: rebuild garden.svg and sync the README's marker block.

This is the batteries-included counterpart to ``gitbloom build``: it does
what a human actually wants when they type ``gitbloom render`` -- an
up-to-date ``garden.svg`` *and*, if they have opted in with the marker
comments documented in :mod:`gitbloom.readme`, an up-to-date README preview
-- in one call.

The post-commit hook installed by :mod:`gitbloom.install` deliberately keeps
calling the smaller :mod:`gitbloom.build` module instead of this one: a hook
runs after every single commit and should stay cheap and side-effect
minimal (just the SVG). README syncing is for a human to run deliberately,
or from CI, not silently on every commit.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from .build import GitLogError, NotAGitRepoError, rebuild_garden
from .readme import SyncResult, SyncStatus, sync_readme


@dataclass(frozen=True)
class RenderResult:
    garden_path: Path
    readme: SyncResult


def render(repo_path: str = ".", update_readme: bool = True) -> RenderResult:
    """Rebuild ``garden.svg`` and, unless ``update_readme`` is False, sync README.md.

    Raises the same errors as :func:`gitbloom.build.rebuild_garden` --
    :class:`~gitbloom.build.NotAGitRepoError` or
    :class:`~gitbloom.extractor.GitLogError`.
    """
    garden_path = rebuild_garden(repo_path)
    if update_readme:
        readme_result = sync_readme(repo_path)
    else:
        readme_result = SyncResult(SyncStatus.SKIPPED)
    return RenderResult(garden_path, readme_result)


# Human-readable status line for each SyncStatus, shared by this module's
# own CLI entry point and gitbloom.cli's "render" subcommand.
STATUS_MESSAGES = {
    SyncStatus.NO_README: "no README.md found; skipped",
    SyncStatus.NO_MARKERS: "README.md has no gitbloom markers; skipped",
    SyncStatus.UNCHANGED: "README.md already up to date",
    SyncStatus.UPDATED: "updated README.md",
    SyncStatus.SKIPPED: "README sync skipped (--no-readme)",
}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    quiet = "--quiet" in argv or "-q" in argv
    update_readme = "--no-readme" not in argv
    positional = [a for a in argv if a not in ("--quiet", "-q", "--no-readme")]
    repo_path = positional[0] if positional else "."

    try:
        result = render(repo_path, update_readme=update_readme)
    except (NotAGitRepoError, GitLogError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not quiet:
        print(f"wrote {result.garden_path}")
        print(STATUS_MESSAGES[result.readme.status])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
