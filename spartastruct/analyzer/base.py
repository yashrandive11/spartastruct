"""Core data model for SpartaStruct analysis results.

All analysis modules produce instances of these dataclasses, and all
diagram generators and renderers consume them.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParamInfo:
    """A single function/method parameter with optional type annotation."""

    name: str
    type: str = "Any"


@dataclass
class AttributeInfo:
    """A class attribute or instance variable."""

    name: str
    type: str = "Any"
    visibility: str = "public"  # "public", "protected", "private"


@dataclass
class MethodInfo:
    """A class method with full signature information."""

    name: str
    params: list[ParamInfo] = field(default_factory=list)
    return_type: str = "None"
    decorators: list[str] = field(default_factory=list)
    is_async: bool = False
    calls: list[str] = field(default_factory=list)
    visibility: str = "public"  # "public", "protected", "private"


@dataclass
class ClassInfo:
    """A Python class with all its members and metadata."""

    name: str
    bases: list[str] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)
    attributes: list[AttributeInfo] = field(default_factory=list)
    methods: list[MethodInfo] = field(default_factory=list)
    is_abstract: bool = False
    is_dataclass: bool = False
    orm_type: str | None = None  # "sqlalchemy", "django", "tortoise", "peewee"


@dataclass
class FunctionInfo:
    """A module-level function."""

    name: str
    params: list[ParamInfo] = field(default_factory=list)
    return_type: str = "None"
    decorators: list[str] = field(default_factory=list)
    is_async: bool = False
    calls: list[str] = field(default_factory=list)


@dataclass
class ImportInfo:
    """Classified imports for a single Python file."""

    stdlib: list[str] = field(default_factory=list)
    third_party: list[str] = field(default_factory=list)
    local: list[str] = field(default_factory=list)  # local project import edges


@dataclass
class RouteInfo:
    """An HTTP route definition (FastAPI, Flask, or Django)."""

    method: str  # "GET", "POST", "PUT", "DELETE", etc. or "ANY" for Flask catch-all
    path: str
    handler_name: str


@dataclass
class FileResult:
    """Analysis results for a single Python file."""

    path: str  # relative path from project root
    classes: list[ClassInfo] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)
    imports: ImportInfo = field(default_factory=ImportInfo)
    routes: list[RouteInfo] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """Top-level container for an entire project analysis run."""

    files_analyzed: list[FileResult] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    entry_points: list[str] = field(default_factory=list)  # relative file paths
    warnings: list[str] = field(default_factory=list)
    llm_calls_succeeded: int = 0
    files_skipped_large: int = 0
    files_skipped_parse_error: int = 0

    @property
    def all_classes(self) -> list[ClassInfo]:
        """Return all ClassInfo objects across all analyzed files."""
        return [cls for fr in self.files_analyzed for cls in fr.classes]

    @property
    def all_functions(self) -> list[FunctionInfo]:
        """Return all FunctionInfo objects across all analyzed files."""
        return [fn for fr in self.files_analyzed for fn in fr.functions]

    @property
    def all_routes(self) -> list[RouteInfo]:
        """Return all RouteInfo objects across all analyzed files."""
        return [r for fr in self.files_analyzed for r in fr.routes]

    @property
    def orm_models(self) -> list[ClassInfo]:
        """Return all classes that are ORM models."""
        return [cls for cls in self.all_classes if cls.orm_type is not None]
