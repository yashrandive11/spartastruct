"""Static generator for API Endpoint Map (flowchart LR)."""

from __future__ import annotations

from spartastruct.analyzer.base import AnalysisResult

_METHOD_COLORS = {
    "GET": "fill:#d4edda,stroke:#28a745",
    "POST": "fill:#cce5ff,stroke:#004085",
    "PUT": "fill:#fff3cd,stroke:#856404",
    "PATCH": "fill:#fff3cd,stroke:#856404",
    "DELETE": "fill:#f8d7da,stroke:#721c24",
}


def generate(result: AnalysisResult) -> str:
    """Generate a Mermaid flowchart LR grouping all routes by resource.

    Groups routes by the first path segment (resource). Each route is a
    node showing method + path + handler name. HTTP methods are colour-coded
    via classDef.

    Args:
        result: The full analysis result.

    Returns:
        A Mermaid flowchart LR string (without fences).
    """
    lines = ['%%{init: {"maxTextSize": 200000} }%%', "flowchart LR"]

    for method, style in _METHOD_COLORS.items():
        lines.append(f"    classDef {method.lower()} {style}")

    routes = result.all_routes
    if not routes:
        lines.append('    noroutes["No routes detected"]')
        return "\n".join(lines)

    # Group by resource (first non-empty, non-param path segment)
    groups: dict[str, list] = {}
    for route in routes:
        parts = [p for p in route.path.split("/") if p and not p.startswith("{")]
        resource = parts[0] if parts else "root"
        groups.setdefault(resource, []).append(route)

    lines.append('    Client(["Client"])')

    for g_idx, (resource, group_routes) in enumerate(groups.items()):
        sg_id = f"sg_{g_idx}"
        lines.append(f'    subgraph {sg_id}["/{resource}"]')
        for r_idx, route in enumerate(group_routes):
            node_id = f"r_{g_idx}_{r_idx}"
            label = f"{route.method} {route.path}\\n{route.handler_name}"
            method_class = route.method.lower() if route.method in _METHOD_COLORS else "get"
            lines.append(f'        {node_id}["{label}"]:::{method_class}')
        lines.append("    end")
        lines.append(f"    Client --> {sg_id}")

    return "\n".join(lines)
