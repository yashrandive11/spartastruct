"""Python AST analyzer — extracts structure from Python source files."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from spartastruct.analyzer.base import (
    AnalysisResult,
    AttributeInfo,
    ClassInfo,
    FileResult,
    FunctionInfo,
    ImportInfo,
    MethodInfo,
    ParamInfo,
    RouteInfo,
)

# Known ORM base class patterns
_SQLALCHEMY_BASES = frozenset({"Base", "DeclarativeBase", "Model"})
_DJANGO_BASES = frozenset({"models.Model", "Model"})
_TORTOISE_BASES = frozenset({"tortoise.models.Model", "Model"})
_PEEWEE_BASES = frozenset({"peewee.Model", "Model"})


def _visibility(name: str) -> str:
    """Infer visibility from a Python identifier naming convention."""
    if name.startswith("__") and not name.endswith("__"):
        return "private"
    if name.startswith("_"):
        return "protected"
    return "public"


def _annotation_to_str(node: ast.expr | None) -> str:
    """Convert an AST annotation node to a readable string."""
    if node is None:
        return "Any"
    return ast.unparse(node)


def _decorator_names(decorator_list: list[ast.expr]) -> list[str]:
    """Extract decorator names from an AST decorator list."""
    names = []
    for dec in decorator_list:
        if isinstance(dec, ast.Name):
            names.append(dec.id)
        elif isinstance(dec, ast.Attribute):
            names.append(ast.unparse(dec))
        elif isinstance(dec, ast.Call):
            if isinstance(dec.func, ast.Name):
                names.append(dec.func.id)
            elif isinstance(dec.func, ast.Attribute):
                names.append(ast.unparse(dec.func))
    return names


def _classify_imports(
    tree: ast.Module,
    local_roots: frozenset[str],
) -> ImportInfo:
    """Classify all imports in a module as stdlib, third-party, or local."""
    stdlib_names = sys.stdlib_module_names  # type: ignore[attr-defined]
    stdlib: list[str] = []
    third_party: list[str] = []
    local: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                _bucket(root, alias.name, stdlib_names, local_roots, stdlib, third_party, local)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root = node.module.split(".")[0]
                _bucket(root, node.module, stdlib_names, local_roots, stdlib, third_party, local)

    return ImportInfo(stdlib=stdlib, third_party=third_party, local=local)


def _bucket(
    root: str,
    full_name: str,
    stdlib_names: frozenset[str],
    local_roots: frozenset[str],
    stdlib: list[str],
    third_party: list[str],
    local: list[str],
) -> None:
    """Append full_name to the appropriate bucket list."""
    if root in stdlib_names:
        stdlib.append(full_name)
    elif root in local_roots:
        local.append(full_name)
    else:
        third_party.append(full_name)


def _detect_orm_type(
    class_node: ast.ClassDef,
    file_imports: ImportInfo,
) -> str | None:
    """Determine if a class is an ORM model and return the ORM type string."""
    base_names = set()
    for base in class_node.bases:
        base_names.add(ast.unparse(base))

    all_imports = set(file_imports.stdlib + file_imports.third_party + file_imports.local)
    has_sqlalchemy = any("sqlalchemy" in imp for imp in all_imports)
    has_django = any("django" in imp for imp in all_imports)
    has_tortoise = any("tortoise" in imp for imp in all_imports)
    has_peewee = any("peewee" in imp for imp in all_imports)

    if has_sqlalchemy and base_names & _SQLALCHEMY_BASES:
        return "sqlalchemy"
    if has_django and base_names & _DJANGO_BASES:
        return "django"
    if has_tortoise and base_names & _TORTOISE_BASES:
        return "tortoise"
    if has_peewee and base_names & _PEEWEE_BASES:
        return "peewee"
    return None


def _extract_class(class_node: ast.ClassDef, file_imports: ImportInfo) -> ClassInfo:
    """Build a ClassInfo from an AST ClassDef node."""
    decorators = _decorator_names(class_node.decorator_list)
    bases = [ast.unparse(b) for b in class_node.bases]

    is_abstract = bool({"ABC", "ABCMeta"} & set(bases))
    is_dataclass = "dataclass" in decorators
    orm_type = _detect_orm_type(class_node, file_imports)

    attributes: list[AttributeInfo] = []
    methods: list[MethodInfo] = []

    for item in class_node.body:
        # Class-level annotated assignments: x: int = 5
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            name = item.target.id
            type_str = _annotation_to_str(item.annotation)
            attributes.append(AttributeInfo(
                name=name,
                type=type_str,
                visibility=_visibility(name),
            ))
        # Plain assignments at class level (e.g. ORM Column definitions)
        elif isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name):
                    type_str = _infer_type_simple(item.value)
                    attributes.append(AttributeInfo(
                        name=target.id,
                        type=type_str,
                        visibility=_visibility(target.id),
                    ))
        elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append(_extract_method(item))

    # Check for abstractmethod usage
    if any("abstractmethod" in m.decorators for m in methods):
        is_abstract = True

    return ClassInfo(
        name=class_node.name,
        bases=bases,
        decorators=decorators,
        attributes=attributes,
        methods=methods,
        is_abstract=is_abstract,
        is_dataclass=is_dataclass,
        orm_type=orm_type,
    )


def _extract_method(node: ast.FunctionDef | ast.AsyncFunctionDef) -> MethodInfo:
    """Build a MethodInfo from an AST function node inside a class."""
    params = _extract_params(node)
    # Remove 'self' and 'cls' from param list for display
    params = [p for p in params if p.name not in ("self", "cls")]
    return MethodInfo(
        name=node.name,
        params=params,
        return_type=_annotation_to_str(node.returns),
        decorators=_decorator_names(node.decorator_list),
        is_async=isinstance(node, ast.AsyncFunctionDef),
        calls=[],  # filled in later
        visibility=_visibility(node.name),
    )


def _extract_params(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ParamInfo]:
    """Extract parameters from a function definition node."""
    params = []
    args = node.args
    # Combine positional, keyword-only, and *args/**kwargs
    all_args = args.args + args.posonlyargs + args.kwonlyargs
    if args.vararg:
        all_args.append(args.vararg)
    if args.kwarg:
        all_args.append(args.kwarg)
    for arg in all_args:
        type_str = _annotation_to_str(arg.annotation) if arg.annotation else "Any"
        params.append(ParamInfo(name=arg.arg, type=type_str))
    return params


def _infer_type_simple(value_node: ast.expr | None) -> str:
    """Infer type from a simple AST value node without astroid."""
    if value_node is None:
        return "Any"
    if isinstance(value_node, ast.Constant):
        return type(value_node.value).__name__
    if isinstance(value_node, ast.List):
        return "list"
    if isinstance(value_node, ast.Dict):
        return "dict"
    if isinstance(value_node, ast.Set):
        return "set"
    if isinstance(value_node, ast.Tuple):
        return "tuple"
    if isinstance(value_node, ast.Call):
        if isinstance(value_node.func, ast.Name):
            return value_node.func.id
        if isinstance(value_node.func, ast.Attribute):
            return value_node.func.attr
    return "Any"


def _infer_type_astroid(file_path: Path, lineno: int, name: str) -> str:
    """Use astroid to infer type of an unannotated assignment.

    This is a best-effort helper. Falls back to 'Any' on any failure.
    Used only when _infer_type_simple returns 'Any'.
    """
    try:
        import astroid  # noqa: PLC0415

        module = astroid.MANAGER.ast_from_file(str(file_path))
        for node in module.nodes_of_class(astroid.AssignAttr):
            if node.lineno == lineno and node.attrname == name:
                inferred = list(node.infer())
                if inferred and inferred[0] is not astroid.Uninferable:
                    return type(inferred[0]).__name__
    except Exception:  # noqa: BLE001
        pass
    return "Any"


def _detect_entry_points(file_result: FileResult, filename: str) -> bool:
    """Return True if this file appears to be a project entry point."""
    entry_names = {
        "main.py", "app.py", "run.py", "server.py",
        "manage.py", "wsgi.py", "asgi.py", "__main__.py",
    }
    return Path(filename).name in entry_names


class PythonAnalyzer:
    """Analyzes Python source files and produces an AnalysisResult.

    Uses ast for primary parsing, with limited astroid support for
    type inference on unannotated assignments.
    """

    def __init__(self, project_root: Path) -> None:
        """Initialize with the project root for local import resolution."""
        self._root = project_root.resolve()
        self._local_roots = self._discover_local_roots()

    def _discover_local_roots(self) -> frozenset[str]:
        """Build the set of top-level package/module names in this project."""
        roots: set[str] = set()
        for item in self._root.iterdir():
            if item.is_dir() and (item / "__init__.py").exists():
                roots.add(item.name)
            elif item.is_file() and item.suffix == ".py":
                roots.add(item.stem)
        return frozenset(roots)

    def analyze(self, files: list[Path], warnings: list[str] | None = None) -> AnalysisResult:
        """Analyze a list of Python files and return a complete AnalysisResult.

        Args:
            files: Absolute paths to .py files to analyze.
            warnings: Optional list to append parse warnings to.

        Returns:
            An AnalysisResult populated with data from all successfully parsed files.
        """
        if warnings is None:
            warnings = []

        file_results: list[FileResult] = []
        parse_errors = 0

        for file_path in files:
            result = self._analyze_file(file_path, warnings)
            if result is not None:
                file_results.append(result)
            else:
                parse_errors += 1

        # Detect entry points
        entry_points: list[str] = []
        for fr in file_results:
            if _detect_entry_points(fr, fr.path):
                entry_points.append(fr.path)
            # Also check for if __name__ == "__main__" — done during parse
            if fr.__dict__.get("_has_main_block", False):
                if fr.path not in entry_points:
                    entry_points.append(fr.path)

        analysis = AnalysisResult(
            files_analyzed=file_results,
            entry_points=entry_points,
            warnings=warnings,
            files_skipped_parse_error=parse_errors,
        )

        # Post-process: detect frameworks and resolve function calls
        from spartastruct.utils.framework_detector import detect_frameworks  # noqa: PLC0415
        analysis.frameworks = detect_frameworks(analysis)

        self._resolve_calls(analysis)

        return analysis

    def _analyze_file(self, file_path: Path, warnings: list[str]) -> FileResult | None:
        """Parse a single file and return a FileResult, or None on error."""
        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError as exc:
            rel = file_path.relative_to(self._root) if file_path.is_relative_to(self._root) else file_path
            warnings.append(f"Parse error in {rel}: {exc}")
            return None
        except Exception as exc:  # noqa: BLE001
            rel = file_path.relative_to(self._root) if file_path.is_relative_to(self._root) else file_path
            warnings.append(f"Failed to read {rel}: {exc}")
            return None

        try:
            rel_path = str(file_path.relative_to(self._root))
        except ValueError:
            rel_path = str(file_path)

        imports = _classify_imports(tree, self._local_roots)
        classes = self._extract_classes(tree, imports, file_path)
        functions = self._extract_functions(tree)
        routes = self._extract_routes(tree)

        # Check for if __name__ == "__main__"
        has_main_block = self._has_main_guard(tree)

        fr = FileResult(
            path=rel_path,
            classes=classes,
            functions=functions,
            imports=imports,
            routes=routes,
        )
        fr.__dict__["_has_main_block"] = has_main_block  # type: ignore[attr-defined]
        return fr

    def _extract_classes(
        self,
        tree: ast.Module,
        imports: ImportInfo,
        file_path: Path,
    ) -> list[ClassInfo]:
        """Extract all top-level and nested class definitions."""
        classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(_extract_class(node, imports))
        return classes

    def _extract_functions(self, tree: ast.Module) -> list[FunctionInfo]:
        """Extract all module-level function definitions (not methods).

        Stub — implemented in next task.
        """
        return []

    def _extract_routes(self, tree: ast.Module) -> list[RouteInfo]:
        """Extract HTTP route definitions from FastAPI/Flask/Django patterns.

        Stub — implemented in next task.
        """
        return []

    def _has_main_guard(self, tree: ast.Module) -> bool:
        """Return True if the module contains an if __name__ == '__main__' block."""
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                test = node.test
                if (
                    isinstance(test, ast.Compare)
                    and isinstance(test.left, ast.Name)
                    and test.left.id == "__name__"
                    and len(test.comparators) == 1
                    and isinstance(test.comparators[0], ast.Constant)
                    and test.comparators[0].value == "__main__"
                ):
                    return True
        return False

    def _resolve_calls(self, result: AnalysisResult) -> None:
        """Resolve function call names to local project symbols where possible.

        Stub — implemented in next task.
        """
        pass
