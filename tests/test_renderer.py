"""Tests for the markdown renderer."""

from __future__ import annotations

from spartastruct.analyzer.base import AnalysisResult, FileResult
from spartastruct.renderer.markdown_renderer import DiagramSection, make_sections, render


def test_make_sections_static_only():
    static = {"class_diagram": 'classDiagram\n    note "test"', "er_diagram": "erDiagram"}
    sections = make_sections(static)
    assert len(sections) == 11
    cd = next(s for s in sections if s.key == "class_diagram")
    assert cd.title == "Class Diagram"
    assert cd.mermaid == 'classDiagram\n    note "test"'
    assert cd.description == ""


def test_make_sections_with_llm():
    static = {"class_diagram": "classDiagram"}
    llm = {"class_diagram": ("Shows three classes.", "classDiagram\n    A --> B")}
    sections = make_sections(static, llm)
    cd = next(s for s in sections if s.key == "class_diagram")
    assert cd.description == "Shows three classes."
    assert "A --> B" in cd.mermaid


def test_render_contains_headings():
    result = AnalysisResult(files_analyzed=[FileResult(path="main.py")])
    sections = [
        DiagramSection(
            key="class_diagram",
            title="Class Diagram",
            description="",
            mermaid="classDiagram",
        ),
    ]
    output = render(result, sections, project_name="MyApp")
    assert "# MyApp" in output
    assert "## Class Diagram" in output
    assert "```mermaid" in output
    assert "classDiagram" in output


def test_render_includes_description():
    result = AnalysisResult()
    sections = [
        DiagramSection(
            key="er_diagram",
            title="ER Diagram",
            description="Illustrates the User-Post relationship.",
            mermaid="erDiagram",
        )
    ]
    output = render(result, sections, project_name="Blog")
    assert "Illustrates the User-Post relationship." in output


def test_render_file_count():
    files = [FileResult(path=f"mod{i}.py") for i in range(3)]
    result = AnalysisResult(files_analyzed=files, frameworks=["FastAPI"])
    sections = [DiagramSection(key="dfd", title="DFD", description="", mermaid="flowchart LR")]
    output = render(result, sections, project_name="API")
    assert "3 file(s)" in output
    assert "FastAPI" in output


def test_render_skips_empty_mermaid():
    result = AnalysisResult()
    sections = [
        DiagramSection(key="class_diagram", title="Class Diagram", description="", mermaid=""),
    ]
    output = render(result, sections, project_name="Empty")
    assert "## Class Diagram" in output
    # Empty mermaid should not produce a broken fence
    assert "```mermaid\n\n```" not in output
