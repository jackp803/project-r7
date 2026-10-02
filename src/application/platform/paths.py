"""Validate configured roots without creating directories or changing mounts."""

from pathlib import Path


def absolute_path(value: object, field: str) -> Path:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ValueError(f"{field}: absolute path required")
    path = Path(value)
    if not path.is_absolute():
        raise ValueError(f"{field}: absolute path required")
    return path.resolve(strict=False)


def overlapping(left: Path, right: Path) -> bool:
    return left.is_relative_to(right) or right.is_relative_to(left)


def existing_ancestor(path: Path) -> Path:
    current = path.resolve(strict=False)
    while not current.exists():
        if current.parent == current:
            raise ValueError("No existing data volume")
        current = current.parent
    return current
