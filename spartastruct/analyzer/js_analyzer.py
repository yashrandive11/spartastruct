"""Regex-based analyzer for JavaScript and TypeScript source files."""

from __future__ import annotations

import re
from pathlib import Path

from spartastruct.analyzer.base import (
    AnalysisResult,
    ClassInfo,
    FileResult,
    FunctionInfo,
    ImportInfo,
    MethodInfo,
    RouteInfo,
)

# Class / interface declarations
_CLASS_RE = re.compile(
    r"(?:export\s+)?(?:abstract\s+)?(?:class|interface)\s+(\w+)"
    r"(?:\s+extends\s+([\w,\s<>]+?))?(?:\s+implements\s+([\w,\s<>]+?))?"
    r"\s*\{",
    re.MULTILINE,
)

# Method inside a class body
_METHOD_RE = re.compile(
    r"(?:(?:public|private|protected|static|async|override|abstract|readonly)\s+)*"
    r"(\w+)\s*\([^)]*\)\s*(?::\s*[\w<>\[\]|&\s]+?)?\s*[{;]",
    re.MULTILINE,
)
_METHOD_SKIP = frozenset(
    {"if", "for", "while", "switch", "catch", "super", "return", "new", "throw"}
)

# Named function declarations
_FUNC_DECL_RE = re.compile(
    r"(?:export\s+)?(?P<async>async\s+)?function\s+(?P<name>\w+)\s*\(",
    re.MULTILINE,
)

# Arrow / expression functions: const foo = (async?) (...) =>
_ARROW_RE = re.compile(
    r"(?:export\s+)?(?:const|let|var)\s+(?P<name>\w+)\s*=\s*(?P<async>async\s+)?\(",
    re.MULTILINE,
)

# ES module imports
_IMPORT_FROM_RE = re.compile(
    r"""import\s+(?:.*?\s+from\s+)?['"]([^'"]+)['"]""",
    re.MULTILINE | re.DOTALL,
)

# CommonJS requires
_REQUIRE_RE = re.compile(
    r"""(?:const|let|var)\s+\w+\s*=\s*require\s*\(\s*['"]([^'"]+)['"]\s*\)""",
    re.MULTILINE,
)

# Express routes
_EXPRESS_ROUTE_RE = re.compile(
    r"(?:app|router)\.(get|post|put|patch|delete|all)\s*\(\s*['\"`]([^'\"`]+)['\"`]",
    re.MULTILINE | re.IGNORECASE,
)

# NestJS decorator routes
_NESTJS_ROUTE_RE = re.compile(
    r"@(Get|Post|Put|Patch|Delete|All)\s*\(\s*(?:['\"`]([^'\"`]*)['\"`])?\s*\)",
    re.MULTILINE,
)

_JS_ENTRY_NAMES = frozenset(
    {"index.js", "index.ts", "main.js", "main.ts", "app.js", "app.ts", "server.js", "server.ts"}
)


def _extract_class_body(source: str, brace_pos: int) -> str:
    """Return the text between the first matching { } pair starting at brace_pos."""
    depth = 0
    start = None
    for i in range(brace_pos, len(source)):
        ch = source[i]
        if ch == "{":
            if start is None:
                start = i + 1
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                return source[start:i]
    return ""


def _extract_methods(class_body: str) -> list[MethodInfo]:
    methods: list[MethodInfo] = []
    seen: set[str] = set()
    for m in _METHOD_RE.finditer(class_body):
        name = m.group(1)
        if name in _METHOD_SKIP or name in seen:
            continue
        seen.add(name)
        methods.append(MethodInfo(name=name))
    return methods


def _classify_import(module_path: str) -> tuple[str, str]:
    if module_path.startswith("."):
        return "local", module_path
    return "third_party", module_path


def _extract_routes(source: str) -> list[RouteInfo]:
    routes: list[RouteInfo] = []
    for m in _EXPRESS_ROUTE_RE.finditer(source):
        routes.append(RouteInfo(
            method=m.group(1).upper(),
            path=m.group(2),
            handler_name="handler",
        ))
    for m in _NESTJS_ROUTE_RE.finditer(source):
        routes.append(RouteInfo(
            method=m.group(1).upper(),
            path=m.group(2) or "/",
            handler_name="handler",
        ))
    return routes


def _analyze_file(file_path: Path, project_root: Path) -> FileResult:
    try:
        source = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        source = ""

    try:
        rel_path = str(file_path.relative_to(project_root))
    except ValueError:
        rel_path = str(file_path)

    # Classes / interfaces
    classes: list[ClassInfo] = []
    class_spans: list[tuple[int, int]] = []
    for m in _CLASS_RE.finditer(source):
        name = m.group(1)
        bases_raw = (m.group(2) or "").strip()
        bases = [b.strip() for b in re.split(r",\s*", bases_raw) if b.strip()]
        brace_pos = m.end() - 1
        class_body = _extract_class_body(source, brace_pos)
        class_spans.append((brace_pos, brace_pos + len(class_body) + 2))
        methods = _extract_methods(class_body)
        classes.append(ClassInfo(name=name, bases=bases, methods=methods))

    def _in_class(pos: int) -> bool:
        return any(start <= pos <= end for start, end in class_spans)

    # Module-level functions
    functions: list[FunctionInfo] = []
    seen_fns: set[str] = set()

    for m in _FUNC_DECL_RE.finditer(source):
        if _in_class(m.start()):
            continue
        name = m.group("name")
        if name in seen_fns:
            continue
        seen_fns.add(name)
        functions.append(FunctionInfo(name=name, is_async=bool(m.group("async"))))

    for m in _ARROW_RE.finditer(source):
        if _in_class(m.start()):
            continue
        name = m.group("name")
        if name in seen_fns:
            continue
        seen_fns.add(name)
        functions.append(FunctionInfo(name=name, is_async=bool(m.group("async"))))

    # Imports
    third_party: list[str] = []
    local: list[str] = []

    for m in _IMPORT_FROM_RE.finditer(source):
        kind, path = _classify_import(m.group(1))
        (local if kind == "local" else third_party).append(path)

    for m in _REQUIRE_RE.finditer(source):
        kind, path = _classify_import(m.group(1))
        (local if kind == "local" else third_party).append(path)

    imports = ImportInfo(
        third_party=list(dict.fromkeys(third_party)),
        local=list(dict.fromkeys(local)),
    )

    routes = _extract_routes(source)

    return FileResult(
        path=rel_path, classes=classes, functions=functions, imports=imports, routes=routes
    )


class JsAnalyzer:
    """Analyzes JavaScript and TypeScript source files using regex-based extraction."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root.resolve()

    def analyze(
        self,
        files: list[Path],
        warnings: list[str] | None = None,
    ) -> AnalysisResult:
        if warnings is None:
            warnings = []

        file_results: list[FileResult] = []
        for file_path in files:
            try:
                fr = _analyze_file(file_path, self._root)
                file_results.append(fr)
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"Failed to analyze {file_path.name}: {exc}")

        entry_points = [
            fr.path for fr in file_results
            if Path(fr.path).name in _JS_ENTRY_NAMES
        ]

        return AnalysisResult(
            files_analyzed=file_results,
            entry_points=entry_points,
            warnings=warnings,
        )
