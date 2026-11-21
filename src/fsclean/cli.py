"""Command-line interface for fsclean."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .core import Move, apply_moves, format_bytes, plan_moves


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fsclean",
        description=(
            "Tidy a messy folder (e.g. Downloads) by moving loose files into "
            "category folders. Dry run by default; nothing moves without --apply."
        ),
    )
    parser.add_argument("path", nargs="?", default=".", help="folder to tidy (default: current directory)")
    parser.add_argument(
        "-a", "--apply", action="store_true",
        help="actually move the files (default is a dry-run preview)",
    )
    parser.add_argument(
        "-d", "--dest", metavar="DIR", default=None,
        help="move into category folders under DIR instead of PATH",
    )
    parser.add_argument(
        "-r", "--rule", action="append", metavar="EXT=DIR",
        help="route an extension to a folder, e.g. 'log=logs' (repeatable, wins over builtins)",
    )
    parser.add_argument(
        "-e", "--exclude", action="append", metavar="PATTERN",
        help="skip files matching an fnmatch pattern such as '*.tmp' (repeatable)",
    )
    parser.add_argument("-V", "--version", action="version", version=f"fsclean {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        moves, unknown = plan_moves(
            args.path, rules=args.rule or (), exclude=args.exclude or (), dest=args.dest,
        )
    except (NotADirectoryError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    root = Path(args.path).absolute()
    total = sum(m.size for m in moves)
    grouped: dict[str, list[Move]] = {}
    for move in moves:
        grouped.setdefault(move.category, []).append(move)

    verb = "Moving" if args.apply else "Would move"
    suffix = "" if args.apply else "  (dry run - add --apply to move for real)"
    print(f"{verb}: {len(moves)} file(s), {format_bytes(total)}{suffix}")
    for category in sorted(grouped):
        print(f"\n{category} ({len(grouped[category])}):")
        for move in grouped[category]:
            print(f"  {move.src.name}  ->  {category}/{move.dest.name}")
    if unknown:
        print(f"\nleft in place: {unknown} file(s) with unknown extension")

    if args.apply and moves:
        moved = apply_moves(moves)
        print(f"\nApplied: {moved} file(s) moved.")
    return 0


def run() -> int:
    try:
        return main()
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(run())
