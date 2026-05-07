"""Static generator for Sequence Diagram (sequenceDiagram)."""

from __future__ import annotations

from spartastruct.analyzer.base import AnalysisResult


def generate(result: AnalysisResult) -> str:
    """Generate a Mermaid sequenceDiagram showing component interaction flow.

    Traces: Client → Route Handler → Service Layer → Repository/DB.
    Falls back to a generic request/response flow when no routes are present.

    Args:
        result: The full analysis result.

    Returns:
        A Mermaid sequenceDiagram string (without fences).
    """
    lines = ['%%{init: {"maxTextSize": 200000} }%%', "sequenceDiagram"]
    lines.append("    participant Client")

    routes = result.all_routes
    frameworks = result.frameworks
    is_web = any(f in frameworks for f in ["FastAPI", "Flask", "Django", "Express", "NestJS"])

    if not routes:
        # Generic fallback
        lines.append("    participant App")
        lines.append("    participant Logic")
        lines.append("    Client->>App: call")
        lines.append("    App->>Logic: process(input)")
        if result.orm_models:
            lines.append("    participant DB")
            lines.append("    Logic->>DB: query()")
            lines.append("    DB-->>Logic: result")
        lines.append("    Logic-->>App: output")
        lines.append("    App-->>Client: response")
        return "\n".join(lines)

    # Web app flow
    lines.append("    participant Router")

    service_classes = [
        c for c in result.all_classes
        if "service" in c.name.lower() or "handler" in c.name.lower()
        or "controller" in c.name.lower() or "manager" in c.name.lower()
    ]
    repo_classes = [
        c for c in result.all_classes
        if "repo" in c.name.lower() or "repository" in c.name.lower()
        or "dao" in c.name.lower() or "store" in c.name.lower()
    ]

    if service_classes:
        svc_name = service_classes[0].name
        lines.append(f"    participant {svc_name}")
    if repo_classes:
        repo_name = repo_classes[0].name
        lines.append(f"    participant {repo_name}")
    if result.orm_models:
        lines.append("    participant DB")

    # Pre-compute service and repo references once
    svc_name = service_classes[0].name if service_classes else None
    svc_method = "process()"
    if service_classes and service_classes[0].methods:
        svc_method = f"{service_classes[0].methods[0].name}()"
    repo_name = repo_classes[0].name if repo_classes else None

    shown_paths: set[str] = set()
    for route in routes:
        key = f"{route.method}:{route.path}"
        if key in shown_paths or len(shown_paths) >= 6:
            continue
        shown_paths.add(key)

        lines.append(f"    Client->>Router: {route.method} {route.path}")
        lines.append(f"    Router->>Router: {route.handler_name}()")

        if svc_name:
            lines.append(f"    Router->>{svc_name}: {svc_method}")
            if repo_name:
                repo_method = "find()" if "GET" in route.method else "save()"
                lines.append(f"    {svc_name}->>{repo_name}: {repo_method}")
                if result.orm_models:
                    lines.append(f"    {repo_name}->>DB: SQL query")
                    lines.append(f"    DB-->>{repo_name}: rows")
                lines.append(f"    {repo_name}-->>{svc_name}: data")
            lines.append(f"    {svc_name}->>Router: result")
        elif result.orm_models:
            lines.append("    Router->>DB: SQL query")
            lines.append("    DB-->>Router: rows")

        lines.append("    Router-->>Client: HTTP response")

    return "\n".join(lines)
