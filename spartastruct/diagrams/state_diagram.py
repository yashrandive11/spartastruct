"""Static generator for State Diagram (stateDiagram-v2)."""

from __future__ import annotations

from spartastruct.analyzer.base import AnalysisResult, ClassInfo

_STATE_ATTR_NAMES = frozenset({"status", "state", "stage", "phase", "mode", "step"})

_TRANSITION_KEYWORDS = frozenset({
    "approve", "reject", "cancel", "activate", "deactivate", "start", "stop",
    "complete", "fail", "pause", "resume", "submit", "publish", "archive",
    "open", "close", "enable", "disable", "lock", "unlock", "process", "finish",
})


def _has_state_field(cls: ClassInfo) -> bool:
    return any(a.name.lower() in _STATE_ATTR_NAMES for a in cls.attributes)


def _transition_methods(cls: ClassInfo) -> list[str]:
    return [
        m.name for m in cls.methods
        if any(kw in m.name.lower() for kw in _TRANSITION_KEYWORDS)
    ]


def generate(result: AnalysisResult) -> str:
    """Generate a Mermaid stateDiagram-v2 showing state machines in the project.

    Identifies classes with status/state attributes and transition methods.
    Falls back to a generic HTTP request lifecycle when none are found.

    Args:
        result: The full analysis result.

    Returns:
        A Mermaid stateDiagram-v2 string (without fences).
    """
    lines = ['%%{init: {"maxTextSize": 200000} }%%', "stateDiagram-v2"]

    state_classes = [c for c in result.all_classes if _has_state_field(c)]

    if not state_classes:
        lines.append("    [*] --> Received")
        lines.append("    Received --> Validating: validate()")
        lines.append("    Validating --> Processing: valid")
        lines.append("    Validating --> Rejected: invalid")
        lines.append("    Processing --> Completed: success")
        lines.append("    Processing --> Failed: error")
        lines.append("    Completed --> [*]")
        lines.append("    Rejected --> [*]")
        lines.append("    Failed --> [*]")
        return "\n".join(lines)

    for cls in state_classes[:3]:
        transitions = _transition_methods(cls)
        lines.append(f"    state {cls.name} {{")
        lines.append("        [*] --> Initialized")

        if transitions:
            prev = "Initialized"
            for method in transitions[:5]:
                state_name = method.capitalize() + "d" if not method.endswith("e") else method[:-1].capitalize() + "ed"
                lines.append(f"        {prev} --> {state_name}: {method}()")
                prev = state_name
            lines.append(f"        {prev} --> [*]")
        else:
            lines.append("        Initialized --> Active")
            lines.append("        Active --> [*]")

        lines.append("    }")

    return "\n".join(lines)
