# Contributing to SpartaStruct

## Setup

```bash
git clone https://github.com/yashrandive/spartastruct
cd spartastruct

# Create and activate a conda environment
conda create -n spartastruct python=3.11
conda activate spartastruct

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest tests/ -v
```

## Linting

```bash
ruff check .
ruff format .
```

## Project Structure

```
spartastruct/
  analyzer/       # AST parsing (base.py data model, python_analyzer.py)
  diagrams/       # Six static Mermaid generators
  llm/            # LLM enrichment (client.py, prompts.py)
  renderer/       # Markdown renderer (markdown_renderer.py)
  templates/      # Jinja2 output template (structure.md.j2)
  utils/          # File walker, framework detector
  cli.py          # Click CLI entry point
  config.py       # TOML config loader/writer
tests/
  fixtures/       # sample_plain, sample_fastapi, sample_django
```

## Adding a New Diagram

1. Create `spartastruct/diagrams/my_diagram.py` with a `generate(result: AnalysisResult) -> str` function
2. Add it to `_GENERATORS` in `spartastruct/cli.py`
3. Add a system prompt in `spartastruct/llm/prompts.py` and register in `DIAGRAM_PROMPTS`
4. Add a title in `spartastruct/renderer/markdown_renderer.py` (`_DIAGRAM_TITLES` and `_DIAGRAM_ORDER`)
5. Add tests in `tests/test_diagrams.py`

## Commit Convention

`type: short description` where type is `feat`, `fix`, `test`, `docs`, `chore`, or `refactor`.
