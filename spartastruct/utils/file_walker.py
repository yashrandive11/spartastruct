"""File system utilities for discovering Python source files."""

from __future__ import annotations

from pathlib import Path

# Directories to skip during recursive walk
SKIP_DIRS = frozenset(
    {
        "__pycache__",
        ".git",
        "venv",
        ".venv",
        "env",
        ".env",
        "node_modules",
        "dist",
        "build",
        "eggs",
        ".eggs",
        ".tox",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "spartadocs",
    }
)

# Files larger than this are skipped with a warning
MAX_FILE_SIZE_BYTES = 500 * 1024  # 500 KB

# Markers that indicate a project root
ROOT_MARKERS = frozenset({"pyproject.toml", "setup.py", "setup.cfg", ".git"})


def find_project_root(start: Path) -> Path:
    """Walk upward from start to find the project root.

    Looks for pyproject.toml, setup.py, setup.cfg, or .git.
    Returns start itself if no marker is found.
    """
    current = start.resolve()
    while True:
        if any((current / marker).exists() for marker in ROOT_MARKERS):
            return current
        parent = current.parent
        if parent == current:
            # Reached filesystem root without finding a marker
            return start.resolve()
        current = parent


def walk_project(root: Path) -> tuple[list[Path], list[str]]:
    """Recursively discover all .py files under root, applying skip rules.

    Args:
        root: The project root directory to walk from.

    Returns:
        A tuple of (py_files, warnings) where py_files is a list of absolute
        paths to .py files and warnings is a list of human-readable warning
        strings for skipped files.
    """
    py_files: list[Path] = []
    warnings: list[str] = []

    root = root.resolve()

    for item in _walk(root):
        if item.is_file() and item.suffix == ".py":
            size = item.stat().st_size
            if size > MAX_FILE_SIZE_BYTES:
                rel = item.relative_to(root)
                warnings.append(f"Skipped (too large, {size // 1024}KB > 500KB): {rel}")
            else:
                py_files.append(item)

    return py_files, warnings


def _walk(directory: Path):
    """Yield all files under directory, skipping SKIP_DIRS."""
    try:
        entries = list(directory.iterdir())
    except PermissionError:
        return

    for entry in sorted(entries):
        if entry.is_dir():
            if entry.name not in SKIP_DIRS:
                yield from _walk(entry)
        else:
            yield entry
