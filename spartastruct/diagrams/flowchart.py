"""Static generator for Application Logic Flowchart (flowchart TD)."""

from __future__ import annotations

from spartastruct.analyzer.base import AnalysisResult


def generate(result: AnalysisResult) -> str:
    """Generate a Mermaid flowchart TD showing application logic flow.

    Args:
        result: The full analysis result.

    Returns:
        A Mermaid flowchart TD string (without fences).
    """
    lines = ["flowchart TD"]

    entry_points = result.entry_points
    frameworks = result.frameworks
    routes = result.all_routes

    if not entry_points and not frameworks:
        lines.append('    NoEntry(["No entry point detected"])')
        return "\n".join(lines)

    # Start node
    ep_label = entry_points[0] if entry_points else "Application"
    lines.append(f'    Start(["Start: {ep_label}"])')

    is_web = any(f in frameworks for f in ["FastAPI", "Flask", "Django"])

    if is_web:
        lines.append('    Init["Initialize App / Load Config"]')
        lines.append('    Start --> Init')
        lines.append('    Server["Start Server / Bind Port"]')
        lines.append('    Init --> Server')
        lines.append('    Request["Receive HTTP Request"]')
        lines.append('    Server --> Request')
        lines.append('    Routing{"Route Match?"}')
        lines.append('    Request --> Routing')

        if routes:
            for i, route in enumerate(routes[:5]):
                node_id = f"handler_{i}"
                label = f"{route.method} {route.path}"
                lines.append(f'    {node_id}["{label}"]')
                lines.append(f"    Routing -->|yes| {node_id}")
            lines.append('    handler_0 --> Response["Return Response"]')
        else:
            lines.append('    Handler["Route Handler"]')
            lines.append('    Routing -->|yes| Handler')
            lines.append('    Handler --> Response["Return Response"]')

        lines.append('    Routing -->|no| NotFound["404 Not Found"]')
        lines.append('    Response --> End(["End"])')
        lines.append('    NotFound --> End')
    else:
        # Plain Python entry point flow
        lines.append('    Main["Main Function / Script Body"]')
        lines.append('    Start --> Main')

        # Show top-level functions from entry file as steps
        entry_funcs = []
        for fr in result.files_analyzed:
            if fr.path in entry_points or any(ep in fr.path for ep in entry_points):
                entry_funcs = fr.functions[:4]
                break

        if entry_funcs:
            prev = "Main"
            for i, fn in enumerate(entry_funcs):
                node_id = f"fn_{i}"
                lines.append(f'    {node_id}["{fn.name}()"]')
                lines.append(f"    {prev} --> {node_id}")
                prev = node_id
            lines.append(f'    {prev} --> End(["End"])')
        else:
            lines.append('    Main --> End(["End"])')

    return "\n".join(lines)
