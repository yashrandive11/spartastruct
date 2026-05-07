"""Static generator for Component / Service Map (graph TD)."""

from __future__ import annotations

from spartastruct.analyzer.base import AnalysisResult

# Suffix → layer name mapping (checked against lowercase class name)
_LAYER_SUFFIXES: list[tuple[tuple[str, ...], str]] = [
    (("controller", "router", "view", "handler"), "Controllers"),
    (("service", "manager", "facade"), "Services"),
    (("repository", "repo", "dao", "store"), "Repositories"),
    (("model", "entity", "schema"), "Models"),
    (("util", "utils", "helper", "helpers", "middleware"), "Utils"),
]


def _classify_class(name: str) -> str | None:
    lower = name.lower()
    for suffixes, layer in _LAYER_SUFFIXES:
        if any(lower.endswith(s) or lower.startswith(s) for s in suffixes):
            return layer
    return None


def generate(result: AnalysisResult) -> str:
    """Generate a Mermaid graph TD showing logical component layers.

    Groups classes by naming convention into Controllers, Services,
    Repositories, Models, and Utils layers. Draws dependency arrows
    between layers. Falls back to framework nodes when no classes found.

    Args:
        result: The full analysis result.

    Returns:
        A Mermaid graph TD string (without fences).
    """
    lines = ['%%{init: {"maxTextSize": 200000} }%%', "graph TD"]
    lines.append("    classDef layer fill:#e8f4fd,stroke:#2196f3,font-weight:bold")
    lines.append("    classDef component fill:#f8f9fa,stroke:#6c757d")
    lines.append("    classDef external fill:#f8d7da,stroke:#dc3545")

    layers: dict[str, list[str]] = {}
    for cls in result.all_classes:
        layer = _classify_class(cls.name)
        if layer:
            layers.setdefault(layer, []).append(cls.name)

    if not layers:
        if result.frameworks:
            lines.append('    subgraph ext["External Dependencies"]')
            for i, fw in enumerate(result.frameworks[:8]):
                lines.append(f'        fw{i}["{fw}"]:::external')
            lines.append("    end")
            if result.entry_points:
                lines.append('    App["Application"]:::layer')
                lines.append("    App --> ext")
        else:
            lines.append('    App["Application (no components detected)"]')
        return "\n".join(lines)

    layer_node_ids: dict[str, str] = {}
    layer_order = ["Controllers", "Services", "Repositories", "Models", "Utils"]
    for layer in layer_order:
        if layer not in layers:
            continue
        sg_id = layer.lower()
        layer_node_ids[layer] = sg_id
        lines.append(f'    subgraph {sg_id}["{layer}"]')
        for i, cls_name in enumerate(layers[layer][:6]):
            lines.append(f'        {sg_id}_{i}["{cls_name}"]:::component')
        lines.append("    end")

    layer_pairs = [
        ("Controllers", "Services"),
        ("Services", "Repositories"),
        ("Repositories", "Models"),
    ]
    for src_layer, dst_layer in layer_pairs:
        if src_layer in layer_node_ids and dst_layer in layer_node_ids:
            lines.append(f"    {layer_node_ids[src_layer]} --> {layer_node_ids[dst_layer]}")

    if result.frameworks:
        lines.append('    subgraph external["External / Frameworks"]')
        for i, fw in enumerate(result.frameworks[:6]):
            lines.append(f'        extfw{i}["{fw}"]:::external')
        lines.append("    end")
        if "Repositories" in layer_node_ids:
            lines.append(f"    {layer_node_ids['Repositories']} --> external")
        elif "Services" in layer_node_ids:
            lines.append(f"    {layer_node_ids['Services']} --> external")

    return "\n".join(lines)
