"""Tests for the six static Mermaid diagram generators."""

from __future__ import annotations

from pathlib import Path

import pytest

from spartastruct.analyzer.base import (
    AnalysisResult,
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
    assert "classDiagram" in output


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
    assert "erDiagram" in output


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
    assert "flowchart LR" in output


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
    assert "flowchart TD" in output


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
    assert "graph LR" in output


def test_function_graph_has_subgraphs(plain_result):
    output = function_graph.generate(plain_result)
    assert "subgraph" in output


def test_function_graph_empty(empty_result):
    output = function_graph.generate(empty_result)
    assert "graph LR" in output


# --- Module Graph ---


def test_module_graph_starts_with_header(plain_result):
    output = module_graph.generate(plain_result)
    assert "graph TD" in output


def test_module_graph_has_file_nodes(plain_result):
    output = module_graph.generate(plain_result)
    assert "main.py" in output or "shapes.py" in output


def test_module_graph_empty_state(empty_result):
    output = module_graph.generate(empty_result)
    assert "graph TD" in output


def test_function_graph_has_spacing_config(plain_result):
    out = function_graph.generate(plain_result)
    assert "%%{init" in out
    assert "nodeSpacing" in out


def test_function_graph_no_edge_labels(plain_result):
    out = function_graph.generate(plain_result)
    assert "-->|" not in out


def test_function_graph_deduplicates_edges():
    """Same caller→callee pair must appear only once even if called N times."""
    from spartastruct.analyzer.base import FileResult, FunctionInfo

    fn_a = FunctionInfo(name="a", calls=["b", "b", "b"])
    fn_b = FunctionInfo(name="b")
    fr = FileResult(path="mod.py", functions=[fn_a, fn_b])
    result = AnalysisResult(files_analyzed=[fr])
    out = function_graph.generate(result)
    edge_lines = [
        line.strip()
        for line in out.splitlines()
        if "-->" in line and "%%{" not in line and "subgraph" not in line
    ]
    assert len(edge_lines) == 1


def test_module_graph_has_spacing_config(fastapi_result):
    out = module_graph.generate(fastapi_result)
    assert "%%{init" in out
    assert "nodeSpacing" in out


def test_module_graph_deduplicates_edges():
    """Same src→dst module edge must appear only once."""
    from spartastruct.analyzer.base import FileResult, ImportInfo

    fr_a = FileResult(path="a.py", imports=ImportInfo(local=["b", "b"]))
    fr_b = FileResult(path="b.py")
    result = AnalysisResult(files_analyzed=[fr_a, fr_b])
    out = module_graph.generate(result)
    edge_lines = [line.strip() for line in out.splitlines() if "-->" in line and "%%{" not in line]
    assert edge_lines.count("mod0 --> mod1") == 1


def test_function_graph_respects_max_out_edges():
    """Outgoing edges from a single node must be capped at _MAX_OUT_EDGES (8)."""
    import re

    from spartastruct.analyzer.base import FileResult, FunctionInfo

    # caller calls 12 distinct callees; all 12 also exist as functions in the
    # same file so they all resolve to known node IDs — exercising the cap.
    callee_names = [f"callee_{i}" for i in range(12)]
    caller = FunctionInfo(name="caller", calls=callee_names)
    callees = [FunctionInfo(name=name) for name in callee_names]
    fr = FileResult(path="big.py", functions=[caller, *callees])
    result = AnalysisResult(files_analyzed=[fr])
    out = function_graph.generate(result)

    # Find the caller's node ID dynamically by locating its label in the output.
    caller_id = None
    for line in out.split("\n"):
        m = re.search(r'(fn\d+)\["caller\(\)"', line)
        if m:
            caller_id = m.group(1)
            break
    assert caller_id is not None, "caller node not found in output"
    outgoing = [line for line in out.split("\n") if re.match(rf"    {caller_id} -->", line)]
    assert len(outgoing) == 8


def test_function_graph_cap_applies_to_methods():
    """_MAX_OUT_EDGES cap must also apply to class methods."""
    import re

    from spartastruct.analyzer.base import ClassInfo, FileResult, MethodInfo

    # Build a class with a 'caller' method that calls 12 distinct 'callee_N' methods.
    # For method-to-method resolution, calls must use the qualified "ClassName.method"
    # key because function_graph looks up callee via node_ids.get(call).
    callee_methods = [
        MethodInfo(name=f"callee_{i}", is_async=False, calls=[], decorators=[]) for i in range(12)
    ]
    caller_method = MethodInfo(
        name="caller",
        is_async=False,
        calls=[f"MyService.callee_{i}" for i in range(12)],
        decorators=[],
    )
    cls = ClassInfo(
        name="MyService",
        bases=[],
        methods=[caller_method] + callee_methods,
    )
    fr = FileResult(path="service.py", functions=[], classes=[cls])
    result = AnalysisResult(files_analyzed=[fr])
    out = function_graph.generate(result)

    # Find the caller method's node ID dynamically.
    caller_id = None
    for line in out.split("\n"):
        m = re.search(r'(fn\d+)\["MyService\.caller\(\)"', line)
        if m:
            caller_id = m.group(1)
            break
    assert caller_id is not None, "caller method node not found"
    outgoing = [line for line in out.split("\n") if re.match(rf"    {caller_id} -->", line)]
    assert len(outgoing) == 8
