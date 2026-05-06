"""Tests for the Click CLI."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from spartastruct.cli import main

PLAIN_DIR = str(Path(__file__).parent / "fixtures" / "sample_plain")
FASTAPI_DIR = str(Path(__file__).parent / "fixtures" / "sample_fastapi")


@pytest.fixture
def runner():
    return CliRunner()


def test_main_help(runner):
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "analyze" in result.output
    assert "init" in result.output
    assert "config" in result.output


def test_analyze_no_llm_plain(runner, tmp_path):
    result = runner.invoke(
        main,
        [
            "analyze",
            PLAIN_DIR,
            "--no-llm",
            "--output",
            str(tmp_path / "out"),
        ],
    )
    assert result.exit_code == 0, result.output
    out_file = tmp_path / "out" / "ARCHITECTURE.md"
    assert out_file.exists()
    content = out_file.read_text()
    assert "## Class Diagram" in content
    assert "```mermaid" in content


def test_analyze_no_llm_fastapi(runner, tmp_path):
    result = runner.invoke(
        main,
        [
            "analyze",
            FASTAPI_DIR,
            "--no-llm",
            "--output",
            str(tmp_path / "out"),
        ],
    )
    assert result.exit_code == 0, result.output
    content = (tmp_path / "out" / "ARCHITECTURE.md").read_text()
    assert "## Entity Relationship Diagram" in content
    assert "## Data Flow Diagram" in content


def test_analyze_creates_output_dir(runner, tmp_path):
    out = tmp_path / "nested" / "docs"
    result = runner.invoke(
        main,
        [
            "analyze",
            PLAIN_DIR,
            "--no-llm",
            "--output",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (out / "ARCHITECTURE.md").exists()


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
