"""Placeholder for State Diagram generator."""

from __future__ import annotations

from spartastruct.analyzer.base import AnalysisResult

_INIT = '%%{init: {"maxTextSize": 200000} }%%'


def generate(result: AnalysisResult) -> str:
    """Generate a State Diagram.

    Args:
        result: The full analysis result.

    Returns:
        A Mermaid diagram string (without fences).
    """
    return _INIT + "\nstateDiagram-v2\n    [*] --> State"
