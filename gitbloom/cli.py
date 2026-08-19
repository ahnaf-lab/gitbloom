"""The ``gitbloom`` command: install/uninstall the hook, or build once by hand.

Thin argparse wrapper around :mod:`gitbloom.install` and :mod:`gitbloom.build`
so both are usable as a library without ever going through argv parsing (see
their own ``main()`` functions, kept for standalone ``python3 -m`` use).
"""

from __future__ import annotations

import argparse
import sys

from .build import GitLogError, NotAGitRepoError as BuildNotAGitRepoError, rebuild_garden
from .install import (
    HookConflictError,
    NotAGitRepoError as InstallNotAGitRepoError,
    install_hook,
    uninstall_hook,
)
from .render import (
    NotAGitRepoError as RenderNotAGitRepoError,
    STATUS_MESSAGES as _README_STATUS_MESSAGES,
    render,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gitbloom", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_p = subparsers.add_parser(
        "install", help="add the post-commit hook that regenerates garden.svg"
    )
    install_p.add_argument("repo", nargs="?", default=".")
    install_p.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing post-commit hook not created by gitbloom",
    )

    uninstall_p = subparsers.add_parser(
        "uninstall", help="remove gitbloom's post-commit hook"
    )
    uninstall_p.add_argument("repo", nargs="?", default=".")

    build_p = subparsers.add_parser(
        "build", help="regenerate garden.svg once, without touching hooks"
    )
    build_p.add_argument("repo", nargs="?", default=".")
    build_p.add_argument("--quiet", "-q", action="store_true")

    render_p = subparsers.add_parser(
        "render",
        help="regenerate garden.svg and sync any <!-- gitbloom:start/end --> "
        "block in README.md",
    )
    render_p.add_argument("repo", nargs="?", default=".")
    render_p.add_argument("--quiet", "-q", action="store_true")
    render_p.add_argument(
        "--no-readme",
        action="store_true",
        help="only write garden.svg; do not touch README.md",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    args = _build_parser().parse_args(argv)

    if args.command == "install":
        try:
            path = install_hook(args.repo, force=args.force)
        except (InstallNotAGitRepoError, HookConflictError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"installed post-commit hook at {path}")
        return 0

    if args.command == "uninstall":
        try:
            removed = uninstall_hook(args.repo)
        except (InstallNotAGitRepoError, HookConflictError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print("removed post-commit hook" if removed else "no gitbloom hook installed")
        return 0

    if args.command == "build":
        try:
            out_path = rebuild_garden(args.repo)
        except (BuildNotAGitRepoError, GitLogError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if not args.quiet:
            print(f"wrote {out_path}")
        return 0

    if args.command == "render":
        try:
            result = render(args.repo, update_readme=not args.no_readme)
        except (RenderNotAGitRepoError, GitLogError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if not args.quiet:
            print(f"wrote {result.garden_path}")
            print(_README_STATUS_MESSAGES[result.readme.status])
        return 0

    return 2  # unreachable: argparse enforces a valid subcommand


if __name__ == "__main__":
    raise SystemExit(main())
