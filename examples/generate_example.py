#!/usr/bin/env python3
"""Regenerate examples/garden.svg from a small, fully deterministic fixture repo.

``examples/garden.svg`` is the preview embedded in this project's own
README. It is not built from *this* repository's real history (that would
make the README's own example change every time gitbloom's own history
grows, which is confusing rather than illustrative); instead it comes from a
small throwaway repo built right here with fixed commit content, author
identity and commit dates.

Every one of those inputs feeds into the commit hash, and the hash is what
:mod:`gitbloom.plant` uses to derive hue and petal rotation, so fixing all of
them is what makes the output byte-for-byte reproducible on any machine --
the same property golden-file tests in ``tests/`` rely on for the plant and
garden renderers themselves. ``tests/test_examples.py`` re-runs this exact
fixture and asserts it still matches the checked-in SVG, so a change to the
extractor, plant generator or composer that would silently alter the example
fails the test suite instead of going unnoticed.

Usage::

    python3 examples/generate_example.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gitbloom.extractor import get_commit_stats
from gitbloom.garden import compose_garden_svg

OUT_PATH = Path(__file__).resolve().parent / "garden.svg"

# (path relative to repo root, file content, commit subject) -- deliberately
# varied churn sizes and insertion/deletion ratios so the four plants in the
# example look distinct from one another.
FIXTURE_COMMITS = [
    ("README.md", "# demo\n", "docs: start the demo project"),
    (
        "app.py",
        "def main():\n    pass\n",
        "feat: add application entrypoint",
    ),
    (
        "app.py",
        "def main():\n    print('hello')\n\n\ndef helper():\n    return 42\n",
        "feat: add helper function",
    ),
    (
        "tests/test_app.py",
        "def test_helper():\n    assert True\n",
        "test: cover helper behaviour",
    ),
]

_IDENTITY = {
    "GIT_AUTHOR_NAME": "Gitbloom Example",
    "GIT_AUTHOR_EMAIL": "example@gitbloom.invalid",
    "GIT_COMMITTER_NAME": "Gitbloom Example",
    "GIT_COMMITTER_EMAIL": "example@gitbloom.invalid",
}


def _run(cmd: list[str], cwd: Path, env: dict) -> None:
    subprocess.run(cmd, cwd=cwd, env=env, check=True, capture_output=True, text=True)


def build_fixture_repo(repo: Path) -> None:
    """Create the fixture repo's commits at ``repo``, a fresh empty directory."""
    base_env = {**os.environ, **_IDENTITY}
    _run(["git", "init", "-q"], repo, base_env)
    _run(["git", "config", "user.email", _IDENTITY["GIT_AUTHOR_EMAIL"]], repo, base_env)
    _run(["git", "config", "user.name", _IDENTITY["GIT_AUTHOR_NAME"]], repo, base_env)

    for i, (relpath, content, message) in enumerate(FIXTURE_COMMITS):
        path = repo / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

        commit_env = dict(base_env)
        stamp = f"2024-01-{i + 1:02d}T12:00:00"
        commit_env["GIT_AUTHOR_DATE"] = stamp
        commit_env["GIT_COMMITTER_DATE"] = stamp

        _run(["git", "add", relpath], repo, commit_env)
        _run(["git", "commit", "-q", "-m", message], repo, commit_env)


def generate_svg() -> str:
    """Build the fixture repo in a temp directory and return its garden SVG."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        build_fixture_repo(repo)
        commits = get_commit_stats(str(repo))
        return compose_garden_svg(commits)


def main() -> int:
    OUT_PATH.write_text(generate_svg())
    print(f"wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
