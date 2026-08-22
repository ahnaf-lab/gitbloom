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

The garden composer lines every commit's plant up along one ground line into
a single `garden.svg` — oldest commit on the left, newest on the right, so
the garden grows to the right as the repo grows. Layout is deliberately
simple and fully deterministic (fixed, evenly-spaced positions; only each
plant's own shape depends on its commit), so the same commit history always
produces the exact same `garden.svg` bytes.

The hook installer adds a `post-commit` hook to a repo that reruns the
extractor + composer after every commit and rewrites `garden.svg` at the top
of the working tree, so the file stays in sync with history automatically.
`gitbloom install` adds it, `gitbloom uninstall` removes it; the installer
never overwrites or deletes a `post-commit` hook it did not create itself —
it refuses instead, unless `--force` is passed.

This milestone adds `gitbloom render`, the command a human (or CI) runs to
regenerate `garden.svg` **and** keep a preview of it embedded in `README.md`
in sync (see "Embedding the garden in your own README" below). It also adds
`examples/garden.svg`, a deterministic example built from a small fixture
repo, so this README can show what a garden looks like without depending on
gitbloom's own (still tiny) commit history:

![example garden](examples/garden.svg)

## Install

Requires Python 3.9+ and `git` on `PATH`. No third-party dependencies —
everything used (`subprocess`, `dataclasses`, `argparse`, `json`) is in the
standard library, which is enough to parse `git log` output, render SVG, and
manage a git hook safely.

```bash
git clone <this-repo-url>
cd gitbloom
pip install -e .
```

`pip install -e .` registers the `gitbloom` command (via the `[project.scripts]`
entry point in `pyproject.toml`) and makes the package importable as
`python3 -m gitbloom...` from anywhere — the installed hook itself runs
`python3 -m gitbloom.build --quiet`, so it needs the package importable, not
just the `gitbloom` command on `PATH`. Without installing, everything is
still usable directly from a checkout by running `python3 -m gitbloom.cli ...`
with this directory's parent on `PYTHONPATH`.

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

Installing the hook so `garden.svg` regenerates on every commit:

```bash
cd /path/to/some/other/repo
gitbloom install          # adds .git/hooks/post-commit
git commit --allow-empty -m "test the hook"
cat garden.svg             # regenerated automatically
gitbloom uninstall        # removes the hook again
```

`gitbloom install` refuses to overwrite a `post-commit` hook it did not
create itself (pass `--force` to replace it anyway), and `gitbloom uninstall`
likewise refuses to delete a hook it does not recognise — both operations are
idempotent and only ever touch a hook carrying gitbloom's own marker comment.
To regenerate `garden.svg` once by hand, without installing anything:

```bash
gitbloom build              # writes garden.svg at the repo root, then exits
```

`gitbloom install`/`uninstall`/`build` all accept an optional repo path
argument (defaulting to `.`) and are covered by `tests/test_install.py`,
`tests/test_build.py` and `tests/test_cli.py`, which install and uninstall
hooks and run full builds against real throwaway git repositories.

### Embedding the garden in your own README

`gitbloom render` does everything `gitbloom build` does — regenerate
`garden.svg` from the current commit history — and then also looks for a
marker block in that repo's own `README.md`:

```markdown
<!-- gitbloom:start -->
<!-- gitbloom:end -->
```

Paste those two HTML comments anywhere in your README once. Every time you
run `gitbloom render` after that, whatever sits between them is replaced
with `![garden](garden.svg)`; everything else in the file, including the
markers themselves, is left untouched. Pass `--no-readme` to only rebuild
`garden.svg` without touching `README.md`:

```bash
gitbloom render              # rebuilds garden.svg, syncs README.md if it has markers
gitbloom render --no-readme  # rebuilds garden.svg only
```

`sync_readme()` in `gitbloom/readme.py` is safe to call on a README that has
no markers or does not exist yet — it reports that nothing needed doing
rather than raising, so `gitbloom render` always succeeds at writing
`garden.svg` regardless of whether a project has opted in to the embed. This
is covered by `tests/test_readme.py` and `tests/test_render.py`.

### Example

`examples/garden.svg` (embedded above) is generated from a small, fully
deterministic fixture repo — fixed file contents, author identity and commit
dates, so the commit hashes gitbloom's plant generator derives colour and
shape from never change between runs or machines:

```bash
python3 examples/generate_example.py
```

`tests/test_examples.py` re-runs the same fixture and asserts the result
still matches the checked-in SVG byte-for-byte, so a change to the
extractor, plant generator or garden composer that would silently alter the
example fails the test suite instead of the README quietly going stale.

## Status

Built autonomously, one
gated milestone at a time. Every change here is required to pass a real test
suite before it is committed.
