"""Tests for the LLM client utilities."""

from __future__ import annotations

from unittest.mock import patch

import litellm

from spartastruct.analyzer.base import AnalysisResult, ClassInfo, FileResult, ImportInfo
from spartastruct.llm.client import (
    _MAX_CLASSES,
    _MAX_FILES,
    _MAX_ROUTES,
    _parse_llm_response,
    _result_to_json,
    call_llm,
    get_llm_failures,
)


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


def test_call_llm_retries_on_rate_limit_then_succeeds():
    from unittest.mock import MagicMock
    success_response = MagicMock()
    success_response.choices[0].message.content = "ok"
    calls = []

    def fake_completion(**kwargs):
        calls.append(1)
        if len(calls) < 2:
            raise litellm.RateLimitError("rate limit", llm_provider="anthropic", model="haiku")
        return success_response

    with patch("litellm.completion", side_effect=fake_completion):
        with patch("time.sleep"):  # don't actually wait in tests
            result = call_llm("prompt", "system", "model", {})

    assert result == "ok"
    assert len(calls) == 2
    assert get_llm_failures() == []  # no failure recorded on successful retry


def test_call_llm_gives_up_after_max_retries():
    with patch("litellm.completion", side_effect=litellm.RateLimitError(
        "rate limit", llm_provider="anthropic", model="haiku"
    )):
        with patch("time.sleep"):
            result = call_llm("prompt", "system", "model", {})

    assert result == ""
    failures = get_llm_failures()
    assert len(failures) == 1
    assert "Rate limit hit" in failures[0]


def _make_result(n_files: int = 1, n_classes: int = 0) -> AnalysisResult:
    files = [
        FileResult(path=f"mod{i}.py", classes=[], functions=[], imports=ImportInfo(), routes=[])
        for i in range(n_files)
    ]
    classes_per_file = n_classes // max(n_files, 1)
    for fr in files:
        for j in range(classes_per_file):
            fr.classes.append(ClassInfo(name=f"C{j}"))
    return AnalysisResult(files_analyzed=files)


def test_result_to_json_small_project_no_truncation_note():
    result = _make_result(n_files=5, n_classes=5)
    payload = _result_to_json(result)
    assert "note" not in payload


def test_result_to_json_caps_files():
    result = _make_result(n_files=_MAX_FILES + 50)
    import json
    data = json.loads(_result_to_json(result))
    assert len(data["files"]) == _MAX_FILES
    assert "note" in data


def test_result_to_json_caps_classes():
    result = _make_result(n_files=1, n_classes=_MAX_CLASSES + 20)
    import json
    data = json.loads(_result_to_json(result))
    assert len(data["classes"]) == _MAX_CLASSES
    assert "note" in data
