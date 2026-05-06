"""Tests for the JS/TS analyzer and multi-language file walking."""

from __future__ import annotations

from pathlib import Path

from spartastruct.utils.file_walker import SUPPORTED_EXTENSIONS, walk_project

FIXTURES = Path(__file__).parent / "fixtures"


def test_walk_project_finds_js_ts_files(tmp_path):
    (tmp_path / "app.js").write_text("console.log('hello')")
    (tmp_path / "types.ts").write_text("export type Foo = string")
    (tmp_path / "component.tsx").write_text("export default function App() {}")
    (tmp_path / "ignored.txt").write_text("not a source file")

    files, warnings = walk_project(tmp_path, extensions=frozenset({".js", ".ts", ".tsx"}))
    stems = {f.name for f in files}
    assert "app.js" in stems
    assert "types.ts" in stems
    assert "component.tsx" in stems
    assert "ignored.txt" not in stems
    assert warnings == []


def test_walk_project_default_still_finds_py_only(tmp_path):
    (tmp_path / "main.py").write_text("print('hi')")
    (tmp_path / "app.js").write_text("console.log('hi')")

    files, _ = walk_project(tmp_path)
    assert all(f.suffix == ".py" for f in files)


def test_supported_extensions_contains_js_ts():
    assert ".js" in SUPPORTED_EXTENSIONS
    assert ".ts" in SUPPORTED_EXTENSIONS
    assert ".jsx" in SUPPORTED_EXTENSIONS
    assert ".tsx" in SUPPORTED_EXTENSIONS
    assert ".py" in SUPPORTED_EXTENSIONS
