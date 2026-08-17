"""Safely extract per-commit stats from ``git log --numstat``.

This module shells out to the real ``git`` binary (never a shell) to read
``files changed / insertions / deletions / message length`` for every commit
in a repository. Those four numbers are the seed data gitbloom later turns
into a procedurally grown plant per commit.

Security notes:
  * ``subprocess.run`` is always called with a list of argv, never
    ``shell=True`` and never a string command, so there is no shell
    metacharacter injection.
  * ``rev_range`` is validated to reject anything that looks like a git
    option (a leading ``-``), so a caller cannot smuggle flags such as
    ``--upload-pack=...`` into the argument list.
  * Commit subjects are read as opaque text; they are never evaluated,
    executed, or used to build further shell commands.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict, dataclass

# Unlikely-to-collide separators so a commit header can be split back apart
# even if the subject line itself contains tabs or stray control bytes.
_RECORD_SEP = "\x1e"
_FIELD_SEP = "\x1f"
_PRETTY_FORMAT = f"{_RECORD_SEP}%H{_FIELD_SEP}%an{_FIELD_SEP}%at{_FIELD_SEP}%s"


class GitLogError(RuntimeError):
    """Raised when ``git log`` cannot be run or exits non-zero."""


@dataclass(frozen=True)
class CommitStats:
    """Stats for a single commit, ready to be mapped onto a plant."""

    commit_hash: str
    author: str
    timestamp: int
    subject: str
    message_length: int
    files: int
    insertions: int
    deletions: int

    def to_dict(self) -> dict:
        return asdict(self)


def _validate_rev_range(rev_range: str) -> None:
    if rev_range.strip().startswith("-"):
        raise ValueError(
            "rev_range must not start with '-' (would be parsed as a git option)"
        )


def _parse_numstat_output(raw: str) -> list[CommitStats]:
    commits: list[CommitStats] = []

    for chunk in raw.split(_RECORD_SEP):
        chunk = chunk.strip("\n")
        if not chunk:
            continue

        lines = chunk.split("\n")
        header_fields = lines[0].split(_FIELD_SEP)
        if len(header_fields) != 4:
            # A malformed/unexpected header means we cannot trust this
            # record; skip it rather than guessing at field positions.
            continue

        commit_hash, author, timestamp_str, subject = header_fields

        files = 0
        insertions = 0
        deletions = 0
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            fields = line.split("\t")
            if len(fields) < 3:
                continue
            added, deleted = fields[0], fields[1]
            files += 1
            if added != "-":
                insertions += int(added)
            if deleted != "-":
                deletions += int(deleted)

        try:
            timestamp = int(timestamp_str)
        except ValueError:
            timestamp = 0

        commits.append(
            CommitStats(
                commit_hash=commit_hash,
                author=author,
                timestamp=timestamp,
                subject=subject,
                message_length=len(subject),
                files=files,
                insertions=insertions,
                deletions=deletions,
            )
        )

    return commits


def get_commit_stats(
    repo_path: str = ".",
    rev_range: str | None = None,
    oldest_first: bool = True,
) -> list[CommitStats]:
    """Return :class:`CommitStats` for every commit in ``repo_path``.

    Args:
        repo_path: path to a git repository (passed to ``git -C``).
        rev_range: optional git revision range (e.g. ``"main"`` or
            ``"abc123..HEAD"``). Must not start with ``-``.
        oldest_first: gitbloom grows a garden over time, so by default
            commits are returned oldest-first (git's own default is
            newest-first).

    Raises:
        ValueError: if ``rev_range`` looks like a git option.
        GitLogError: if git is missing or the log command fails.
    """
    if rev_range is not None:
        _validate_rev_range(rev_range)

    cmd = [
        "git",
        "-C",
        repo_path,
        "log",
        "--numstat",
        f"--pretty=format:{_PRETTY_FORMAT}",
    ]
    if rev_range is not None:
        cmd.append(rev_range)
        cmd.append("--")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except FileNotFoundError as exc:
        raise GitLogError("git executable not found") from exc

    if result.returncode != 0:
        raise GitLogError(
            f"git log failed (exit {result.returncode}): {result.stderr.strip()}"
        )

    commits = _parse_numstat_output(result.stdout)
    if oldest_first:
        commits.reverse()
    return commits


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    repo_path = argv[0] if argv else "."

    try:
        commits = get_commit_stats(repo_path)
    except (GitLogError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps([c.to_dict() for c in commits], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
