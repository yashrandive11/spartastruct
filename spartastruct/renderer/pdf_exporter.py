"""PDF export via Mermaid CLI (mmdc)."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

from spartastruct.renderer.markdown_renderer import DiagramSection

_MMDC_CONFIG = {"maxTextSize": 200000}


def find_mmdc() -> str | None:
    """Return the path to the mmdc binary, or None if not installed."""
    return shutil.which("mmdc")


def export_diagram_pdf(
    section: DiagramSection,
    out_dir: Path,
    mmdc_path: str,
) -> Path:
    """Export a single diagram to PDF using mmdc.

    Writes mermaid source to a temp .mmd file, calls mmdc, cleans up the temp file.

    Returns:
        Path to the created PDF file.

    Raises:
        subprocess.CalledProcessError: if mmdc exits non-zero.
        Note: mmdc's stderr is available on the CalledProcessError as `.stderr`.
    """
    out_file = out_dir / f"{section.key}.pdf"

    with tempfile.NamedTemporaryFile(suffix=".mmd", mode="w", delete=False, encoding="utf-8") as f:
        f.write(section.mermaid)
        mmd_path = f.name

    with tempfile.NamedTemporaryFile(
        suffix=".json", mode="w", delete=False, encoding="utf-8"
    ) as cfg:
        json.dump(_MMDC_CONFIG, cfg)
        cfg_path = cfg.name

    try:
        subprocess.run(
            [mmdc_path, "-i", mmd_path, "-o", str(out_file), "--configFile", cfg_path],
            check=True,
            capture_output=True,
            text=True,
        )
    finally:
        Path(mmd_path).unlink(missing_ok=True)
        Path(cfg_path).unlink(missing_ok=True)

    return out_file


def export_all_pdfs(
    sections: list[DiagramSection],
    out_dir: Path,
    mmdc_path: str,
    progress_callback: Callable[[str], None] | None = None,
) -> list[Path]:
    """Export all non-empty diagrams to individual PDF files.

    Args:
        sections: DiagramSections to export (empty mermaid fields skipped)
        out_dir: directory to write PDFs into (must already exist)
        mmdc_path: absolute path to the mmdc binary
        progress_callback: optional callable receiving a status string per diagram

    Returns:
        List of Paths to created PDF files.

    Stops on the first mmdc failure — partial results are not returned.
    """
    results = []
    for section in sections:
        if not section.mermaid.strip():
            continue
        if progress_callback:
            progress_callback(f"Exporting {section.title} to PDF…")
        out_file = export_diagram_pdf(section, out_dir, mmdc_path)
        results.append(out_file)
    return results


def export_diagram_png(
    section: DiagramSection,
    out_dir: Path,
    mmdc_path: str,
    scale: int = 3,
) -> Path:
    """Export a single diagram to a high-quality transparent-background PNG."""
    out_file = out_dir / f"{section.key}.png"

    with tempfile.NamedTemporaryFile(suffix=".mmd", mode="w", delete=False, encoding="utf-8") as f:
        f.write(section.mermaid)
        mmd_path = f.name

    with tempfile.NamedTemporaryFile(
        suffix=".json", mode="w", delete=False, encoding="utf-8"
    ) as cfg:
        json.dump(_MMDC_CONFIG, cfg)
        cfg_path = cfg.name

    try:
        subprocess.run(
            [
                mmdc_path,
                "-i", mmd_path,
                "-o", str(out_file),
                "--backgroundColor", "transparent",
                "--scale", str(scale),
                "--configFile", cfg_path,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    finally:
        Path(mmd_path).unlink(missing_ok=True)
        Path(cfg_path).unlink(missing_ok=True)

    return out_file


def export_all_pngs(
    sections: list[DiagramSection],
    out_dir: Path,
    mmdc_path: str,
    scale: int = 3,
    progress_callback: Callable[[str], None] | None = None,
) -> list[Path]:
    """Export all non-empty diagrams to individual PNG files with transparent background."""
    results = []
    for section in sections:
        if not section.mermaid.strip():
            continue
        if progress_callback:
            progress_callback(f"Exporting {section.title} to PNG…")
        out_file = export_diagram_png(section, out_dir, mmdc_path, scale=scale)
        results.append(out_file)
    return results
