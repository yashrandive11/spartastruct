# SpartaStruct

> Instant architecture diagrams for any Python codebase

SpartaStruct analyzes your Python project using AST parsing and (optionally) an LLM, then exports six Mermaid.js architecture diagrams as PDFs.

## Diagrams Generated

| Diagram | Type | Description |
|---|---|---|
| Class Diagram | `classDiagram` | All classes, inheritance, and members |
| ER Diagram | `erDiagram` | ORM models and their relationships |
| Data Flow | `flowchart LR` | HTTP routes → service → database |
| App Logic | `flowchart TD` | Entry points and processing flow |
| Function Graph | `graph LR` | Inter-function call graph |
| Module Graph | `graph TD` | Module-level import dependencies |

## Installation

```bash
pip install spartastruct
```

## Quick Start

```bash
# Analyze a project (no LLM, fully offline)
spartastruct analyze /path/to/your/project --no-llm

# With LLM enrichment (requires API key)
spartastruct init                              # create ~/.spartastruct/config.toml
spartastruct config --api-key anthropic YOUR_KEY
spartastruct analyze /path/to/your/project
```

Output: six PDF files in `spartadocs/` in your project directory.

## CLI Reference

### `spartastruct analyze [PATH]`

| Flag | Default | Description |
|---|---|---|
| `--no-llm` | off | Skip LLM; fully offline, static diagrams only |
| `--model MODEL` | from config | Override LLM model |
| `--output DIR` | `spartadocs` | Override output directory |

## PDF Export

PDFs are the default output. Install the Mermaid CLI (requires Node.js) before running `analyze`:

```bash
npm install -g @mermaid-js/mermaid-cli
```

Then run:

```bash
spartastruct analyze /path/to/project --no-llm
```

This writes `class_diagram.pdf`, `er_diagram.pdf`, `dfd.pdf`, `flowchart.pdf`, `function_graph.pdf`, and `module_graph.pdf` into the output directory.

### `spartastruct init`

Creates `~/.spartastruct/config.toml` with default settings.

### `spartastruct config`

| Flag | Description |
|---|---|
| `--model MODEL` | Set default LLM model |
| `--output-dir DIR` | Set default output directory |
| `--api-key PROVIDER KEY` | Set API key (e.g. `--api-key anthropic sk-...`) |
| `--show` | Print current config |

## Supported LLM Providers

SpartaStruct uses [litellm](https://docs.litellm.ai/) and supports any provider it supports: Anthropic, OpenAI, Gemini, Groq, Mistral, Cohere, Together, Ollama.

Default model: `anthropic/claude-haiku-4-5-20251001`

## Supported Frameworks

Auto-detected: FastAPI, Flask, Django, SQLAlchemy, Tortoise ORM, Peewee, Celery, Pydantic, Pytest, NumPy, Pandas, PyTorch, TensorFlow.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md).
