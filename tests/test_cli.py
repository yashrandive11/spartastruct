"""Tests for the Click CLI."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from spartastruct.cli import main

PLAIN_DIR = str(Path(__file__).parent / "fixtures" / "sample_plain")
FASTAPI_DIR = str(Path(__file__).parent / "fixtures" / "sample_fastapi")

_MOCK_MMDC = "/usr/local/bin/mmdc"


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture(autouse=True)
def mock_mmdc():
    """Auto-mock mmdc for every CLI test so they pass without mmdc installed."""
    with patch(
        "spartastruct.renderer.pdf_exporter.shutil.which",
        return_value=_MOCK_MMDC,
    ), patch(
        "spartastruct.renderer.pdf_exporter.subprocess.run",
        return_value=MagicMock(returncode=0),
    ):
        yield


def test_main_help(runner):
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "analyze" in result.output
    assert "init" in result.output
    assert "config" in result.output


def test_analyze_no_llm_plain(runner, tmp_path):
    result = runner.invoke(
        main,
        ["analyze", PLAIN_DIR, "--no-llm", "--output", str(tmp_path / "out")],
    )
    assert result.exit_code == 0, result.output
    assert "PDFs written" in result.output


def test_analyze_no_llm_fastapi(runner, tmp_path):
    result = runner.invoke(
        main,
        ["analyze", FASTAPI_DIR, "--no-llm", "--output", str(tmp_path / "out")],
    )
    assert result.exit_code == 0, result.output
    assert "PDFs written" in result.output


def test_analyze_creates_output_dir(runner, tmp_path):
    out = tmp_path / "nested" / "docs"
    result = runner.invoke(
        main,
        ["analyze", PLAIN_DIR, "--no-llm", "--output", str(out)],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()


def test_analyze_missing_mmdc_errors(runner, tmp_path):
    """Without mmdc installed, analyze errors with a helpful message."""
    with patch("spartastruct.renderer.pdf_exporter.shutil.which", return_value=None):
        result = runner.invoke(
            main,
            ["analyze", PLAIN_DIR, "--no-llm", "--output", str(tmp_path / "out")],
        )
    assert result.exit_code != 0
    assert "mmdc" in result.output.lower() or "mermaid" in result.output.lower()


def test_config_show(runner, tmp_path, monkeypatch):
    import spartastruct.config as cfg_mod

    monkeypatch.setattr(cfg_mod, "CONFIG_DIR", tmp_path / ".spartastruct")
    monkeypatch.setattr(cfg_mod, "CONFIG_FILE", tmp_path / ".spartastruct" / "config.toml")
    result = runner.invoke(main, ["config", "--show"])
    assert result.exit_code == 0
    assert "Model:" in result.output


def test_init_creates_config(runner, tmp_path, monkeypatch):
    import spartastruct.config as cfg_mod

    monkeypatch.setattr(cfg_mod, "CONFIG_DIR", tmp_path / ".spartastruct")
    monkeypatch.setattr(cfg_mod, "CONFIG_FILE", tmp_path / ".spartastruct" / "config.toml")
    result = runner.invoke(main, ["init"])
    assert result.exit_code == 0
    assert (tmp_path / ".spartastruct" / "config.toml").exists()


def test_config_update_model(runner, tmp_path, monkeypatch):
    import spartastruct.config as cfg_mod

    monkeypatch.setattr(cfg_mod, "CONFIG_DIR", tmp_path / ".spartastruct")
    monkeypatch.setattr(cfg_mod, "CONFIG_FILE", tmp_path / ".spartastruct" / "config.toml")
    result = runner.invoke(main, ["config", "--model", "openai/gpt-4o"])
    assert result.exit_code == 0
    cfg = cfg_mod.load_config()
    assert cfg.model == "openai/gpt-4o"


def test_analyze_png_format_writes_pngs(runner, tmp_path):
    result = runner.invoke(
        main,
        ["analyze", PLAIN_DIR, "--no-llm", "--output", str(tmp_path / "out"), "--format", "png"],
    )
    assert result.exit_code == 0, result.output
    assert "PNGs written" in result.output


def test_analyze_both_format_writes_pdfs_and_pngs(runner, tmp_path):
    result = runner.invoke(
        main,
        ["analyze", PLAIN_DIR, "--no-llm", "--output", str(tmp_path / "out"), "--format", "both"],
    )
    assert result.exit_code == 0, result.output
    assert "PDFs written" in result.output
    assert "PNGs written" in result.output


def test_analyze_default_format_is_pdf(runner, tmp_path):
    result = runner.invoke(
        main,
        ["analyze", PLAIN_DIR, "--no-llm", "--output", str(tmp_path / "out")],
    )
    assert result.exit_code == 0, result.output
    assert "PDFs written" in result.output
    assert "PNGs written" not in result.output
