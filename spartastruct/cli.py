"""Click CLI for SpartaStruct."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from spartastruct.analyzer.python_analyzer import PythonAnalyzer
from spartastruct.config import Config, load_config, save_config
from spartastruct.diagrams import (
    class_diagram,
    dfd,
    er_diagram,
    flowchart,
    function_graph,
    module_graph,
)
from spartastruct.llm.client import call_llm_for_diagram, get_llm_failures
from spartastruct.renderer.markdown_renderer import make_sections
from spartastruct.utils.file_walker import find_project_root, walk_project
from spartastruct.utils.framework_detector import detect_frameworks

console = Console()

_GENERATORS = {
    "class_diagram": class_diagram.generate,
    "er_diagram": er_diagram.generate,
    "dfd": dfd.generate,
    "flowchart": flowchart.generate,
    "function_graph": function_graph.generate,
    "module_graph": module_graph.generate,
}


@click.group()
def main() -> None:
    """SpartaStruct — instant architecture diagrams for any Python codebase."""


@main.command()
def init() -> None:
    """Create ~/.spartastruct/config.toml with default settings."""
    from spartastruct.config import CONFIG_FILE  # deferred so monkeypatch in tests takes effect

    if CONFIG_FILE.exists():
        console.print(f"[yellow]Config already exists at {CONFIG_FILE}[/yellow]")
        return
    cfg = Config()
    save_config(cfg)
    console.print(
        Panel(
            f"[green]Config created at {CONFIG_FILE}[/green]\n"
            f"Model: {cfg.model}\n"
            f"Output dir: {cfg.output_dir}",
            title="SpartaStruct initialized",
        )
    )


@main.command()
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False))
@click.option("--no-llm", is_flag=True, help="Skip LLM enrichment (fully offline)")
@click.option("--model", default=None, help="Override LLM model")
@click.option("--output", default=None, help="Override output directory")
def analyze(path: str, no_llm: bool, model: str | None, output: str | None) -> None:
    """Analyze a Python project and export each diagram as a PDF."""
    from spartastruct.renderer.pdf_exporter import export_all_pdfs, find_mmdc

    mmdc_path = find_mmdc()
    if mmdc_path is None:
        raise click.ClickException(
            "mmdc not found. Install the Mermaid CLI with:\n"
            "  npm install -g @mermaid-js/mermaid-cli"
        )

    cfg = load_config()
    if model:
        cfg.model = model
    if output:
        cfg.output_dir = output

    project_path = Path(path).resolve()
    project_root = find_project_root(project_path) or project_path

    out_dir = project_path / cfg.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    pdf_count = 0
    try:
        with Progress(
            SpinnerColumn(), TextColumn("{task.description}"), console=console
        ) as progress:
            t = progress.add_task("Walking files…", total=None)
            py_files, walk_warnings = walk_project(project_path)
            progress.update(t, description=f"Found {len(py_files)} Python files")

            progress.update(t, description="Analyzing AST…")
            analyzer = PythonAnalyzer(project_root)
            result = analyzer.analyze(py_files, walk_warnings)
            result.frameworks = detect_frameworks(result)

            progress.update(t, description="Generating diagrams…")
            static_diagrams: dict[str, str] = {key: gen(result) for key, gen in _GENERATORS.items()}

            llm_results: dict[str, tuple[str, str]] | None = None
            if not no_llm:
                llm_results = {}
                for key in _GENERATORS:
                    progress.update(t, description=f"LLM enriching {key}…")
                    desc, mermaid = call_llm_for_diagram(
                        key, static_diagrams[key], result, cfg.model, cfg.api_keys
                    )
                    if mermaid:
                        llm_results[key] = (desc, mermaid)
                        result.llm_calls_succeeded += 1

            sections = make_sections(static_diagrams, llm_results)

            pdf_files = export_all_pdfs(
                sections,
                out_dir,
                mmdc_path,
                progress_callback=lambda msg: progress.update(t, description=msg),
            )
            pdf_count = len(pdf_files)

        failures = get_llm_failures()
        summary_lines = [
            f"[green]Output:[/green] {out_dir}",
            f"PDFs written: {pdf_count}",
            f"Files analyzed: {len(result.files_analyzed)}",
            f"Frameworks: {', '.join(result.frameworks) or 'none detected'}",
        ]
        if result.llm_calls_succeeded:
            summary_lines.append(f"LLM enrichments: {result.llm_calls_succeeded}/6")
        if failures:
            summary_lines.append(f"[yellow]LLM warnings: {len(failures)} failure(s)[/yellow]")
        if result.warnings:
            summary_lines.append(f"[yellow]Warnings: {len(result.warnings)}[/yellow]")

        console.print(
            Panel(
                "\n".join(summary_lines),
                title="[bold]SpartaStruct Analysis Complete[/bold]",
            )
        )
    except click.ClickException:
        raise
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise SystemExit(1)


@main.command("config")
@click.option("--model", default=None, help="Set default LLM model")
@click.option("--output-dir", default=None, help="Set default output directory")
@click.option(
    "--api-key",
    "api_keys",
    multiple=True,
    type=(str, str),
    metavar="PROVIDER KEY",
    help="Set API key, e.g. --api-key anthropic sk-...",
)
@click.option("--show", is_flag=True, help="Print current config")
def config_cmd(model: str | None, output_dir: str | None, api_keys: tuple, show: bool) -> None:
    """View or update ~/.spartastruct/config.toml."""
    cfg = load_config()

    if show or (not model and not output_dir and not api_keys):
        console.print(
            Panel(
                f"Model: {cfg.model}\n"
                f"Output dir: {cfg.output_dir}\n"
                f"API keys set: {list(cfg.api_keys.keys()) or 'none'}",
                title="Current config",
            )
        )
        return

    if model:
        cfg.model = model
    if output_dir:
        cfg.output_dir = output_dir
    for provider, key in api_keys:
        cfg.api_keys[provider] = key

    save_config(cfg)
    console.print("[green]Config updated.[/green]")
