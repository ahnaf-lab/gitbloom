"""Regenerate ``garden.svg`` for a repository's current commit history.

This is the payload the post-commit hook (:mod:`gitbloom.install`) runs after
every commit: read every commit's stats with :mod:`gitbloom.extractor`,
compose them into one garden with :mod:`gitbloom.garden`, and write the
result to ``garden.svg`` at the top of the working tree — the same place a
user would embed it from in a README.

Kept separate from :mod:`gitbloom.install` so the hook script itself can stay
a one-line call into this module: the hook only needs to know *that* the
garden should be rebuilt, not *how*.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .extractor import GitLogError, get_commit_stats
from .garden import compose_garden_svg

GARDEN_FILENAME = "garden.svg"


class NotAGitRepoError(RuntimeError):
    """Raised when ``repo_path`` is not inside a git working tree."""


def _toplevel(repo_path: str) -> Path:
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise NotAGitRepoError("git executable not found") from exc

    if result.returncode != 0:
        raise NotAGitRepoError(
            f"{repo_path} is not inside a git working tree: {result.stderr.strip()}"
        )
    return Path(result.stdout.strip())


def rebuild_garden(repo_path: str = ".") -> Path:
    """Regenerate ``garden.svg`` at the top of ``repo_path``'s working tree.

    Returns the path the file was written to. Raises :class:`NotAGitRepoError`
    if ``repo_path`` is not a git working tree, or :class:`~gitbloom.extractor.
    GitLogError` if ``git log`` itself fails.
    """
    toplevel = _toplevel(repo_path)
    commits = get_commit_stats(str(toplevel))
    svg = compose_garden_svg(commits)

    out_path = toplevel / GARDEN_FILENAME
    out_path.write_text(svg)
    return out_path


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    quiet = "--quiet" in argv or "-q" in argv
    positional = [a for a in argv if a not in ("--quiet", "-q")]
    repo_path = positional[0] if positional else "."

    try:
        out_path = rebuild_garden(repo_path)
    except (NotAGitRepoError, GitLogError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not quiet:
        print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
