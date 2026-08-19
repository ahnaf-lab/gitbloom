"""Marker-based README auto-update: keep an embedded garden preview in sync.

``gitbloom render`` (see :mod:`gitbloom.render`) regenerates ``garden.svg``
and then looks for a pair of HTML comment markers in the repo's
``README.md``::

    <!-- gitbloom:start -->
    ...anything...
    <!-- gitbloom:end -->

Whatever sits between the markers is replaced with a single Markdown image
reference to the freshly-built garden. Pasting the two marker comments once
is all a user has to do to opt a README in; every later render keeps the
image reference in sync without touching anything else in the file.

Design notes:
  * A missing README or missing markers is *not* an error. Most repos will
    not have opted in, and ``gitbloom render`` should still succeed and
    write ``garden.svg`` regardless. Callers get a :class:`SyncStatus` back
    describing what happened instead of an exception, so the CLI can report
    it without a try/except for what is actually the common case.
  * Only the text between the markers is touched. Everything else in the
    README -- including the markers themselves -- is left byte-for-byte
    identical, so this is safe to run against a real README with existing
    content above and below the block.
  * The write is skipped entirely if the replacement would not change the
    file, so running ``gitbloom render`` twice in a row does not touch the
    file's mtime or produce a spurious diff.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

START_MARKER = "<!-- gitbloom:start -->"
END_MARKER = "<!-- gitbloom:end -->"

# DOTALL + non-greedy so this matches exactly one start..end span, leaving
# everything before the first START_MARKER and after the matched END_MARKER
# alone (including any later, unrelated marker pairs).
_MARKER_RE = re.compile(
    re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER), re.DOTALL
)


class SyncStatus(Enum):
    NO_README = "no_readme"
    NO_MARKERS = "no_markers"
    UNCHANGED = "unchanged"
    UPDATED = "updated"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class SyncResult:
    status: SyncStatus
    readme_path: Path | None = None

    @property
    def updated(self) -> bool:
        return self.status is SyncStatus.UPDATED


def _block(image_relpath: str) -> str:
    return f"{START_MARKER}\n![garden]({image_relpath})\n{END_MARKER}"


def sync_readme(repo_path: str = ".", image_relpath: str = "garden.svg") -> SyncResult:
    """Update the marker block in ``repo_path``/README.md to reference ``image_relpath``.

    Returns a :class:`SyncResult` describing what happened. Never raises for
    the "nothing to do" cases (no README, no markers present) -- those are
    normal, expected states for a repo that has not opted in to the preview.
    """
    readme_path = Path(repo_path) / "README.md"
    if not readme_path.exists():
        return SyncResult(SyncStatus.NO_README)

    original = readme_path.read_text()
    if START_MARKER not in original or END_MARKER not in original:
        return SyncResult(SyncStatus.NO_MARKERS, readme_path)

    updated = _MARKER_RE.sub(_block(image_relpath), original, count=1)
    if updated == original:
        return SyncResult(SyncStatus.UNCHANGED, readme_path)

    readme_path.write_text(updated)
    return SyncResult(SyncStatus.UPDATED, readme_path)
