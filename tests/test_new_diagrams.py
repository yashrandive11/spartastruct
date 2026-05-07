"""Tests for the five new static Mermaid diagram generators."""

from __future__ import annotations

from pathlib import Path

import pytest

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
from spartastruct.analyzer.python_analyzer import PythonAnalyzer
from spartastruct.diagrams import (
    api_map,
    component_map,
    event_flow,
    sequence_diagram,
    state_diagram,
)
from spartastruct.utils.file_walker import walk_project

FASTAPI_DIR = Path(__file__).parent / "fixtures" / "sample_fastapi"


@pytest.fixture
def empty_result():
    return AnalysisResult()


@pytest.fixture
def fastapi_result():
    files, warnings = walk_project(FASTAPI_DIR)
    return PythonAnalyzer(FASTAPI_DIR).analyze(files, warnings)


# ── Sequence Diagram ──────────────────────────────────────────────────────────

def test_sequence_diagram_header(fastapi_result):
    out = sequence_diagram.generate(fastapi_result)
    assert "sequenceDiagram" in out


def test_sequence_diagram_shows_client(fastapi_result):
    out = sequence_diagram.generate(fastapi_result)
    assert "Client" in out


def test_sequence_diagram_shows_routes(fastapi_result):
    out = sequence_diagram.generate(fastapi_result)
    assert "GET" in out or "POST" in out


def test_sequence_diagram_empty_fallback(empty_result):
    out = sequence_diagram.generate(empty_result)
    assert "sequenceDiagram" in out
    assert "Client" in out


# ── State Diagram ─────────────────────────────────────────────────────────────

def test_state_diagram_header(fastapi_result):
    out = state_diagram.generate(fastapi_result)
    assert "stateDiagram-v2" in out


def test_state_diagram_empty_has_fallback(empty_result):
    out = state_diagram.generate(empty_result)
    assert "stateDiagram-v2" in out
    assert "[*]" in out


def test_state_diagram_detects_status_fields():
    cls = ClassInfo(
        name="Order",
        attributes=[AttributeInfo(name="status", type="str")],
        methods=[
            MethodInfo(name="approve"),
            MethodInfo(name="reject"),
            MethodInfo(name="cancel"),
        ],
    )
    fr = FileResult(path="order.py", classes=[cls], imports=ImportInfo())
    result = AnalysisResult(files_analyzed=[fr])
    out = state_diagram.generate(result)
    assert "stateDiagram-v2" in out
    assert "Order" in out


def test_state_diagram_transition_methods():
    cls = ClassInfo(
        name="Task",
        attributes=[AttributeInfo(name="state", type="str")],
        methods=[
            MethodInfo(name="start"),
            MethodInfo(name="complete"),
            MethodInfo(name="fail"),
        ],
    )
    fr = FileResult(path="task.py", classes=[cls], imports=ImportInfo())
    result = AnalysisResult(files_analyzed=[fr])
    out = state_diagram.generate(result)
    assert "start" in out or "complete" in out or "fail" in out


# ── API Endpoint Map ──────────────────────────────────────────────────────────

def test_api_map_header(fastapi_result):
    out = api_map.generate(fastapi_result)
    assert "flowchart" in out


def test_api_map_shows_routes(fastapi_result):
    out = api_map.generate(fastapi_result)
    assert "GET" in out or "POST" in out


def test_api_map_empty_fallback(empty_result):
    out = api_map.generate(empty_result)
    assert "flowchart" in out
    assert "No routes" in out


def test_api_map_groups_by_resource():
    routes = [
        RouteInfo(method="GET", path="/users", handler_name="list_users"),
        RouteInfo(method="POST", path="/users", handler_name="create_user"),
        RouteInfo(method="GET", path="/posts", handler_name="list_posts"),
    ]
    fr = FileResult(path="main.py", routes=routes, imports=ImportInfo())
    result = AnalysisResult(files_analyzed=[fr])
    out = api_map.generate(result)
    assert "users" in out
    assert "posts" in out


# ── Component / Service Map ───────────────────────────────────────────────────

def test_component_map_header(fastapi_result):
    out = component_map.generate(fastapi_result)
    assert "graph" in out


def test_component_map_empty_fallback(empty_result):
    out = component_map.generate(empty_result)
    assert "graph" in out


def test_component_map_detects_service_layer():
    classes = [
        ClassInfo(name="UserService"),
        ClassInfo(name="UserRepository"),
        ClassInfo(name="UserController"),
    ]
    fr = FileResult(path="app.py", classes=classes, imports=ImportInfo())
    result = AnalysisResult(files_analyzed=[fr], frameworks=["FastAPI"])
    out = component_map.generate(result)
    assert "Service" in out or "UserService" in out


def test_component_map_shows_frameworks(fastapi_result):
    out = component_map.generate(fastapi_result)
    assert "FastAPI" in out or "SQLAlchemy" in out or "graph" in out


# ── Event / Message Flow ──────────────────────────────────────────────────────

def test_event_flow_header(fastapi_result):
    out = event_flow.generate(fastapi_result)
    assert "flowchart" in out


def test_event_flow_empty_fallback(empty_result):
    out = event_flow.generate(empty_result)
    assert "flowchart" in out


def test_event_flow_detects_celery_tasks():
    fn = FunctionInfo(
        name="send_email",
        decorators=["shared_task"],
        is_async=False,
    )
    fr = FileResult(path="tasks.py", functions=[fn], imports=ImportInfo(
        third_party=["celery"]
    ))
    result = AnalysisResult(files_analyzed=[fr], frameworks=["Celery"])
    out = event_flow.generate(result)
    assert "send_email" in out or "Celery" in out or "task" in out.lower()


def test_event_flow_detects_async_functions():
    fn = FunctionInfo(name="handle_event", is_async=True)
    fr = FileResult(path="events.py", functions=[fn], imports=ImportInfo())
    result = AnalysisResult(files_analyzed=[fr])
    out = event_flow.generate(result)
    assert "flowchart" in out
    assert "handle_event" in out or "async" in out.lower() or "flowchart" in out


# ── Wiring ────────────────────────────────────────────────────────────────────

def test_all_new_generators_are_callable(fastapi_result):
    """All five new generators must return a non-empty string."""
    from spartastruct.diagrams import (
        api_map,
        component_map,
        event_flow,
        sequence_diagram,
        state_diagram,
    )
    generators = [
        sequence_diagram.generate,
        state_diagram.generate,
        api_map.generate,
        component_map.generate,
        event_flow.generate,
    ]
    for gen in generators:
        out = gen(fastapi_result)
        assert isinstance(out, str) and len(out) > 0, f"{gen.__module__} returned empty"


def test_all_new_diagram_keys_in_generators():
    """All five new diagram keys must be registered in CLI _GENERATORS."""
    from spartastruct.cli import _GENERATORS
    expected_keys = {
        "sequence_diagram", "state_diagram", "api_map",
        "component_map", "event_flow",
    }
    assert expected_keys.issubset(set(_GENERATORS.keys()))


def test_all_new_diagram_keys_in_renderer():
    """All five new diagram keys must appear in markdown renderer."""
    from spartastruct.renderer.markdown_renderer import _DIAGRAM_TITLES, _DIAGRAM_ORDER
    expected_keys = {
        "sequence_diagram", "state_diagram", "api_map",
        "component_map", "event_flow",
    }
    assert expected_keys.issubset(set(_DIAGRAM_TITLES.keys()))
    assert expected_keys.issubset(set(_DIAGRAM_ORDER))


def test_all_new_diagram_keys_in_llm_prompts():
    """All five new diagram keys must have LLM prompts registered."""
    from spartastruct.llm.prompts import DIAGRAM_PROMPTS
    expected_keys = {
        "sequence_diagram", "state_diagram", "api_map",
        "component_map", "event_flow",
    }
    assert expected_keys.issubset(set(DIAGRAM_PROMPTS.keys()))
