"""Static generator for Mermaid classDiagram."""

from __future__ import annotations

from spartastruct.analyzer.base import AnalysisResult

_VIS_PREFIX = {"public": "+", "protected": "#", "private": "-"}
_INIT_CONFIG = '%%{init: {"maxTextSize": 200000} }%%'


def generate(result: AnalysisResult) -> str:
    """Generate a Mermaid classDiagram from the analysis result.

    Args:
        result: The full analysis result containing class information.

    Returns:
        A Mermaid classDiagram string (without fences).
    """
    classes = result.all_classes
    if not classes:
        return 'classDiagram\n    note "No classes found in this project"'

    lines = [_INIT_CONFIG, "classDiagram"]

    for cls in classes:
        lines.append(f"    class {_safe_name(cls.name)} {{")
        if cls.is_abstract:
            lines.append("        <<abstract>>")
        elif cls.is_dataclass:
            lines.append("        <<dataclass>>")
        elif cls.orm_type:
            lines.append(f"        <<{cls.orm_type}>>")

        for attr in cls.attributes:
            prefix = _VIS_PREFIX.get(attr.visibility, "+")
            lines.append(f"        {prefix}{attr.type} {attr.name}")

        for method in cls.methods:
            prefix = _VIS_PREFIX.get(method.visibility, "+")
            params_str = ", ".join(
                f"{p.name}: {p.type}" if p.type != "Any" else p.name for p in method.params
            )
            ret = f" {method.return_type}" if method.return_type not in ("None", "Any", "") else ""
            async_prefix = "async " if method.is_async else ""
            lines.append(f"        {prefix}{async_prefix}{method.name}({params_str}){ret}")

        lines.append("    }")

    # Inheritance relationships
    for cls in classes:
        for base in cls.bases:
            base_clean = _safe_name(base.split(".")[-1])
            # Only draw if base is a known class in the project
            known = {_safe_name(c.name) for c in classes}
            if base_clean in known:
                lines.append(f"    {base_clean} <|-- {_safe_name(cls.name)}")

    return "\n".join(lines)


def _safe_name(name: str) -> str:
    """Sanitize a name for use as a Mermaid identifier."""
    return name.replace("-", "_").replace(".", "_").replace(" ", "_")
