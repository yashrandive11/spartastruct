# SpartaStruct — Design Spec

**Date:** 2026-05-05
**Status:** Approved
**Project:** SpartaStruct v0.1.0

---

## Overview

SpartaStruct is a Python CLI tool that analyzes a Python codebase (or a single `.py` file) and auto-generates a structured documentation file containing six architecture diagrams rendered in Mermaid.js syntax. Output is a single well-formatted Markdown file saved inside a `spartadocs/` folder in the project root.

It uses a hybrid architecture: Python AST parsing extracts raw structure; an LLM layer (via `litellm`) enriches and narrates the results. A `--no-llm` flag enables fully offline, static-analysis-only operation.

---

## Build Order (Linear)

1. File walker (`utils/file_walker.py`)
2. AST parser + `astroid` type inference (`analyzer/python_analyzer.py`)
3. Six static diagram generators (`diagrams/`)
4. LLM client + prompts (`llm/`)
5. Jinja2 renderer (`renderer/`, `templates/`)
6. Click CLI + Rich terminal output (`cli.py`, `config.py`)
7. Tests + fixtures

---

## Data Model

Defined in `analyzer/base.py`. All other modules either produce or consume `AnalysisResult`.

```python
@dataclass
class AnalysisResult:
    files_analyzed: list[FileResult]
    frameworks: list[str]
    entry_points: list[str]       # relative paths
    warnings: list[str]
    llm_calls_succeeded: int = 0
    files_skipped_large: int = 0
    files_skipped_parse_error: int = 0

@dataclass
class FileResult:
    path: str                     # relative to project root
    classes: list[ClassInfo]
    functions: list[FunctionInfo]
    imports: ImportInfo
    routes: list[RouteInfo]

@dataclass
class ClassInfo:
    name: str
    bases: list[str]
    decorators: list[str]
    attributes: list[AttributeInfo]
    methods: list[MethodInfo]
    is_abstract: bool
    is_dataclass: bool
    orm_type: str | None          # "sqlalchemy", "django", "tortoise", "peewee", None

@dataclass
class AttributeInfo:
    name: str
    type: str                     # annotation or astroid-inferred or "Any"
    visibility: str               # "public", "protected", "private"

@dataclass
class MethodInfo:
    name: str
    params: list[ParamInfo]
    return_type: str
    decorators: list[str]
    is_async: bool
    calls: list[str]              # resolved local call targets where possible
    visibility: str

@dataclass
class ParamInfo:
    name: str
    type: str

@dataclass
class FunctionInfo:
    name: str
    params: list[ParamInfo]
    return_type: str
    decorators: list[str]
    is_async: bool
    calls: list[str]

@dataclass
class ImportInfo:
    stdlib: list[str]
    third_party: list[str]
    local: list[str]              # local import edges for module graph

@dataclass
class RouteInfo:
    method: str                   # GET, POST, etc.
    path: str
    handler_name: str

@dataclass
class DiagramSection:
    title: str
    emoji: str
    description: str              # LLM-generated or "" in --no-llm mode
    mermaid: str                  # final Mermaid block content
```

> `DiagramSection` is a render-time construct, not an analysis output. Define it in `renderer/markdown_renderer.py` (or a shared `types.py` if needed by both the renderer and CLI). It is not part of `AnalysisResult`.

---

## File Walker (`utils/file_walker.py`)

**`walk_project(root: Path) -> tuple[list[Path], list[str]]`**

- Recursively walks from `root`, yielding `.py` files only.
- Skips directories: `__pycache__`, `.git`, `venv`, `.venv`, `env`, `.env`, `node_modules`, `dist`, `build`, `eggs`, `.eggs`, `.tox`, `.pytest_cache`, `.mypy_cache`, `spartadocs`.
- Files >500KB: skip with warning added to return list.
- Returns `(py_files, warnings)`.

**Project root detection**

Walk upward from `cwd` looking for `pyproject.toml`, `setup.py`, `setup.cfg`, or `.git`. If none found, treat `cwd` as root.

**`--file` mode**

Accept a single `.py` path. All six diagrams scoped to that file only.

---

## AST Parser (`analyzer/python_analyzer.py`)

**`PythonAnalyzer.analyze(files: list[Path], root: Path) -> AnalysisResult`**

For each file:

1. `ast.parse()` — primary pass. On `SyntaxError`, log warning and skip file.
2. Single AST walk extracts: classes, functions, imports, routes.
3. For attributes/assignments missing type annotations: call `_infer_type(node)` which wraps `astroid` inference. Returns inferred type string on success, `"Any"` on any exception.
4. Function call extraction: walks each function/method body for `ast.Call` nodes; resolves name to local project function if the name matches a known symbol in `AnalysisResult`.

**Import classification**

- Stdlib: `sys.stdlib_module_names` (Python 3.10+)
- Local: root package name matches a directory or `.py` file directly under project root
- Third-party: everything else

**Framework detection** (`utils/framework_detector.py`)

Scans all `ImportInfo` across all files for known framework names: `fastapi`, `flask`, `django`, `starlette`, `sqlalchemy`, `celery`, `pydantic`, `pytest`, `click`, `typer`, etc. Returns `list[str]` of detected framework names.

**Entry point detection**

- Files named: `main.py`, `app.py`, `run.py`, `server.py`, `manage.py`, `wsgi.py`, `asgi.py`, `__main__.py`
- Files containing `if __name__ == "__main__":` blocks
- Files with `app = FastAPI()`, `app = Flask()`, `application = Django()` assignments

**Route extraction**

- FastAPI: `@app.get(...)`, `@app.post(...)`, `@router.get(...)`, etc. → `RouteInfo(method, path, handler_name)`
- Flask: `@app.route(path, methods=[...])` → `RouteInfo`
- Django: parse `urlpatterns` lists in `urls.py` → `RouteInfo`

**ORM detection**

- SQLAlchemy: classes inheriting `Base`, `DeclarativeBase`, `Model`; `Column()` fields; `relationship()`; `Table()` definitions
- Django: classes inheriting `models.Model`; field types; `ForeignKey`, `ManyToManyField`, `OneToOneField`
- Tortoise ORM: classes inheriting `tortoise.models.Model`
- Peewee: classes inheriting `peewee.Model`
- Sets `ClassInfo.orm_type` accordingly

**Visibility inference**

- `__name` → `"private"`
- `_name` → `"protected"`
- `name` → `"public"`

---

## Six Diagram Generators (`diagrams/`)

Each module exposes `generate(result: AnalysisResult) -> str` returning valid Mermaid syntax. Pure functions, no I/O.

### 1. Class Diagram (`class_diagram.py`)

- Type: `classDiagram`
- Every `ClassInfo` as a class node
- Attributes: `+type name` / `-type name` / `#type name` per visibility
- Methods: `+name(param: type) returnType` per visibility
- `<<abstract>>` stereotype for abstract classes; `<<dataclass>>` for dataclasses
- Relationships: `<|--` inheritance, `*--` composition, `o--` aggregation
- Empty state: `note "No classes found in this project"`

### 2. ER Diagram (`er_diagram.py`)

- Type: `erDiagram`
- Only classes where `orm_type` is set
- Fields with PK/FK/UK markers
- Relationship edges with cardinality and labels
- Empty state: `note "No ORM models detected"`

### 3. Data Flow Diagram (`dfd.py`)

- Type: `flowchart LR`
- External entities: `([Name])` — stadium shape
- Processes (routes/functions): `[Name]` — rectangle
- Data stores (DB models, caches): `[(Name)]` — cylindrical
- Labeled directed edges: `-->|data label|`
- Full journey: request → route handler → service → repository → DB → response
- Celery: task queues as stores, tasks as processes
- Fallback if no routes: generic request→handler→response chain

### 4. Application Logic Flowchart (`flowchart.py`)

- Type: `flowchart TD`
- Root: entry points as `([Start])`
- Steps: `[Process]`
- Decisions: `{Condition}`
- Terminals: `([End])`
- Web frameworks: request lifecycle shape
- Empty state: `([No entry point detected])`

### 5. Function Interconnection Graph (`function_graph.py`)

- Type: `graph LR`
- All module-level functions and class methods as nodes
- `subgraph FileName` per file
- Caller → callee directed edges for resolved local calls
- `:::async` style on async functions; `:::entrypoint` on entry point functions
- Edge labels: `call`, `async call`, `method call`, `callback`
- If >50 functions: truncate to entry-point call tree only, note omission

### 6. Module Dependency Graph (`module_graph.py`)

- Type: `graph TD`
- Every `.py` file as a node (relative path)
- `subgraph DirectoryName` per directory
- Local import edges only
- Third-party packages: terminal `:::external` nodes
- Stdlib imports omitted
- Entry point files: `:::entrypoint`

---

## LLM Integration (`llm/`)

### `client.py`

**`call_llm(prompt: str, system_prompt: str) -> str`**
- Loads config from `~/.spartastruct/config.toml`
- Sets provider API key as env var before calling `litellm.completion()`
- Model string comes directly from config — no hardcoding
- Returns response content on success; returns `""` on any exception
- Logs failure reason to module-level list folded into `AnalysisResult.warnings`

**`call_llm_for_diagram(diagram_type: str, static_mermaid: str, parsed_json: str) -> tuple[str, str]`**
- Selects system prompt from `prompts.py` by `diagram_type`
- Calls `call_llm`; parses response: description (before fence) + Mermaid block (inside fence)
- On empty response or parse failure: returns `("", static_mermaid)`
- LLM receives the static Mermaid as context plus the parsed JSON

**Supported litellm model strings (all routed via config):**
- `"claude-sonnet-4-20250514"` → Anthropic
- `"gpt-4o"` → OpenAI
- `"gemini/gemini-1.5-pro"` → Google
- `"groq/llama3-70b-8192"` → Groq
- `"ollama/codellama"` → Local Ollama
- `"together_ai/mistralai/Mixtral-8x7B-Instruct-v0.1"` → Together AI

### `prompts.py`

Six constants: `CLASS_DIAGRAM_PROMPT`, `ER_DIAGRAM_PROMPT`, `DFD_PROMPT`, `FLOWCHART_PROMPT`, `FUNCTION_GRAPH_PROMPT`, `MODULE_GRAPH_PROMPT`.

Each prompt specifies:
1. What the diagram represents
2. Exact Mermaid syntax rules and node shapes for that diagram type
3. Output format: 2–3 sentence description first, then fenced ` ```mermaid ` block
4. Hard instruction not to hallucinate structure absent from input JSON
5. Hard instruction to use only valid Mermaid syntax

---

## Renderer & CLI

### `renderer/markdown_renderer.py`

**`render(result: AnalysisResult, diagrams: list[DiagramSection], config: Config) -> str`**
- Loads `templates/structure.md.j2` via Jinja2
- Passes all data; template handles all formatting
- No conditional logic in template — Python resolves empty states before render

### `templates/structure.md.j2`

Output structure:
```
# ⚡ SpartaStruct — Project Architecture

| Field | Value |
...header table...

---
## {emoji} {title}

{description}

```mermaid
{mermaid}
```

(repeated for all 6 diagrams)

---
## 📊 Analysis Summary

...metrics table...

### Frameworks Detected
...

### Warnings
...
```

### `config.py`

**`load_config() -> Config`** — reads `~/.spartastruct/config.toml`. If missing, prints Rich panel instructing `spartastruct init` and exits with code 1.

`Config` dataclass fields mirror the TOML structure: `llm.provider`, `llm.model`, `llm.temperature`, `llm.max_tokens`, `api_keys.*`, `ollama.base_url`, `ollama.model`, `output.default_folder`.

### `cli.py`

`@click.group() main` with four commands:

**`init`**
- Interactive wizard via `click.prompt()`
- Asks: provider choice → model string → API key (or Ollama URL + model)
- Writes `~/.spartastruct/config.toml` with all fields commented
- `--force` to overwrite existing config

**`analyze`**
- Options: `--file PATH`, `--output FOLDER`, `--no-llm`, `--model STRING`
- `--model` overrides config for this run only
- Checks for existing `spartadocs/structure.md`; prompts before overwriting
- Orchestrates: file walk → parse → generate static diagrams → LLM enrichment (unless `--no-llm`) → render → write
- Rich `Progress` bar with named steps

**`config`**
- Reads and prints config via Rich `Syntax` panel

**`--version`** / **`--help`** via Click decorators

### Rich Terminal Output

- Header: `Panel("⚡ SpartaStruct v0.1.0", style="bold cyan")`
- Progress steps:
  1. Scanning files
  2. Parsing AST
  3. Extracting classes
  4. Extracting functions
  5. Detecting ORM models
  6. Generating Class Diagram [1/6]
  7. Calling LLM [1/6]
  8. … (repeat 6–7 for each diagram)
  9. Writing output
- Success: `Panel` with output path and key stats
- Warnings: `[yellow]` text
- Errors: `[red]` text — no raw tracebacks, all caught at CLI boundary

---

## Testing

### Fixtures (`tests/fixtures/`)

**`sample_fastapi/`** — small FastAPI app with:
- SQLAlchemy models (User, Post with FK relationship)
- Router with GET/POST routes
- Service layer calling repository layer
- `main.py` entry point

**`sample_django/`** — small Django app with:
- `models.Model` subclasses
- `urls.py` with `urlpatterns`
- `views.py` with function-based views
- `manage.py` entry point

**`sample_plain/`** — plain Python with:
- Abstract base class + concrete subclasses
- Dataclasses
- Module-level functions with call relationships
- No framework imports

### Test Files

**`test_analyzer.py`**
- `test_class_extraction` — verifies `ClassInfo` fields from fixture
- `test_function_extraction` — verifies `FunctionInfo` including async flag
- `test_import_classification` — stdlib vs third-party vs local
- `test_orm_detection` — SQLAlchemy and Django ORM models
- `test_route_extraction` — FastAPI and Django routes
- `test_entry_point_detection`
- `test_astroid_type_inference` — unannotated assignments get inferred type

**`test_diagrams.py`**
- One test per diagram generator: pass a fixture `AnalysisResult`, assert output starts with correct Mermaid header, assert empty state renders correctly
- No LLM calls in diagram tests

**`test_cli.py`**
- `test_analyze_no_llm` — runs `spartastruct analyze --no-llm` on `sample_plain/`, asserts `structure.md` created with all six sections
- `test_analyze_single_file` — `--file` mode
- `test_init_creates_config` — wizard flow with mocked `click.prompt`
- `test_config_missing_exits` — exits with code 1 and helpful message when no config

---

## Project File Structure

```
spartastruct/
├── spartastruct/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── analyzer/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── python_analyzer.py
│   ├── diagrams/
│   │   ├── __init__.py
│   │   ├── class_diagram.py
│   │   ├── er_diagram.py
│   │   ├── dfd.py
│   │   ├── flowchart.py
│   │   ├── function_graph.py
│   │   └── module_graph.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   └── prompts.py
│   ├── renderer/
│   │   ├── __init__.py
│   │   └── markdown_renderer.py
│   └── utils/
│       ├── __init__.py
│       ├── file_walker.py
│       └── framework_detector.py
├── templates/
│   └── structure.md.j2
├── tests/
│   ├── fixtures/
│   │   ├── sample_fastapi/
│   │   ├── sample_django/
│   │   └── sample_plain/
│   ├── test_analyzer.py
│   ├── test_diagrams.py
│   └── test_cli.py
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-05-05-spartastruct-design.md
├── pyproject.toml
├── README.md
├── CONTRIBUTING.md
└── .gitignore
```

---

## Key Constraints

- All public functions and classes have complete docstrings
- No raw Python tracebacks reach the user — all caught at CLI boundary, displayed via Rich
- All six diagrams always present in output; empty states render gracefully
- `spartadocs/` created if not exists; `structure.md` overwrite prompts user
- Tool works correctly from any subdirectory (walks upward for project root)
- Entire codebase passes `ruff` linting with default settings
- `astroid` used only for type inference on unannotated assignments; isolated in one helper
- LLM calls: six per run, one per diagram; any failure falls back silently to static diagram
- `litellm` is the single LLM interface; model string from config only, never hardcoded

---

## Config File (`~/.spartastruct/config.toml`)

```toml
[llm]
provider = "anthropic"          # Options: anthropic, openai, gemini, groq, mistral, cohere, together, ollama
model = "claude-sonnet-4-20250514"   # Any model string supported by litellm
temperature = 0.2
max_tokens = 4096

[api_keys]
anthropic = "sk-ant-..."        # Anthropic Claude
openai = "sk-..."               # OpenAI GPT models
gemini = ""                     # Google Gemini
groq = ""                       # Groq (fast open source inference)
mistral = ""                    # Mistral AI
cohere = ""                     # Cohere
together = ""                   # Together AI (open source models)

[ollama]
base_url = "http://localhost:11434"
model = "codellama"             # Any model pulled via `ollama pull`

[output]
default_folder = "spartadocs"
```

---

## Output File Header

```markdown
# ⚡ SpartaStruct — Project Architecture

| Field | Value |
|---|---|
| Project | <root folder name> |
| Generated | <ISO 8601 timestamp> |
| SpartaStruct Version | 0.1.0 |
| Files Analyzed | <count> |
| Language | Python |
| Framework(s) | <detected frameworks or "None detected"> |
| LLM Model | <model string or "Static Analysis Only"> |
```
