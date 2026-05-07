"""LLM enrichment client using litellm."""

from __future__ import annotations

import json
import os
import re
import time

import litellm

from spartastruct.analyzer.base import AnalysisResult
from spartastruct.llm.prompts import DIAGRAM_PROMPTS

litellm.suppress_debug_info = True

_llm_failures: list[str] = []

_RATE_LIMIT_RETRIES = 3
_RATE_LIMIT_BACKOFF_BASE = 15  # seconds; doubles each retry (15 → 30 → 60)


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
    """Call the LLM and return the text response, or "" on any failure.

    Retries up to _RATE_LIMIT_RETRIES times with exponential backoff when a
    RateLimitError is returned, so large projects don't fail on the TPM cap.
    """
    _set_api_key_env_vars(api_keys)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]
    delay = _RATE_LIMIT_BACKOFF_BASE
    for attempt in range(_RATE_LIMIT_RETRIES + 1):
        try:
            response = litellm.completion(model=model, messages=messages)
            return response.choices[0].message.content or ""
        except litellm.RateLimitError:
            if attempt == _RATE_LIMIT_RETRIES:
                _llm_failures.append(
                    f"Rate limit hit after {_RATE_LIMIT_RETRIES} retries — skipping diagram enrichment."  # noqa: E501
                )
                return ""
            time.sleep(delay)
            delay *= 2
        except Exception as exc:
            _llm_failures.append(str(exc))
            return ""
    return ""  # unreachable


def _parse_llm_response(response: str, fallback_mermaid: str) -> tuple[str, str]:
    """Extract (description, mermaid) from LLM response text."""
    match = re.search(r"```mermaid\s*(.*?)```", response, re.DOTALL)
    if not match:
        return ("", fallback_mermaid)
    mermaid = match.group(1).strip()
    description = response[: match.start()].strip()
    return (description, mermaid)


_MAX_CLASSES = 80
_MAX_ROUTES = 50
_MAX_FILES = 100
_MAX_DIAGRAM_CHARS = 4_000


def _result_to_json(result: AnalysisResult) -> str:
    """Serialize a capped subset of AnalysisResult to a compact JSON string.

    Caps classes/routes/files so the prompt stays within LLM token limits on
    large projects (thousands of files).
    """
    all_classes = result.all_classes
    all_routes = result.all_routes
    all_files = [fr.path for fr in result.files_analyzed]

    truncated = (
        len(all_classes) > _MAX_CLASSES
        or len(all_routes) > _MAX_ROUTES
        or len(all_files) > _MAX_FILES
    )

    data: dict = {
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
            for c in all_classes[:_MAX_CLASSES]
        ],
        "routes": [
            {"method": r.method, "path": r.path, "handler": r.handler_name}
            for r in all_routes[:_MAX_ROUTES]
        ],
        "files": all_files[:_MAX_FILES],
    }
    if truncated:
        data["note"] = (
            f"Truncated: showing {min(len(all_classes), _MAX_CLASSES)}/{len(all_classes)} classes, "
            f"{min(len(all_routes), _MAX_ROUTES)}/{len(all_routes)} routes, "
            f"{min(len(all_files), _MAX_FILES)}/{len(all_files)} files."
        )
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
    diagram_snippet = static_mermaid[:_MAX_DIAGRAM_CHARS]
    if len(static_mermaid) > _MAX_DIAGRAM_CHARS:
        diagram_snippet += f"\n... (truncated, {len(static_mermaid)} chars total)"
    user_message = (
        f"Codebase structure:\n```json\n{parsed_json}\n```\n\n"
        f"Static diagram:\n```mermaid\n{diagram_snippet}\n```\n\n"
        "Improve the diagram and provide a brief description."
    )

    response = call_llm(user_message, system_prompt, model, api_keys)
    if not response:
        return ("", static_mermaid)
    return _parse_llm_response(response, static_mermaid)
