"""Tests for the Python AST analyzer."""

from __future__ import annotations

from pathlib import Path

import pytest

from spartastruct.analyzer.python_analyzer import PythonAnalyzer
from spartastruct.utils.file_walker import walk_project

PLAIN_DIR = Path(__file__).parent / "fixtures" / "sample_plain"
FASTAPI_DIR = Path(__file__).parent / "fixtures" / "sample_fastapi"
DJANGO_DIR = Path(__file__).parent / "fixtures" / "sample_django"


@pytest.fixture
def plain_result():
    files, warnings = walk_project(PLAIN_DIR)
    analyzer = PythonAnalyzer(PLAIN_DIR)
    return analyzer.analyze(files, warnings)


@pytest.fixture
def fastapi_result():
    files, warnings = walk_project(FASTAPI_DIR)
    analyzer = PythonAnalyzer(FASTAPI_DIR)
    return analyzer.analyze(files, warnings)


@pytest.fixture
def django_result():
    files, warnings = walk_project(DJANGO_DIR)
    analyzer = PythonAnalyzer(DJANGO_DIR)
    return analyzer.analyze(files, warnings)


# --- Class extraction ---


def test_class_names_extracted(plain_result):
    names = {c.name for c in plain_result.all_classes}
    assert {"Shape", "Circle", "Rectangle", "ShapeRegistry"}.issubset(names)


def test_abstract_class_detected(plain_result):
    shape = next(c for c in plain_result.all_classes if c.name == "Shape")
    assert shape.is_abstract is True


def test_dataclass_detected(plain_result):
    circle = next(c for c in plain_result.all_classes if c.name == "Circle")
    assert circle.is_dataclass is True


def test_class_bases(plain_result):
    circle = next(c for c in plain_result.all_classes if c.name == "Circle")
    assert "Shape" in circle.bases


def test_visibility_inference(plain_result):
    registry = next(c for c in plain_result.all_classes if c.name == "ShapeRegistry")
    shapes_attr = next((a for a in registry.attributes if a.name == "_shapes"), None)
    assert shapes_attr is not None
    assert shapes_attr.visibility == "protected"


def test_method_extraction(plain_result):
    circle = next(c for c in plain_result.all_classes if c.name == "Circle")
    method_names = {m.name for m in circle.methods}
    assert {"area", "perimeter"}.issubset(method_names)


# --- Function extraction ---


def test_module_functions_extracted(plain_result):
    fn_names = {f.name for f in plain_result.all_functions}
    # utils.py has create_default_shapes, scale_shape_area, format_area, summarize_registry
    # main.py has run
    assert "run" in fn_names


def test_async_function_detection(fastapi_result):
    fn_names_async = {
        f.name for fr in fastapi_result.files_analyzed for f in fr.functions if f.is_async
    }
    # health_check is async in main.py
    assert "health_check" in fn_names_async


# --- Import classification ---


def test_stdlib_imports_classified(plain_result):
    all_stdlib = [imp for fr in plain_result.files_analyzed for imp in fr.imports.stdlib]
    assert any("math" in i for i in all_stdlib)


def test_local_imports_classified(plain_result):
    all_local = [imp for fr in plain_result.files_analyzed for imp in fr.imports.local]
    assert any("utils" in i or "shapes" in i for i in all_local)


def test_third_party_imports_classified(fastapi_result):
    all_tp = [imp for fr in fastapi_result.files_analyzed for imp in fr.imports.third_party]
    assert any("fastapi" in i for i in all_tp)


# --- ORM detection ---


def test_sqlalchemy_orm_detected(fastapi_result):
    orm_names = {c.name for c in fastapi_result.orm_models}
    assert {"User", "Post"}.issubset(orm_names)


def test_sqlalchemy_orm_type(fastapi_result):
    user = next(c for c in fastapi_result.orm_models if c.name == "User")
    assert user.orm_type == "sqlalchemy"


def test_django_orm_detected(django_result):
    orm_names = {c.name for c in django_result.orm_models}
    assert {"Author", "Article", "Tag"}.issubset(orm_names)


def test_django_orm_type(django_result):
    author = next(c for c in django_result.orm_models if c.name == "Author")
    assert author.orm_type == "django"


# --- Route extraction ---


def test_fastapi_routes_extracted(fastapi_result):
    all_routes = fastapi_result.all_routes
    methods = {r.method for r in all_routes}
    assert "GET" in methods
    assert "POST" in methods


def test_fastapi_route_handlers(fastapi_result):
    handler_names = {r.handler_name for r in fastapi_result.all_routes}
    assert "get_user" in handler_names
    assert "create_user" in handler_names


def test_django_routes_extracted(django_result):
    all_routes = django_result.all_routes
    assert len(all_routes) >= 3


def test_django_route_handlers(django_result):
    handler_names = {r.handler_name for r in django_result.all_routes}
    assert "article_list" in handler_names or "article_detail" in handler_names


# --- Entry point detection ---


def test_entry_point_detected_by_filename(plain_result):
    assert any("main.py" in ep for ep in plain_result.entry_points)


def test_entry_point_detected_by_filename_django(django_result):
    assert any("manage.py" in ep for ep in django_result.entry_points)


# --- Framework detection ---


def test_frameworks_detected(fastapi_result):
    assert "FastAPI" in fastapi_result.frameworks
    assert "SQLAlchemy" in fastapi_result.frameworks
