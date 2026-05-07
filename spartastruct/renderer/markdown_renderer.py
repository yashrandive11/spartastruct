"""Markdown renderer: turns DiagramSections into a single ARCHITECTURE.md."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from spartastruct.analyzer.base import AnalysisResult


@dataclass
class DiagramSection:
    key: str  # "class_diagram", "er_diagram", etc.
    title: str  # "Class Diagram"
    description: str  # from LLM or ""
    mermaid: str  # Mermaid source — LLM-enriched when available
    static_mermaid: str = ""  # original static diagram, used as fallback on render failure


_DIAGRAM_TITLES: dict[str, str] = {
    "class_diagram": "Class Diagram",
    "er_diagram": "Entity Relationship Diagram",
    "dfd": "Data Flow Diagram",
    "flowchart": "Application Logic",
    "function_graph": "Function Call Graph",
    "module_graph": "Module Dependency Graph",
    "sequence_diagram": "Sequence Diagram",
    "state_diagram": "State Diagram",
    "api_map": "API Endpoint Map",
    "component_map": "Component Map",
    "event_flow": "Event & Message Flow",
}

_DIAGRAM_ORDER = [
    "class_diagram",
    "er_diagram",
    "dfd",
    "flowchart",
    "function_graph",
    "module_graph",
    "sequence_diagram",
    "state_diagram",
    "api_map",
    "component_map",
    "event_flow",
]


def make_sections(
    static_diagrams: dict[str, str],
    llm_results: dict[str, tuple[str, str]] | None = None,
) -> list[DiagramSection]:
    """Build DiagramSection list from static diagrams and optional LLM results.

    Args:
        static_diagrams: mapping of diagram_key -> static mermaid string
        llm_results: mapping of diagram_key -> (description, enhanced_mermaid)
    """
    sections = []
    for key in _DIAGRAM_ORDER:
        static = static_diagrams.get(key, "")
        if llm_results and key in llm_results:
            description, mermaid = llm_results[key]
        else:
            description, mermaid = "", static
        sections.append(
            DiagramSection(
                key=key,
                title=_DIAGRAM_TITLES[key],
                description=description,
                mermaid=mermaid,
                static_mermaid=static,
            )
        )
    return sections


def render(
    result: AnalysisResult,
    sections: list[DiagramSection],
    project_name: str,
) -> str:
    """Render the full ARCHITECTURE.md content.

    Loads the Jinja2 template from the package's templates/ directory.
    """
    templates_dir = Path(__file__).parent.parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("structure.md.j2")
    return template.render(
        project_name=project_name,
        sections=sections,
        result=result,
    )
