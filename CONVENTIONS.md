# 📐 CONVENTIONS.md — Code Conventions

> AI agents: follow these conventions in every file you write. Consistency matters for a hackathon — reviewers skim code fast.

---

## Python Style

- **Version:** Python 3.11+
- **Formatter:** `black` (default settings)
- **Linter:** `ruff`
- **Type hints:** required on all function signatures
- **Docstrings:** Google style, one-line for simple functions, full for complex ones
- **Imports:** stdlib first, third-party second, local third — separated by blank lines

```python
# ✅ Correct
import asyncio
import json
from dataclasses import dataclass

import httpx
from neo4j import AsyncGraphDatabase

from src.graph.schema import Claim, Edge
```

---

## Naming Conventions

| Thing | Convention | Example |
|-------|-----------|---------|
| Files | `snake_case.py` | `graph_manager.py` |
| Classes | `PascalCase` | `ExtractorAgent` |
| Functions | `snake_case` | `extract_claims` |
| Async functions | `snake_case` (same) | `async def extract_claims` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_CHUNK_SIZE = 500` |
| Variables | `snake_case` | `paper_id` |
| Neo4j node labels | `PascalCase` | `:Claim`, `:OpenQuestion` |
| Neo4j relationship types | `UPPER_SNAKE_CASE` | `CONTRADICTS`, `SUPPORTS` |
| WebSocket event types | `snake_case` | `"node_added"`, `"edge_updated"` |
| Environment variables | `UPPER_SNAKE_CASE` | `AZURE_OPENAI_KEY` |

---

## File Structure Within a Module

Every Python file follows this order:

```python
"""Module docstring."""

# 1. Imports (stdlib, third-party, local)

# 2. Constants

# 3. Dataclasses / TypedDicts / Enums

# 4. Main class(es)

# 5. Standalone functions

# 6. if __name__ == "__main__": (only for scripts)
```

---

## Error Handling

- **Never** use bare `except:` — always catch specific exceptions
- Log errors with context (paper_id, chunk_index, etc.)
- Agents should **never crash the pipeline** — catch, log, continue
- Use custom exceptions for domain errors:

```python
class ExtractionError(Exception): pass
class GraphWriteError(Exception): pass
class FoundryQueryError(Exception): pass
```

---

## Async Rules

- All I/O is async — no blocking calls in async functions
- Use `asyncio.create_task()` for fire-and-forget pipeline steps
- Use `asyncio.gather()` for parallel independent operations
- Never use `time.sleep()` — use `asyncio.sleep()`
- Never use `requests` — use `httpx.AsyncClient`

---

## Logging

```python
import logging
logger = logging.getLogger(__name__)

# Use correlation IDs in every log line
logger.info("Extracting claims", extra={"paper_id": paper_id})
logger.error("Extraction failed", extra={"paper_id": paper_id, "error": str(e)})
```

Log levels:
- `DEBUG`: internal agent reasoning steps
- `INFO`: pipeline stage transitions, node/edge counts
- `WARNING`: skipped items, fallbacks triggered
- `ERROR`: failures that don't stop the pipeline
- `CRITICAL`: failures that stop everything

---

## LLM Prompt Rules

- System prompts go in the agent class as a `SYSTEM_PROMPT` class constant
- Always request JSON output explicitly: `"Respond ONLY with valid JSON. No preamble."`
- Always include the expected output schema in the prompt
- Always validate parsed JSON against a Pydantic model before use
- Log the raw LLM response at DEBUG level (never at INFO — too noisy)

---

## D3.js / JavaScript Conventions

- No build step, no npm — plain ES modules via CDN
- `const` by default, `let` only when reassignment is needed, never `var`
- Function names: `camelCase`
- Event handlers: `on` + PascalCase noun (`onNodeClick`, `onEdgeUpdate`)
- DOM IDs: `kebab-case` (`graph-container`, `side-panel`)
- CSS classes: `kebab-case` (`node-claim`, `edge-contradicts`)

---

## Git Commit Messages

Format: `type(scope): short description`

Types: `feat`, `fix`, `refactor`, `docs`, `style`, `test`

```
feat(extractor): add embedding deduplication for claims
fix(comparator): handle empty claim list gracefully
feat(frontend): add glow animation for new nodes
docs(readme): add demo video link
```

Keep commits small and focused. One logical change per commit.

---

## What Not to Do

- ❌ No `print()` statements in production code — use `logger`
- ❌ No hardcoded strings that should be constants
- ❌ No synchronous HTTP calls in async code
- ❌ No Cypher queries outside `graph_manager.py`
- ❌ No direct Azure SDK calls outside the agent classes and uploaders
- ❌ No `TODO` comments in committed code — add to TODO.md instead
- ❌ No commented-out code committed — delete it
