"""Static generator for Module Dependency Graph (graph TD)."""

from __future__ import annotations

from pathlib import Path

from spartastruct.analyzer.base import AnalysisResult


def generate(result: AnalysisResult) -> str:
    """Generate a Mermaid graph TD showing module-level import dependencies.

    Groups files by directory using subgraph blocks. Entry point files get
    the :::entrypoint style. Third-party packages get :::external style.
    Stdlib imports are omitted.

    Args:
        result: The full analysis result.

    Returns:
        A Mermaid graph TD string (without fences).
    """
    lines = ["graph TD"]
    lines.append("    classDef entrypoint fill:#fff3cd,stroke:#ff9800")
    lines.append("    classDef external fill:#f8d7da,stroke:#dc3545")

    if not result.files_analyzed:
        lines.append('    empty["No Python files analyzed"]')
        return "\n".join(lines)

    entry_files = set(result.entry_points)

    # Group files by directory
    dir_groups: dict[str, list[str]] = {}
    for fr in result.files_analyzed:
        directory = str(Path(fr.path).parent)
        dir_groups.setdefault(directory, []).append(fr.path)

    # Node ID mapping
    node_ids: dict[str, str] = {}
    for i, fr in enumerate(result.files_analyzed):
        node_ids[fr.path] = f"mod{i}"

    # External package nodes (collected across all files)
    external_pkgs: set[str] = set()
    for fr in result.files_analyzed:
        for imp in fr.imports.third_party:
            root = imp.split(".")[0]
            external_pkgs.add(root)

    ext_ids: dict[str, str] = {}
    for i, pkg in enumerate(sorted(external_pkgs)):
        ext_ids[pkg] = f"ext{i}"

    # Subgraphs per directory
    for directory, files in dir_groups.items():
        dir_label = directory if directory != "." else "root"
        sg_id = _safe_id(dir_label)
        lines.append(f"    subgraph {sg_id}[\"{dir_label}\"]")
        for file_path in files:
            nid = node_ids[file_path]
            stem = Path(file_path).name
            lines.append(f'        {nid}["{stem}"]')
            if file_path in entry_files:
                lines.append(f"        {nid}:::entrypoint")
        lines.append("    end")

    # External nodes
    if external_pkgs:
        lines.append('    subgraph external["Third-party packages"]')
        for pkg in sorted(external_pkgs):
            eid = ext_ids[pkg]
            lines.append(f'        {eid}["{pkg}"]')
            lines.append(f"        {eid}:::external")
        lines.append("    end")

    # Edges: local imports
    path_to_fr = {fr.path: fr for fr in result.files_analyzed}

    for fr in result.files_analyzed:
        src_id = node_ids[fr.path]
        for local_imp in fr.imports.local:
            # Resolve import root to a file path
            imp_root = local_imp.split(".")[0]
            for other_path in node_ids:
                other_stem = Path(other_path).stem
                if other_stem == imp_root or other_path.replace("/", ".").replace(".py", "") == local_imp:
                    dst_id = node_ids[other_path]
                    if src_id != dst_id:
                        lines.append(f"    {src_id} --> {dst_id}")
                    break

        # Third-party edges
        for tp_imp in fr.imports.third_party:
            root = tp_imp.split(".")[0]
            if root in ext_ids:
                lines.append(f"    {src_id} --> {ext_ids[root]}")

    return "\n".join(lines)


def _safe_id(name: str) -> str:
    """Sanitize a name for use as a Mermaid node/subgraph ID."""
    return name.replace("-", "_").replace(".", "_").replace("/", "_").replace(" ", "_")
