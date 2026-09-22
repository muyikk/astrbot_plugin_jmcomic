from __future__ import annotations

import re
from pathlib import Path

_INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
_NATURAL_PARTS = re.compile(r"(\d+)")
_ALBUM_ID = re.compile(r"\d+")


def clean_album_id(raw: str) -> str:
    """Normalize ``JM123`` and ``123`` to the same safe album id."""
    value = str(raw).strip()
    if value[:2].lower() == "jm":
        value = value[2:]
    if not _ALBUM_ID.fullmatch(value):
        raise ValueError("漫画 ID 必须是纯数字，或 JM 加纯数字，例如 JM12345")
    return value


def sanitize_filename(name: str, fallback: str = "untitled") -> str:
    value = _INVALID_FILENAME_CHARS.sub("", str(name)).strip().rstrip(".")
    return value[:180] or fallback


def natural_path_key(path: Path) -> tuple[object, ...]:
    """Sort page paths naturally so 2.jpg comes before 10.jpg."""
    relative = path.as_posix().lower()
    return tuple(int(part) if part.isdigit() else part for part in _NATURAL_PARTS.split(relative))


def human_size(size: int) -> str:
    value = float(max(size, 0))
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TiB"
