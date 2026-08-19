# gitbloom

Turn your commit history into a procedurally grown garden: each commit
becomes a deterministic SVG plant shaped by its diff stats, composed into one
image that grows with the repo. Installs as a `post-commit` hook so
`garden.svg` regenerates itself and can be embedded in a README.

The data layer is a safe extractor that turns `git log --numstat` into
structured per-commit stats (files changed, insertions, deletions, message
length). The plant generator is a pure function that maps those stats onto a
single deterministic SVG "plant" — stem height from total churn, leaf count
from files touched, petal count from message length, and leaf colour from
the insertions/deletions ratio (greener when a commit adds more than it
removes, browner when it's mostly deletions). Flower hue is derived from the
commit hash, so two commits with identical stats still look like different
plants.

This milestone adds the garden composer: a pure function that lines every
commit's plant up along one ground line into a single `garden.svg` —
oldest commit on the left, newest on the right, so the garden grows to the
right as the repo grows. Layout is deliberately simple and fully
deterministic (fixed, evenly-spaced positions; only each plant's own shape
depends on its commit), so the same commit history always produces the exact
same `garden.svg` bytes. A later milestone wires this up as a `post-commit`
hook so the file regenerates itself.

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

Turning one commit's stats into a plant:

```python
from gitbloom.extractor import get_commit_stats
from gitbloom.plant import generate_plant_svg

commit = get_commit_stats(".")[0]
svg = generate_plant_svg(commit)  # a standalone <svg>...</svg> string
```

`generate_plant_svg()` is a pure function: the same `CommitStats` always
produces the exact same SVG string. Nothing in it reads the clock, the
filesystem, or any random source — anything that needs to vary per commit
(flower hue, petal rotation) is derived from a hash of the commit hash
instead. That determinism is verified by golden-file tests in
`tests/test_plant.py`, which compare fixed sample commits against checked-in
`tests/golden/*.svg` fixtures.

Composing a whole repo's history into one garden:

```python
from gitbloom.extractor import get_commit_stats
from gitbloom.garden import compose_garden_svg

commits = get_commit_stats(".")  # oldest first
svg = compose_garden_svg(commits)  # one standalone <svg>...</svg> garden

with open("garden.svg", "w") as f:
    f.write(svg)
```

`compose_garden_svg()` is a pure function too: it places each commit's plant
at a fixed, evenly-spaced x-offset along one ground line (no stats-dependent
positioning, no collision search), so the garden's width grows by a constant
amount per commit and its height never changes. An empty commit list still
renders a valid (plant-less) garden, so a freshly-initialised repo gets a
usable `garden.svg`. This is verified by golden-file tests in
`tests/test_garden.py` against checked-in `tests/golden_garden/*.svg`
fixtures, covering zero, one, and several commits.

## Status

Built autonomously with [Claude Code](https://claude.com/claude-code), one
gated milestone at a time. Every change here is required to pass a real test
suite before it is committed.
