"""Turn file names received from the other computer into safe local paths.

Names that are fine on Linux can be illegal on Windows (``a:b.txt``, ``CON``,
trailing dots, names differing only by case), and a malicious sender could try
``../../something``. Everything received goes through plan_destinations().
"""

import os
import re
from pathlib import Path

from . import IS_WINDOWS

_WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {
    f"LPT{i}" for i in range(1, 10)
}
_WINDOWS_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_MAX_NAME_BYTES = 240  # leaves room for the ".part" suffix used while receiving


def split_relpath(path: str) -> list[str]:
    """Split a protocol path ("a/b/c.txt") and reject anything that escapes."""
    if not isinstance(path, str) or not path:
        raise ValueError("empty path")
    parts = path.split("/")
    for part in parts:
        if part in ("", ".", ".."):
            raise ValueError(f"unsafe path: {path!r}")
    return parts


def clean_name(name: str, windows: bool = IS_WINDOWS) -> str:
    name = name.replace("\x00", "")
    if windows:
        name = _WINDOWS_INVALID.sub("_", name).rstrip(" .")
        if name.split(".")[0].upper() in _WINDOWS_RESERVED:
            name = "_" + name
    if name in ("", ".", ".."):
        name = "_"
    return _truncate(name)


def _truncate(name: str) -> str:
    if len(name.encode("utf-8")) <= _MAX_NAME_BYTES:
        return name
    stem, ext = os.path.splitext(name)
    if len(ext.encode("utf-8")) > 20:
        stem, ext = name, ""
    budget = _MAX_NAME_BYTES - len(ext.encode("utf-8"))
    stem = stem.encode("utf-8")[:budget].decode("utf-8", "ignore")
    return stem + ext


def _numbered(name: str, n: int, is_dir: bool) -> str:
    stem, ext = (name, "") if is_dir else os.path.splitext(name)
    return f"{stem} ({n}){ext}"


def plan_destinations(items: list[dict], base: Path, windows: bool = IS_WINDOWS,
                      reserved: set[str] | None = None) -> list[Path]:
    """Map every offered item to a destination path inside ``base``.

    Top-level names that already exist get " (1)", " (2)"... appended, and on
    Windows names that only differ by case are kept apart the same way.
    ``reserved`` holds casefolded paths claimed by transfers still in progress.
    """
    base = Path(os.path.abspath(base))
    reserved = reserved if reserved is not None else set()
    dir_map: dict[str, Path] = {"": base}
    taken: dict[Path, set[str]] = {}

    def key(name: str) -> str:
        return name.casefold() if windows else name

    def claim(parent: Path, name: str, is_dir: bool) -> Path:
        used = taken.setdefault(parent, set())
        candidate, n = name, 0
        while (key(candidate) in used or (parent / candidate).exists()
               or str(parent / candidate).casefold() in reserved):
            n += 1
            candidate = _numbered(name, n, is_dir)
        used.add(key(candidate))
        return parent / candidate

    def map_dir(parts: list[str]) -> Path:
        rel = "/".join(parts)
        if rel not in dir_map:
            parent = map_dir(parts[:-1])
            dir_map[rel] = claim(parent, clean_name(parts[-1], windows), is_dir=True)
        return dir_map[rel]

    result = []
    for item in items:
        parts = split_relpath(item["path"])
        if item["kind"] == "dir":
            dest = map_dir(parts)
        else:
            dest = claim(map_dir(parts[:-1]), clean_name(parts[-1], windows), is_dir=False)
        if os.path.commonpath([str(base), os.path.abspath(dest)]) != str(base):
            raise ValueError(f"unsafe path: {item['path']!r}")
        result.append(dest)
    return result


def top_level_paths(base: Path, destinations: list[Path]) -> set[Path]:
    """The first path component below ``base`` of every destination."""
    base = Path(os.path.abspath(base))
    return {base / dest.relative_to(base).parts[0] for dest in destinations}
