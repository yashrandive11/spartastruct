"""File system utilities for discovering source files across languages."""

from __future__ import annotations

from pathlib import Path

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
        ".next",
        ".nuxt",
        "coverage",
        "out",
    }
)

MAX_FILE_SIZE_BYTES = 500 * 1024  # 500 KB

ROOT_MARKERS = frozenset({"pyproject.toml", "setup.py", "setup.cfg", ".git", "package.json"})

SUPPORTED_EXTENSIONS = frozenset({".py", ".js", ".ts", ".jsx", ".tsx"})

_DEFAULT_EXTENSIONS = frozenset({".py"})


def find_project_root(start: Path) -> Path:
    """Walk upward from start to find the project root."""
    current = start.resolve()
    while True:
        if any((current / marker).exists() for marker in ROOT_MARKERS):
            return current
        parent = current.parent
        if parent == current:
            return start.resolve()
        current = parent


def walk_project(
    root: Path,
    extensions: frozenset[str] = _DEFAULT_EXTENSIONS,
) -> tuple[list[Path], list[str]]:
    """Recursively discover all source files under root matching extensions.

    Args:
        root: The project root directory to walk from.
        extensions: File extensions to include (e.g. frozenset({".py", ".ts"})).
                    Defaults to {".py"} to preserve existing behaviour.

    Returns:
        A tuple of (source_files, warnings).
    """
    source_files: list[Path] = []
    warnings: list[str] = []

    root = root.resolve()

    for item in _walk(root):
        if item.is_file() and item.suffix in extensions:
            size = item.stat().st_size
            if size > MAX_FILE_SIZE_BYTES:
                rel = item.relative_to(root)
                warnings.append(f"Skipped (too large, {size // 1024}KB > 500KB): {rel}")
            else:
                source_files.append(item)

    return source_files, warnings


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
