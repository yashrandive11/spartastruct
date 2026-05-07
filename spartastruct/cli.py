"""Click CLI for SpartaStruct."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from spartastruct.analyzer.base import AnalysisResult as _AnalysisResult
from spartastruct.analyzer.js_analyzer import JsAnalyzer
from spartastruct.analyzer.python_analyzer import PythonAnalyzer
from spartastruct.config import Config, load_config, save_config
from spartastruct.diagrams import (
    api_map,
    class_diagram,
    component_map,
    dfd,
    er_diagram,
    event_flow,
    flowchart,
    function_graph,
    module_graph,
    sequence_diagram,
    state_diagram,
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
    "sequence_diagram": sequence_diagram.generate,
    "state_diagram": state_diagram.generate,
    "api_map": api_map.generate,
    "component_map": component_map.generate,
    "event_flow": event_flow.generate,
}

_JS_TS_EXTENSIONS = frozenset({".js", ".ts", ".jsx", ".tsx"})
_PY_EXTENSIONS = frozenset({".py"})


def _detect_extensions(project_path: Path) -> frozenset[str]:
    """Return extensions to walk based on which source files exist in the project."""

    def _count(pattern: str) -> int:
        return sum(
            1
            for p in project_path.rglob(pattern)
            if "node_modules" not in str(p) and ".git" not in str(p)
        )

    py_count = _count("*.py")
    js_count = sum(_count(ext) for ext in ("*.js", "*.ts", "*.jsx", "*.tsx"))

    if py_count == 0 and js_count > 0:
        return _JS_TS_EXTENSIONS
    if js_count == 0:
        return _PY_EXTENSIONS
    return _PY_EXTENSIONS | _JS_TS_EXTENSIONS


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
@click.option(
    "--format",
    "export_format",
    default="pdf",
    type=click.Choice(["pdf", "png", "both"], case_sensitive=False),
    help="Output format: pdf (default), png (transparent background, 3x scale), or both",
)
def analyze(  # noqa: PLR0913
    path: str, no_llm: bool, model: str | None, output: str | None, export_format: str
) -> None:
    """Analyze a Python project and export each diagram as a PDF."""
    from spartastruct.renderer.pdf_exporter import export_all_pdfs, export_all_pngs, find_mmdc

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

    try:
        with Progress(
            SpinnerColumn(), TextColumn("{task.description}"), console=console
        ) as progress:
            t = progress.add_task("Walking files…", total=None)
            extensions = _detect_extensions(project_path)
            all_files, walk_warnings = walk_project(project_path, extensions=extensions)
            progress.update(t, description=f"Found {len(all_files)} source files")

            progress.update(t, description="Analyzing…")
            # shared warning list — both analyzers append to it in-place
            result = _AnalysisResult(warnings=walk_warnings)

            py_files = [f for f in all_files if f.suffix == ".py"]
            js_files = [f for f in all_files if f.suffix in _JS_TS_EXTENSIONS]

            if py_files:
                py_analyzer = PythonAnalyzer(project_root)
                py_result = py_analyzer.analyze(py_files, walk_warnings)
                result.files_analyzed.extend(py_result.files_analyzed)
                result.entry_points.extend(py_result.entry_points)
                result.files_skipped_parse_error += py_result.files_skipped_parse_error

            if js_files:
                js_analyzer = JsAnalyzer(project_root)
                js_result = js_analyzer.analyze(js_files, walk_warnings)
                result.files_analyzed.extend(js_result.files_analyzed)
                result.entry_points.extend(js_result.entry_points)

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

            pdf_files: list[Path] = []
            png_files: list[Path] = []

            if export_format in ("pdf", "both"):
                pdf_files = export_all_pdfs(
                    sections,
                    out_dir,
                    mmdc_path,
                    progress_callback=lambda msg: progress.update(t, description=msg),
                )
            if export_format in ("png", "both"):
                png_files = export_all_pngs(
                    sections,
                    out_dir,
                    mmdc_path,
                    progress_callback=lambda msg: progress.update(t, description=msg),
                )

        failures = get_llm_failures()
        summary_lines = [
            f"[green]Output:[/green] {out_dir}",
        ]
        if pdf_files:
            summary_lines.append(f"PDFs written: {len(pdf_files)}")
        if png_files:
            summary_lines.append(f"PNGs written: {len(png_files)}")
        summary_lines += [
            f"Files analyzed: {len(result.files_analyzed)}",
            f"Frameworks: {', '.join(result.frameworks) or 'none detected'}",
        ]
        if result.llm_calls_succeeded:
            summary_lines.append(f"LLM enrichments: {result.llm_calls_succeeded}/11")
        if failures:
            summary_lines.append(f"[yellow]LLM warnings: {len(failures)} failure(s)[/yellow]")
            for msg in failures:
                summary_lines.append(f"[yellow]  • {msg}[/yellow]")
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
