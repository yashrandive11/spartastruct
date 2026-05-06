"""Static generator for Mermaid erDiagram."""

from __future__ import annotations

from spartastruct.analyzer.base import AnalysisResult

# SQLAlchemy/Django type → SQL type mapping
_TYPE_MAP = {
    "Integer": "int",
    "String": "string",
    "Text": "string",
    "Boolean": "boolean",
    "Float": "float",
    "DateTime": "datetime",
    "Date": "date",
    "CharField": "string",
    "TextField": "string",
    "IntegerField": "int",
    "BooleanField": "boolean",
    "EmailField": "string",
    "SlugField": "string",
    "DateTimeField": "datetime",
    "DateField": "date",
    "ForeignKey": "int",
    "ManyToManyField": "int",
    "OneToOneField": "int",
}

_FK_ATTRS = frozenset({"ForeignKey", "ManyToManyField", "OneToOneField", "relationship"})
_PK_NAMES = frozenset({"id", "pk"})


def generate(result: AnalysisResult) -> str:
    """Generate a Mermaid erDiagram from ORM models in the analysis result.

    Args:
        result: The full analysis result.

    Returns:
        A Mermaid erDiagram string (without fences).
    """
    models = result.orm_models
    if not models:
        return 'erDiagram\n    NOTE { string message "No ORM models detected" }'

    lines = ['%%{init: {"maxTextSize": 200000} }%%', "erDiagram"]

    for model in models:
        lines.append(f"    {model.name} {{")
        for attr in model.attributes:
            default_type = attr.type.lower() if attr.type != "Any" else "string"
            sql_type = _TYPE_MAP.get(attr.type, default_type)
            marker = ""
            if attr.name in _PK_NAMES or attr.name.endswith("_id") and attr.name == "id":
                marker = " PK"
            elif attr.type in _FK_ATTRS or attr.name.endswith("_id"):
                marker = " FK"
            lines.append(f"        {sql_type} {attr.name}{marker}")
        lines.append("    }")

    # Draw relationships between models
    model_names = {m.name for m in models}
    for model in models:
        for attr in model.attributes:
            if attr.type in ("ForeignKey", "OneToOneField", "ManyToManyField"):
                # We can't easily resolve the target without more context, skip
                pass
            # Look for relationship() calls — type will be the related class name
            if attr.type in model_names and attr.type != model.name:
                lines.append(f"    {model.name} }}o--|| {attr.type} : has")

    return "\n".join(lines)
