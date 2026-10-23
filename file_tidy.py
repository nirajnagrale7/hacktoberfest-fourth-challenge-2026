"""Safe planning and application of local file organization suggestions."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CATEGORIES = ("Documents", "Images", "Audio", "Video", "Archives", "Code", "Other")
MAX_FILES = 100
_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')
_WHITESPACE = re.compile(r"\s+")
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


@dataclass(frozen=True)
class FileMove:
    source: Path
    destination: Path
    category: str


def scan_folder(folder: str | Path) -> tuple[Path, list[Path]]:
    """Return immediate regular files in a folder without following symlinks."""
    root = Path(folder).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Choose an existing folder.")

    files = sorted(
        (item for item in root.iterdir() if item.is_file() and not item.is_symlink()),
        key=lambda item: item.name.casefold(),
    )
    if len(files) > MAX_FILES:
        raise ValueError(
            f"This folder has {len(files)} files. Please organize at most "
            f"{MAX_FILES} files at a time."
        )
    return root, files


def parse_suggestions(
    response: Any, filenames: list[str]
) -> dict[str, dict[str, str]]:
    """Validate the model response against the exact set of scanned filenames."""
    if not isinstance(response, dict) or not isinstance(response.get("files"), list):
        raise ValueError("The model response must contain a 'files' list.")

    expected = set(filenames)
    suggestions: dict[str, dict[str, str]] = {}
    for item in response["files"]:
        if not isinstance(item, dict):
            raise ValueError("Every model suggestion must be an object.")
        original = item.get("original_name")
        category = item.get("category")
        new_stem = item.get("new_stem")
        if not isinstance(original, str) or original not in expected:
            raise ValueError("The model returned a filename that was not scanned.")
        if original in suggestions:
            raise ValueError(f"The model returned {original!r} more than once.")
        if category not in CATEGORIES:
            raise ValueError(f"The model returned an unsupported category for {original!r}.")
        if not isinstance(new_stem, str) or not new_stem.strip():
            raise ValueError(f"The model returned an empty name for {original!r}.")
        suggestions[original] = {"category": category, "new_stem": new_stem}

    missing = expected - suggestions.keys()
    if missing:
        raise ValueError(f"The model did not categorize: {', '.join(sorted(missing))}.")
    return suggestions


def _safe_stem(stem: str) -> str:
    cleaned = _INVALID_FILENAME_CHARS.sub(" ", stem)
    cleaned = _WHITESPACE.sub("-", cleaned).strip(" .-_")[:80].rstrip(" .")
    if not cleaned:
        raise ValueError("A suggested filename becomes empty after sanitization.")
    if cleaned.split(".", 1)[0].upper() in _WINDOWS_RESERVED_NAMES:
        cleaned = f"_{cleaned}"
    return cleaned


def create_plan(
    root: str | Path,
    files: list[Path],
    suggestions: dict[str, dict[str, str]],
) -> list[FileMove]:
    """Validate suggestions and produce safe, non-conflicting destinations."""
    resolved_root = Path(root).resolve(strict=True)
    if not resolved_root.is_dir():
        raise ValueError("Choose an existing folder.")

    if set(suggestions) != {item.name for item in files}:
        raise ValueError("Suggestions must match the scanned files exactly.")

    plan: list[FileMove] = []
    target_paths: set[Path] = set()
    for file_path in files:
        source = Path(file_path)
        if source.parent.resolve(strict=True) != resolved_root:
            raise ValueError(f"{source.name!r} is not directly inside the selected folder.")
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"{source.name!r} is no longer a regular file.")

        suggestion = suggestions[source.name]
        category = suggestion["category"]
        if category not in CATEGORIES:
            raise ValueError(f"Unsupported category for {source.name!r}.")
        stem = _safe_stem(suggestion["new_stem"])
        destination = resolved_root / category / f"{stem}{source.suffix}"
        if destination in target_paths:
            raise FileExistsError(f"Multiple files would be named {destination.name!r}.")
        if destination.exists():
            raise FileExistsError(f"The destination already exists: {destination}")
        target_paths.add(destination)
        plan.append(FileMove(source=source, destination=destination, category=category))

    return plan


def apply_plan(plan: list[FileMove]) -> None:
    """Move files without overwriting an existing destination."""
    targets = [move.destination for move in plan]
    if len(targets) != len(set(targets)):
        raise FileExistsError("The plan contains duplicate destinations.")
    for move in plan:
        if move.destination.exists():
            raise FileExistsError(f"The destination already exists: {move.destination}")
        if move.source.is_symlink() or not move.source.is_file():
            raise FileNotFoundError(f"The source is no longer available: {move.source}")

    moved: list[FileMove] = []
    try:
        for move in plan:
            move.destination.parent.mkdir(parents=True, exist_ok=True)
            # Linking first ensures a name collision never overwrites user data.
            os.link(move.source, move.destination)
            try:
                move.source.unlink()
            except OSError:
                move.destination.unlink(missing_ok=True)
                raise
            moved.append(move)
    except OSError as error:
        rollback_errors: list[str] = []
        for move in reversed(moved):
            try:
                move.source.parent.mkdir(parents=True, exist_ok=True)
                os.link(move.destination, move.source)
                move.destination.unlink()
            except OSError as rollback_error:
                rollback_errors.append(str(rollback_error))
        detail = f"Organization stopped after {len(moved)} file(s): {error}"
        if rollback_errors:
            detail += " Some rollback operations also failed: " + "; ".join(rollback_errors)
        raise OSError(detail) from error
