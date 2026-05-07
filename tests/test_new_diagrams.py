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
