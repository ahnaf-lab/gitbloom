"""Add/remove the ``post-commit`` hook that keeps ``garden.svg`` fresh.

The hook itself does almost nothing: it shells out to ``python3 -m
gitbloom.build --quiet`` (see :mod:`gitbloom.build`), which reads the repo's
own commit history and rewrites ``garden.svg`` at the top of the working
tree. Git always runs hooks with the working tree root as the current
directory, so the hook script needs no path arguments.

Safety notes:
  * The hook file is only ever written by, or removed by, this module when a
    marker comment it wrote is present. A pre-existing ``post-commit`` hook
    that gitbloom did not create is never overwritten or deleted — callers
    get :class:`HookConflictError` instead, unless ``force=True``.
  * Locating the hooks directory shells out to the real ``git`` binary with
    an argv list (never ``shell=True``), the same pattern used in
    :mod:`gitbloom.extractor`.
"""

from __future__ import annotations

import stat
import subprocess
import sys
from pathlib import Path

MARKER = "# gitbloom:post-commit-hook"

HOOK_SCRIPT = f"""#!/bin/sh
{MARKER}
# Installed by `gitbloom install`; remove with `gitbloom uninstall`.
# Regenerates garden.svg from the repo's current commit history.
exec python3 -m gitbloom.build --quiet
"""


class NotAGitRepoError(RuntimeError):
    """Raised when ``repo_path`` is not inside a git repository."""


class HookConflictError(RuntimeError):
    """Raised when a non-gitbloom ``post-commit`` hook already exists."""


def _git_dir(repo_path: str) -> Path:
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise NotAGitRepoError("git executable not found") from exc

    if result.returncode != 0:
        raise NotAGitRepoError(
            f"{repo_path} is not a git repository: {result.stderr.strip()}"
        )

    git_dir = Path(result.stdout.strip())
    if not git_dir.is_absolute():
        git_dir = Path(repo_path) / git_dir
    return git_dir


def hook_path(repo_path: str = ".") -> Path:
    """Return the path ``post-commit`` hook would live at for ``repo_path``."""
    return _git_dir(repo_path) / "hooks" / "post-commit"


def is_installed(repo_path: str = ".") -> bool:
    """True if gitbloom's own ``post-commit`` hook is currently installed."""
    path = hook_path(repo_path)
    if not path.exists():
        return False
    return MARKER in path.read_text()


def install_hook(repo_path: str = ".", force: bool = False) -> Path:
    """Write the ``post-commit`` hook, returning the path written to.

    If a hook already exists at that path:
      * it is left alone and :class:`HookConflictError` is raised, unless
        it is gitbloom's own hook (already installed -> no-op) or
        ``force=True`` (any existing hook is replaced).
    """
    path = hook_path(repo_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        existing = path.read_text()
        if MARKER in existing:
            return path  # already installed; nothing to do
        if not force:
            raise HookConflictError(
                f"{path} already exists and was not created by gitbloom "
                "(pass force=True to overwrite)"
            )

    path.write_text(HOOK_SCRIPT)
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def uninstall_hook(repo_path: str = ".") -> bool:
    """Remove gitbloom's ``post-commit`` hook if present.

    Returns ``True`` if a hook was removed, ``False`` if there was nothing
    to remove. Raises :class:`HookConflictError` if a ``post-commit`` hook
    exists but was not created by gitbloom — it is left untouched.
    """
    path = hook_path(repo_path)
    if not path.exists():
        return False

    if MARKER not in path.read_text():
        raise HookConflictError(
            f"{path} exists but was not created by gitbloom; not removing it"
        )

    path.unlink()
    return True


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    force = "--force" in argv
    positional = [a for a in argv if a != "--force"]
    action = positional[0] if positional else "install"
    repo_path = positional[1] if len(positional) > 1 else "."

    try:
        if action == "install":
            path = install_hook(repo_path, force=force)
            print(f"installed post-commit hook at {path}")
        elif action == "uninstall":
            removed = uninstall_hook(repo_path)
            print("removed post-commit hook" if removed else "no gitbloom hook installed")
        else:
            print(f"error: unknown action {action!r} (expected install/uninstall)", file=sys.stderr)
            return 2
    except (NotAGitRepoError, HookConflictError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
