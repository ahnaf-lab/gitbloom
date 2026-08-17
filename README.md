# gitbloom

Turn your commit history into a procedurally grown garden: each commit
becomes a deterministic SVG plant shaped by its diff stats, composed into one
image that grows with the repo. Installs as a `post-commit` hook so
`garden.svg` regenerates itself and can be embedded in a README.

This milestone builds the data layer: a safe extractor that turns
`git log --numstat` into structured per-commit stats (files changed,
insertions, deletions, message length). Later milestones turn those stats
into plants and compose the garden image.

## Install

Requires Python 3.9+ and `git` on `PATH`. No third-party dependencies —
everything used (`subprocess`, `dataclasses`, `json`) is in the standard
library, which is enough to parse `git log` output safely.

```bash
git clone <this-repo-url>
cd gitbloom
```

Nothing to build or `pip install` for this milestone; the package is used
directly from source.

## Usage

As a library:

```python
from gitbloom.extractor import get_commit_stats

for commit in get_commit_stats("."):
    print(commit.commit_hash[:8], commit.files, commit.insertions,
          commit.deletions, commit.message_length)
```

As a CLI (prints JSON, one object per commit, oldest first):

```bash
python3 -m gitbloom.extractor /path/to/repo
```

`get_commit_stats()` shells out to the real `git` binary via
`subprocess.run` with an argument list (never a shell string), and rejects
any `rev_range` that looks like a git option (starts with `-`) to prevent
argument injection.

## Status

Built autonomously with [Claude Code](https://claude.com/claude-code), one
gated milestone at a time. Every change here is required to pass a real test
suite before it is committed.
