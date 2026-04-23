# AGENTS.md

Operational guidance for coding agents in `C:\Repos\Dynamic-NPCs`.

## Scope
- Prefer small, targeted edits over broad refactors.
- Follow existing patterns in `src/`.
- Treat `test_old/` as legacy unless explicitly requested.
- Preserve existing Swedish domain text unless asked to change language.
- Use proper Swedish characters (`å`, `ä`, `ö`) in Swedish-facing text (prompts, UI labels, messages, docs).

## Project layout
- `src/api/` - FastAPI app and HTTP middleware.
- `src/services/` - chat/NPC service layer and interactive CLI.
- `src/rag/` - retrieval pipeline and rendering.
- `src/prompting/` - prompt models, policy, and builder.
- `src/db/` - Neo4j config, repositories, commands, UI, seeds.
- `test/` - script-based test/integration flows (not formal pytest suite).

## Cursor/Copilot instruction files
- `.cursorrules`: not found.
- `.cursor/rules/`: not found.
- `.github/copilot-instructions.md`: not found.
- Use this file and local code conventions as the active agent rules.

## Setup
```bash
python -m venv .venv
# PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Set module path when running from repo root (imports are rooted at `src/`):

```powershell
$env:PYTHONPATH = "src"
```

```bash
export PYTHONPATH=src
```

### Required environment variables
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- `HF_TOKEN`
- `API_KEY`
- provider key(s) required by the configured chat/prompt-guard providers, e.g. `GROQ_API_KEY` and/or `MISTRAL_API_KEY`

### Optional environment variables
- `EMBED_MODEL` (defaults to `mixedbread-ai/mxbai-embed-large-v1`), `GEMINI_API_KEY` (Gemini adapter only), `CHAT_PROVIDER`, `PROMPT_GUARD_PROVIDER`

## Build / lint / test commands

No repository-level lint/type/test config files were found (`pyproject.toml`, `pytest.ini`, `ruff.toml`, `mypy.ini`, `setup.cfg` absent).

Use these commands as the current baseline:

```bash
# Build/sanity
python -m compileall src

# Optional lint/type checks if tools are installed
ruff check src test
black --check src test
mypy src

# Fallback if lint tools are unavailable
python -m compileall src test

# Script-based tests (current reality)
python test/test.py
python test/ragtest.py
python test/builder.py
```

### Single-test workflow (important)
Today, "single test" means running one script directly:

```bash
python test/ragtest.py
```

Or call one specific helper:

```bash
python -c "from test.ragtest import get_prompt_test; print(get_prompt_test())"
```

If pytest tests are later introduced, use:

```bash
pytest test/path_to_file.py::test_name
```

## Common run commands
```bash
# DB builder CLI
python src/db/cli.py

# RAG CLI
python src/rag/cli.py

# Chat CLI
python src/services/cli.py

# API server
python -m uvicorn api.api:app --host 0.0.0.0 --port 8000 --reload

# Seed data
python -m db.seeds.otroheten
```

## Code style guidelines

## Prompt structure contract (important)
- Keep prompt assembly centralized in `src/prompt_builder/`.
- `services/chat_service.py` may collect data (player profile, recent exchanges, ids), but should not manually inject/concatenate prompt text.
- `system` message contains all operational context and rules:
  - character identity
  - rules/policy
  - world/RAG context
  - detective/player context
  - recent conversation context
- `user` message contains only the user question payload (no extra context blocks).
- Preserve the explicit boundary markers in task rendering (`<QUESTION> ... </QUESTION>`) so question text is isolated from system context.
- If adding new context sources, add them as dedicated prompt-builder sections, not ad-hoc string edits in services/api.

### Agent mode reminder
- Assume build mode unless explicitly constrained by the current system/developer instructions.
- In build mode you may edit files, run shell commands, and use tools needed to complete the task.

### Imports
- Order: standard library, third-party, local project imports.
- Use one blank line between import groups.
- In package internals, prefer relative imports (`from .x import Y`).
- Across `src` top-level packages, absolute imports (`from db...`, `from services...`) are acceptable; match local file style.

### Formatting and structure
- Use 4-space indentation and PEP 8-style formatting.
- Prefer clear, small functions over dense multi-purpose logic.
- Use f-strings for interpolation.

### Types
- Add type hints for new/edited public functions.
- Prefer modern annotations: `X | None`, `list[str]`, `dict[str, Any]`.
- Continue using dataclasses for core domain models where appropriate.
- Keep repository/service boundaries explicit in return shapes (`None`/`bool`/dataclass/dict with stable keys).

### Naming conventions
- `snake_case` for modules, functions, variables.
- `PascalCase` for classes.
- Common suffixes: `*Repo`, `*Service`, `*Command`.

### Error handling
- Validate critical env vars early and fail fast (`RuntimeError`).
- API layer should raise/return `HTTPException` for HTTP-facing failures.
- Preserve explicit HTTP exceptions; map unexpected errors to 500-level responses.
- Repositories typically return `None` or `False` for not-found cases.
- Always close resources using `try/finally` (see `Config.close()`).

### Neo4j and query safety
- Keep Cypher in repository/command layers, not scattered through UI/API code.
- all Cypher queries must go through `db/repositories/` (or `db/commands/` for CLI command flows), never directly from `services/`, `rag/`, or API handlers.
- Always use parameterized queries (`$param`).
- Do not concatenate user input directly into query strings.
- Keep schema semantics consistent with `src/db/SCHEMA.md`.

### API/service boundaries
- Keep FastAPI handlers thin; delegate logic to services.
- Use Pydantic models for request/response payloads.
- Keep retrieval and prompt composition inside `rag/` + `prompting/` modules.

### Testing expectations for agents
- Run at least one relevant `test/` script after logic changes.
- For API changes, run a health check and one endpoint path when possible.
- If checks cannot run (missing credentials/services), state that explicitly.

## Agent checklist before finishing
- Confirm touched code follows local import and naming patterns.
- Ensure resource cleanup is preserved (`close()` in `finally`).
- Run minimal compile/test command(s) relevant to the change.
- Do not add secrets; keep `.env` untracked.
