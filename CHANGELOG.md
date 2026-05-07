# Changelog

All notable changes to SpartaStruct are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

---

## [Unreleased]

---

## [0.2.2] — 2026-05-06

### Changed
- Mermaid CLI (`mmdc`) no longer needs to be installed manually. SpartaStruct now uses `npx` automatically — only Node.js is required.

---

## [0.2.1] — 2026-05-06

### Changed
- CLI help text updated to reflect Python, JavaScript, and TypeScript support
- README project structure section updated to include all 11 diagram files
- `spartastruct analyze --format` usage examples added to README

---

## [0.2.0] — 2026-05-06

### Added
- **5 new diagram types** (total now 11):
  - Sequence Diagram (`sequenceDiagram`) — Client → Router → Service → Repo → DB call flow
  - State Diagram (`stateDiagram-v2`) — detects state machine classes and transition methods
  - API Endpoint Map (`flowchart LR`) — all HTTP routes grouped by resource, colour-coded by method
  - Component / Service Map (`graph TD`) — logical architecture layers (Controllers → Services → Repositories → Models)
  - Event & Message Flow (`flowchart LR`) — Celery tasks, event emitters, async functions
- LLM system prompts for all 5 new diagram types
- `DiagramSection.static_mermaid` fallback field — if LLM-improved Mermaid fails to render, automatically retries with the static version
- `--format both` option to export PDF and PNG simultaneously

### Fixed
- LLM rate limit errors on large projects: prompt size capped (80 classes / 50 routes / 100 files / 4,000 diagram chars) + exponential backoff retry (15s → 30s → 60s)
- `mmdc` errors now surface the full stderr in the exception message
- `maxTextSize` now correctly passed to `mmdc` via `--configFile` JSON (the `%%{init}%%` directive in `.mmd` source is ignored by `mmdc`)

---

## [0.1.3] — 2026-04-xx

### Added
- JavaScript and TypeScript support (regex-based analyzer)
- PNG export (`--format png`, transparent background, 3× scale)
- Polyglot project support — Python and JS/TS analyzers run together and results are merged

### Fixed
- README images now use absolute GitHub raw URLs so they render correctly on PyPI

---

## [0.1.2] — 2026-04-xx

### Fixed
- Fall back to static diagram when LLM output contains invalid Mermaid syntax

---

## [0.1.1] — 2026-04-xx

### Added
- PyPI package metadata (author, license, classifiers, project URLs)

### Fixed
- `mmdc` stderr is now included in error messages for easier debugging

---

## [0.1.0] — 2026-04-xx

### Added
- Initial release
- 6 diagram types: Class Diagram, ER Diagram, Data Flow Diagram, Flowchart, Function Call Graph, Module Dependency Graph
- Python AST-based analyzer (classes, functions, routes, ORM models, imports)
- LLM enrichment via litellm (any provider)
- PDF export via `mmdc`
- CLI: `analyze`, `init`, `config`
- TOML config at `~/.spartastruct/config.toml`

[Unreleased]: https://github.com/yashrandive11/spartastruct/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/yashrandive11/spartastruct/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/yashrandive11/spartastruct/compare/v0.1.3...v0.2.0
[0.1.3]: https://github.com/yashrandive11/spartastruct/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/yashrandive11/spartastruct/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/yashrandive11/spartastruct/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/yashrandive11/spartastruct/releases/tag/v0.1.0
