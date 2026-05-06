"""LLM enrichment client using litellm."""

from __future__ import annotations

import json
import os
import re

import litellm

from spartastruct.analyzer.base import AnalysisResult
from spartastruct.llm.prompts import DIAGRAM_PROMPTS

litellm.suppress_debug_info = True

_llm_failures: list[str] = []


def get_llm_failures() -> list[str]:
    """Return and clear the accumulated LLM failure messages."""
    failures = _llm_failures[:]
    _llm_failures.clear()
    return failures


def _set_api_key_env_vars(api_keys: dict[str, str]) -> None:
    key_map = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "groq": "GROQ_API_KEY",
        "mistral": "MISTRAL_API_KEY",
        "cohere": "COHERE_API_KEY",
        "together": "TOGETHER_API_KEY",
        "ollama": "OLLAMA_API_BASE",
    }
    for provider, value in api_keys.items():
        env_var = key_map.get(provider.lower())
        if env_var:
            os.environ[env_var] = value


def call_llm(
    prompt: str,
    system_prompt: str,
    model: str,
    api_keys: dict[str, str],
) -> str:
    """Call the LLM and return the text response, or "" on any failure."""
    _set_api_key_env_vars(api_keys)
    try:
        response = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content or ""
    except Exception as exc:
        _llm_failures.append(str(exc))
        return ""


def _parse_llm_response(response: str, fallback_mermaid: str) -> tuple[str, str]:
    """Extract (description, mermaid) from LLM response text."""
    match = re.search(r"```mermaid\s*(.*?)```", response, re.DOTALL)
    if not match:
        return ("", fallback_mermaid)
    mermaid = match.group(1).strip()
    description = response[: match.start()].strip()
    return (description, mermaid)


def _result_to_json(result: AnalysisResult) -> str:
    """Serialize relevant parts of AnalysisResult to a compact JSON string."""
    data = {
        "frameworks": result.frameworks,
        "entry_points": result.entry_points,
        "classes": [
            {
                "name": c.name,
                "bases": c.bases,
                "is_abstract": c.is_abstract,
                "is_dataclass": c.is_dataclass,
                "orm_type": c.orm_type,
                "attributes": [{"name": a.name, "type": a.type} for a in c.attributes],
                "methods": [{"name": m.name, "return_type": m.return_type} for m in c.methods],
            }
            for c in result.all_classes
        ],
        "routes": [
            {"method": r.method, "path": r.path, "handler": r.handler_name}
            for r in result.all_routes
        ],
        "files": [fr.path for fr in result.files_analyzed],
    }
    return json.dumps(data, separators=(",", ":"))


def call_llm_for_diagram(
    diagram_type: str,
    static_mermaid: str,
    result: AnalysisResult,
    model: str,
    api_keys: dict[str, str],
) -> tuple[str, str]:
    """Enrich a static diagram via LLM.

    Returns:
        (description, mermaid) — both are "" / static_mermaid on failure.
    """
    system_prompt = DIAGRAM_PROMPTS.get(diagram_type, "")
    if not system_prompt:
        return ("", static_mermaid)

    parsed_json = _result_to_json(result)
    user_message = (
        f"Codebase structure:\n```json\n{parsed_json}\n```\n\n"
        f"Static diagram:\n```mermaid\n{static_mermaid}\n```\n\n"
        "Improve the diagram and provide a brief description."
    )

    response = call_llm(user_message, system_prompt, model, api_keys)
    if not response:
        return ("", static_mermaid)
    return _parse_llm_response(response, static_mermaid)
