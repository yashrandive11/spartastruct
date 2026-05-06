"""Tests for the PDF exporter."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from spartastruct.renderer.markdown_renderer import DiagramSection
from spartastruct.renderer.pdf_exporter import (
    export_all_pdfs,
    export_diagram_pdf,
    find_mmdc,
)


@pytest.fixture
def section():
    return DiagramSection(
        key="class_diagram",
        title="Class Diagram",
        description="",
        mermaid="classDiagram\n    A --> B",
    )


@pytest.fixture
def empty_section():
    return DiagramSection(key="er_diagram", title="ER Diagram", description="", mermaid="")


def test_find_mmdc_returns_path_when_present():
    patch_target = "spartastruct.renderer.pdf_exporter.shutil.which"
    with patch(patch_target, return_value="/usr/local/bin/mmdc"):
        result = find_mmdc()
    assert result == "/usr/local/bin/mmdc"


def test_find_mmdc_returns_none_when_absent():
    with patch("spartastruct.renderer.pdf_exporter.shutil.which", return_value=None):
        result = find_mmdc()
    assert result is None


def test_export_diagram_pdf_calls_mmdc(section, tmp_path):
    with patch("spartastruct.renderer.pdf_exporter.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        out_file = export_diagram_pdf(section, tmp_path, "/usr/local/bin/mmdc")

    assert out_file == tmp_path / "class_diagram.pdf"
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert call_args[0] == "/usr/local/bin/mmdc"
    assert call_args[2].endswith(".mmd")  # -i <tempfile>
    assert call_args[4] == str(tmp_path / "class_diagram.pdf")  # -o <outfile>


def test_export_diagram_pdf_writes_mermaid_to_temp_file(section, tmp_path):
    captured_content = []

    def fake_run(cmd, **kwargs):
        mmd_path = cmd[2]  # -i <path>
        captured_content.append(Path(mmd_path).read_text())
        return MagicMock(returncode=0)

    with patch("spartastruct.renderer.pdf_exporter.subprocess.run", side_effect=fake_run):
        export_diagram_pdf(section, tmp_path, "/usr/local/bin/mmdc")

    assert captured_content[0] == "classDiagram\n    A --> B"


def test_export_diagram_pdf_cleans_up_temp_file(section, tmp_path):
    seen_paths = []

    def fake_run(cmd, **kwargs):
        seen_paths.append(cmd[2])
        return MagicMock(returncode=0)

    with patch("spartastruct.renderer.pdf_exporter.subprocess.run", side_effect=fake_run):
        export_diagram_pdf(section, tmp_path, "/usr/local/bin/mmdc")

    assert not Path(seen_paths[0]).exists()


def test_export_diagram_pdf_raises_on_mmdc_failure(section, tmp_path):
    import subprocess

    patch_target = "spartastruct.renderer.pdf_exporter.subprocess.run"
    error = subprocess.CalledProcessError(1, "mmdc")
    with patch(patch_target, side_effect=error):
        with pytest.raises(subprocess.CalledProcessError):
            export_diagram_pdf(section, tmp_path, "/usr/local/bin/mmdc")


def test_export_diagram_pdf_cleans_up_temp_file_on_failure(section, tmp_path):
    import subprocess

    seen_paths = []

    def fake_run(cmd, **kwargs):
        seen_paths.append(cmd[2])
        raise subprocess.CalledProcessError(1, "mmdc")

    with patch("spartastruct.renderer.pdf_exporter.subprocess.run", side_effect=fake_run):
        with pytest.raises(subprocess.CalledProcessError):
            export_diagram_pdf(section, tmp_path, "/usr/local/bin/mmdc")

    assert not Path(seen_paths[0]).exists()


def test_export_all_pdfs_skips_empty_mermaid(section, empty_section, tmp_path):
    with patch("spartastruct.renderer.pdf_exporter.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        results = export_all_pdfs([section, empty_section], tmp_path, "/usr/local/bin/mmdc")

    assert len(results) == 1
    assert results[0] == tmp_path / "class_diagram.pdf"
    assert mock_run.call_count == 1


def test_export_all_pdfs_calls_progress_callback(section, tmp_path):
    calls = []
    patch_target = "spartastruct.renderer.pdf_exporter.subprocess.run"
    with patch(patch_target, return_value=MagicMock(returncode=0)):
        export_all_pdfs([section], tmp_path, "/usr/local/bin/mmdc", progress_callback=calls.append)

    assert len(calls) == 1
    assert "Class Diagram" in calls[0]


def test_export_all_pdfs_returns_all_paths(tmp_path):
    sections = [
        DiagramSection(
            key=f"diag_{i}",
            title=f"Diag {i}",
            description="",
            mermaid=f"graph LR\n  A{i}",
        )
        for i in range(3)
    ]
    patch_target = "spartastruct.renderer.pdf_exporter.subprocess.run"
    with patch(patch_target, return_value=MagicMock(returncode=0)):
        results = export_all_pdfs(sections, tmp_path, "/usr/local/bin/mmdc")

    assert len(results) == 3
    assert all(p.suffix == ".pdf" for p in results)
