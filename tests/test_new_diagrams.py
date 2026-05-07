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
