"""Static generator for Mermaid Data Flow Diagram (flowchart LR)."""

from __future__ import annotations

from spartastruct.analyzer.base import AnalysisResult


def generate(result: AnalysisResult) -> str:
    """Generate a Mermaid flowchart LR data flow diagram.

    Args:
        result: The full analysis result.

    Returns:
        A Mermaid flowchart LR string (without fences).
    """
    lines = ['%%{init: {"maxTextSize": 200000} }%%', "flowchart LR"]

    routes = result.all_routes
    orm_models = result.orm_models

    # External entity
    lines.append('    Client(["External Client"])')

    if routes:
        # Group routes as process nodes
        for i, route in enumerate(routes[:10]):  # cap at 10 for readability
            node_id = f"route_{i}"
            label = f"{route.method} {route.path}"
            lines.append(f'    {node_id}["{label}\\n{route.handler_name}"]')
            lines.append(f"    Client -->|request| {node_id}")

        # Service layer (if detected via frameworks)
        if any(f in result.frameworks for f in ["FastAPI", "Flask", "Django"]):
            lines.append('    ServiceLayer["Service Layer"]')
            for i in range(min(len(routes), 10)):
                lines.append(f"    route_{i} -->|call| ServiceLayer")

        # Data store
        if orm_models:
            lines.append('    DB[("Database")]')
            lines.append("    ServiceLayer -->|query| DB")
            lines.append("    DB -->|result| ServiceLayer")
            for i in range(min(len(routes), 10)):
                lines.append(f"    ServiceLayer -->|response| route_{i}")
            lines.append("    route_0 -->|response| Client")
        else:
            lines.append("    ServiceLayer -->|response| Client")
    else:
        # Generic fallback for projects without routes
        lines.append('    EntryPoint["Entry Point"]')
        lines.append('    Logic["Application Logic"]')
        lines.append("    Client -->|input| EntryPoint")
        lines.append("    EntryPoint -->|calls| Logic")
        if orm_models:
            lines.append('    DB[("Database")]')
            lines.append("    Logic -->|query| DB")
            lines.append("    DB -->|data| Logic")
        lines.append("    Logic -->|output| Client")

    return "\n".join(lines)
