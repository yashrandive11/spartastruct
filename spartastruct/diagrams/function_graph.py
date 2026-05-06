"""Static generator for Function Interconnection Graph (graph LR)."""

from __future__ import annotations

from pathlib import Path

from spartastruct.analyzer.base import AnalysisResult

_MAX_FUNCTIONS = 50
_MAX_OUT_EDGES = 8  # max edges per source node to prevent star explosion

_INIT_CONFIG = '%%{init: {"flowchart": {"nodeSpacing": 60, "rankSpacing": 100}} }%%'


def generate(result: AnalysisResult) -> str:
    """Generate a Mermaid graph LR showing function call relationships.

    Groups nodes by file using subgraph blocks. Async functions get the
    :::async style class. Entry point functions get :::entrypoint.
    Edges are deduplicated and capped per source node to avoid visual clutter.

    Args:
        result: The full analysis result.

    Returns:
        A Mermaid graph LR string (without fences).
    """
    lines = [_INIT_CONFIG, "graph LR"]

    all_fn_count = sum(
        len(fr.functions) + sum(len(c.methods) for c in fr.classes) for fr in result.files_analyzed
    )
    if all_fn_count > _MAX_FUNCTIONS:
        lines.append(
            f"    %% Note: {all_fn_count} functions found — showing entry-point call graph only"
        )

    lines.append("    classDef async fill:#e8f4fd,stroke:#2196f3")
    lines.append("    classDef entrypoint fill:#fff3cd,stroke:#ff9800")

    entry_files = set(result.entry_points)
    node_ids: dict[str, str] = {}
    id_counter = [0]

    def make_id(qualified: str) -> str:
        if qualified not in node_ids:
            node_ids[qualified] = f"fn{id_counter[0]}"
            id_counter[0] += 1
        return node_ids[qualified]

    for fr in result.files_analyzed:
        stem = Path(fr.path).stem
        subgraph_id = _safe_id(stem)
        lines.append(f'    subgraph {subgraph_id}["{fr.path}"]')
        is_entry_file = fr.path in entry_files

        for fn in fr.functions:
            qname = f"{stem}.{fn.name}"
            nid = make_id(qname)
            label = ("async " if fn.is_async else "") + f"{fn.name}()"
            lines.append(f'        {nid}["{label}"]')
            if fn.is_async:
                lines.append(f"        {nid}:::async")
            if is_entry_file or fn.name in ("main", "run", "start"):
                lines.append(f"        {nid}:::entrypoint")

        for cls in fr.classes:
            for method in cls.methods:
                qname = f"{cls.name}.{method.name}"
                nid = make_id(qname)
                label = ("async " if method.is_async else "") + f"{cls.name}.{method.name}()"
                lines.append(f'        {nid}["{label}"]')
                if method.is_async:
                    lines.append(f"        {nid}:::async")

        lines.append("    end")

    # Edges — deduplicated and capped per source node
    seen_edges: set[tuple[str, str]] = set()
    out_edge_count: dict[str, int] = {}

    for fr in result.files_analyzed:
        stem = Path(fr.path).stem
        for fn in fr.functions:
            caller_id = node_ids.get(f"{stem}.{fn.name}")
            if not caller_id:
                continue
            for call in fn.calls:
                callee_id = node_ids.get(call) or node_ids.get(f"{stem}.{call}")
                if not callee_id:
                    continue
                edge = (caller_id, callee_id)
                if edge in seen_edges or out_edge_count.get(caller_id, 0) >= _MAX_OUT_EDGES:
                    continue
                seen_edges.add(edge)
                out_edge_count[caller_id] = out_edge_count.get(caller_id, 0) + 1
                lines.append(f"    {caller_id} --> {callee_id}")

        for cls in fr.classes:
            for method in cls.methods:
                caller_id = node_ids.get(f"{cls.name}.{method.name}")
                if not caller_id:
                    continue
                for call in method.calls:
                    callee_id = node_ids.get(call)
                    if not callee_id:
                        continue
                    edge = (caller_id, callee_id)
                    if edge in seen_edges or out_edge_count.get(caller_id, 0) >= _MAX_OUT_EDGES:
                        continue
                    seen_edges.add(edge)
                    out_edge_count[caller_id] = out_edge_count.get(caller_id, 0) + 1
                    lines.append(f"    {caller_id} --> {callee_id}")

    return "\n".join(lines)


def _safe_id(name: str) -> str:
    """Sanitize a name for use as a Mermaid subgraph ID."""
    return name.replace("-", "_").replace(".", "_").replace(" ", "_").replace("/", "_")
