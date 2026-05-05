"""Tests for the six static Mermaid diagram generators."""

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
    class_diagram,
    dfd,
    er_diagram,
    flowchart,
    function_graph,
    module_graph,
)
from spartastruct.utils.file_walker import walk_project

FASTAPI_DIR = Path(__file__).parent / "fixtures" / "sample_fastapi"
PLAIN_DIR = Path(__file__).parent / "fixtures" / "sample_plain"


@pytest.fixture
def empty_result():
    return AnalysisResult()


@pytest.fixture
def plain_result():
    files, warnings = walk_project(PLAIN_DIR)
    return PythonAnalyzer(PLAIN_DIR).analyze(files, warnings)


@pytest.fixture
def fastapi_result():
    files, warnings = walk_project(FASTAPI_DIR)
    return PythonAnalyzer(FASTAPI_DIR).analyze(files, warnings)


# --- Class Diagram ---

def test_class_diagram_starts_with_header(plain_result):
    output = class_diagram.generate(plain_result)
    assert output.startswith("classDiagram")


def test_class_diagram_contains_class_names(plain_result):
    output = class_diagram.generate(plain_result)
    assert "Shape" in output
    assert "Circle" in output


def test_class_diagram_empty_state(empty_result):
    output = class_diagram.generate(empty_result)
    assert "classDiagram" in output
    assert "No classes found" in output


def test_class_diagram_abstract_stereotype(plain_result):
    output = class_diagram.generate(plain_result)
    assert "<<abstract>>" in output


def test_class_diagram_dataclass_stereotype(plain_result):
    output = class_diagram.generate(plain_result)
    assert "<<dataclass>>" in output


def test_class_diagram_inheritance(plain_result):
    output = class_diagram.generate(plain_result)
    assert "<|--" in output


# --- ER Diagram ---

def test_er_diagram_starts_with_header(fastapi_result):
    output = er_diagram.generate(fastapi_result)
    assert output.startswith("erDiagram")


def test_er_diagram_contains_model_names(fastapi_result):
    output = er_diagram.generate(fastapi_result)
    assert "User" in output
    assert "Post" in output


def test_er_diagram_empty_state(empty_result):
    output = er_diagram.generate(empty_result)
    assert "erDiagram" in output
    assert "No ORM models" in output


# --- DFD ---

def test_dfd_starts_with_header(fastapi_result):
    output = dfd.generate(fastapi_result)
    assert output.startswith("flowchart LR")


def test_dfd_contains_client_node(fastapi_result):
    output = dfd.generate(fastapi_result)
    assert "Client" in output


def test_dfd_empty_fallback(empty_result):
    output = dfd.generate(empty_result)
    assert "flowchart LR" in output
    assert "EntryPoint" in output or "Client" in output


# --- Flowchart ---

def test_flowchart_starts_with_header(fastapi_result):
    output = flowchart.generate(fastapi_result)
    assert output.startswith("flowchart TD")


def test_flowchart_has_start_node(fastapi_result):
    output = flowchart.generate(fastapi_result)
    assert "Start" in output


def test_flowchart_empty_state(empty_result):
    output = flowchart.generate(empty_result)
    assert "flowchart TD" in output
    assert "No entry point" in output


def test_flowchart_web_lifecycle(fastapi_result):
    output = flowchart.generate(fastapi_result)
    assert "Request" in output or "Server" in output


# --- Function Graph ---

def test_function_graph_starts_with_header(plain_result):
    output = function_graph.generate(plain_result)
    assert output.startswith("graph LR")


def test_function_graph_has_subgraphs(plain_result):
    output = function_graph.generate(plain_result)
    assert "subgraph" in output


def test_function_graph_empty(empty_result):
    output = function_graph.generate(empty_result)
    assert "graph LR" in output


# --- Module Graph ---

def test_module_graph_starts_with_header(plain_result):
    output = module_graph.generate(plain_result)
    assert output.startswith("graph TD")


def test_module_graph_has_file_nodes(plain_result):
    output = module_graph.generate(plain_result)
    assert "main.py" in output or "shapes.py" in output


def test_module_graph_empty_state(empty_result):
    output = module_graph.generate(empty_result)
    assert "graph TD" in output
