"""Placeholder for API Map diagram generator."""

from __future__ import annotations

from spartastruct.analyzer.base import AnalysisResult

_INIT = '%%{init: {"maxTextSize": 200000} }%%'


def generate(result: AnalysisResult) -> str:
    """Generate an API Map diagram.

    Args:
        result: The full analysis result.

    Returns:
        A Mermaid diagram string (without fences).
    """
    return _INIT + "\ngraph LR\n    A[API Map]"
