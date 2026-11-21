"""Categorize loose files in a directory and plan where they should move."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from fnmatch import fnmatch
from itertools import count
from pathlib import Path

#: Builtin extension -> category map. Custom ``--rule`` entries win over these.
CATEGORIES: dict[str, set[str]] = {
    "images": {"jpg", "jpeg", "png", "gif", "webp", "bmp", "svg", "ico", "tiff", "tif", "heic", "avif"},
    "documents": {"pdf", "doc", "docx", "txt", "md", "rtf", "odt", "xls", "xlsx", "ppt", "pptx", "csv", "pages", "epub"},
    "archives": {"zip", "rar", "7z", "tar", "gz", "bz2", "xz", "zst", "iso"},
    "audio": {"mp3", "wav", "flac", "aac", "ogg", "m4a", "wma", "opus"},
    "video": {"mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v"},
    "code": {"py", "js", "ts", "html", "css", "json", "xml", "yml", "yaml", "sh", "bat", "ps1", "java", "c", "cpp", "h", "go", "rs", "rb", "php", "ipynb", "sql"},
    "fonts": {"ttf", "otf", "woff", "woff2"},
    "executables": {"exe", "msi", "dmg", "appimage", "deb", "rpm", "apk"},
    "data": {"db", "sqlite", "sqlite3", "db3", "parquet", "pkl"},
}

EXT_MAP: dict[str, str] = {
    ext: category for category, exts in CATEGORIES.items() for ext in exts
}


@dataclass(frozen=True)
class Move:
    """One planned relocation of a loose file into its category folder."""

    src: Path
    dest: Path
    category: str
    size: int


def parse_rules(pairs: list[str] | tuple[str, ...]) -> dict[str, str]:
    """Parse ``["log=logs", "jpg=pics"]`` into ``{"log": "logs", ...}``.

    Extensions are lower-cased and stripped of leading dots; target
    directories must be plain single-path names (no separators, no ``.``/``..``).
    """
    rules: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            raise ValueError(f"invalid rule {pair!r}: expected ext=directory")
        ext, directory = pair.split("=", 1)
        ext = ext.strip().lower().lstrip(".")
        directory = directory.strip()
        if not ext or not directory:
            raise ValueError(f"invalid rule {pair!r}: both sides are required")
        if "/" in directory or "\\" in directory or directory in (".", ".."):
            raise ValueError(f"invalid rule {pair!r}: directory must be a plain name")
        rules[ext] = directory
    return rules


def plan_moves(
    root: str | Path,
    *,
    rules: list[str] | tuple[str, ...] = (),
    exclude: list[str] | tuple[str, ...] = (),
    dest: str | Path | None = None,
) -> tuple[list[Move], int]:
    """Build the sorted list of moves for loose files directly inside *root*.

    The scan is deliberately non-recursive. Hidden files, symlinks and
    ``--exclude`` patterns are left alone; files whose extension maps to
    no category (builtin or custom) are not planned and counted as unknown.

    Returns ``(moves, unknown_count)``.
    """
    root_path = Path(root).absolute()
    if not root_path.is_dir():
        raise NotADirectoryError(f"not a directory: {root_path}")

    rule_map = parse_rules(tuple(rules))
    patterns = tuple(exclude)
    target_root = Path(dest).absolute() if dest else root_path

    moves: list[Move] = []
    unknown = 0
    for entry in sorted(root_path.iterdir()):
        if not entry.is_file() or entry.is_symlink():
            continue
        if entry.name.startswith("."):
            continue
        if any(fnmatch(entry.name, pattern) for pattern in patterns):
            continue
        ext = entry.suffix.lower().lstrip(".")
        category = rule_map.get(ext) or EXT_MAP.get(ext)
        if category is None:
            unknown += 1
            continue
        try:
            size = entry.stat().st_size
        except OSError:
            continue
        moves.append(Move(entry, target_root / category / entry.name, category, size))
    return moves, unknown


def apply_moves(moves: list[Move]) -> int:
    """Carry out the planned moves; return how many actually moved.

    Name collisions inside the category folder resolve to ``name (1).ext``.
    """
    moved = 0
    for plan in moves:
        plan.dest.parent.mkdir(parents=True, exist_ok=True)
        final = unique_destination(plan.dest)
        shutil.move(str(plan.src), str(final))
        moved += 1
    return moved


def unique_destination(dest: Path) -> Path:
    """Return *dest*, or the first free ``name (N).ext`` variant of it."""
    if not dest.exists():
        return dest
    stem, suffix = dest.stem, dest.suffix
    for index in count(1):
        candidate = dest.with_name(f"{stem} ({index}){suffix}")
        if not candidate.exists():
            return candidate


def format_bytes(size: float) -> str:
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:,.0f} {unit}" if unit == "B" else f"{size:,.1f} {unit}"
        size /= 1024
    return f"{size:,.1f} TiB"
