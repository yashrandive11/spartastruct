"""Tests for the LLM client utilities."""

from __future__ import annotations

from unittest.mock import patch

from spartastruct.llm.client import _parse_llm_response, call_llm, get_llm_failures


def test_parse_llm_response_extracts_mermaid():
    response = "Shows three classes.\n\n```mermaid\nclassDiagram\n    A --> B\n```"
    desc, mermaid = _parse_llm_response(response, "fallback")
    assert "classDiagram" in mermaid
    assert "A --> B" in mermaid
    assert desc == "Shows three classes."


def test_parse_llm_response_falls_back_when_no_fence():
    desc, mermaid = _parse_llm_response("Some text without mermaid", "fallback_diagram")
    assert mermaid == "fallback_diagram"
    assert desc == ""


def test_get_llm_failures_clears_after_read():
    # Inject a failure via a bad call
    with patch("litellm.completion", side_effect=RuntimeError("bad")):
        call_llm("prompt", "system", "model", {})
    failures = get_llm_failures()
    assert len(failures) == 1
    assert "bad" in failures[0]
    # Second call should be empty — list was cleared
    assert get_llm_failures() == []


def test_parse_llm_response_strips_whitespace():
    response = "   Description here.   \n```mermaid\n  graph LR\n  A-->B\n```"
    desc, mermaid = _parse_llm_response(response, "fb")
    assert desc == "Description here."
    assert mermaid.startswith("graph LR")
