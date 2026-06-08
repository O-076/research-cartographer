# 🤖 AGENTS.md — Instructions for AI Coding Agents

> Primary seed file for Claude Code, GitHub Copilot, Codex, Cursor, and any other AI coding agent.
> Read this file fully before writing a single line of code.
> NEXT_AGENT_PROMPT.md is deprecated — do not create or use it.

---

## Project Status (as of June 7, 2026)

**Core pipeline: COMPLETE and tested.**
Days 1–8 are fully implemented and verified with real papers.
The system is running at localhost:8000. Do not refactor working code.

What works today:
- PDF upload → Foundry IQ → Extractor → Comparator → Gap Finder (OpenAlex) → Neo4j → WebSocket → D3.js graph
- A2A orchestration via Microsoft Agent Framework 1.0
- Live animated force graph with contradiction detection
- Side panel for node details (click any node)
- 10-paper performance tested

**Current work: Phase 2 research intelligence features.**
See TODO.md for the prioritized list. Start with the contradiction drill-down.
The detailed spec for it is in `FEATURE_contradiction_drill_down.md`.

---

## Non-Negotiables — Do Not Change These

- Agent framework: Microsoft Agent Framework 1.0 — not LangChain, not CrewAI
- Knowledge base: Azure AI Foundry IQ — not a custom vector store
- Graph DB: Neo4j — all Cypher queries in `graph_manager.py` only
- Backend: FastAPI — not Flask, not Django
- Frontend graph: D3.js v7 — not Cytoscape, not vis.js
- All secrets via `.env` — never hardcoded, never committed
- No Cypher queries outside `src/graph/graph_manager.py`
- No Azure SDK calls outside agent classes and uploaders

---

## Codebase Map

```
src/
├── agents/
│   ├── base_agent.py          # BaseAgent: OpenAI + Foundry IQ + retry
│   ├── cartographer.py        # A2A orchestrator — coordinates pipeline
│   ├── comparator.py          # Cross-paper edge detection
│   ├── extractor.py           # Claim extraction per paper
│   └── gap_finder.py          # Open question discovery via OpenAlex
├── api/
│   ├── routes/
│   │   ├── graph.py           # GET /graph, GET /edge/{id}, WS /ws/graph
│   │   └── upload.py          # POST /upload
│   ├── limiter.py             # Rate limiting
│   ├── main.py                # FastAPI app entry + lifespan
│   └── models.py              # Pydantic request/response models
├── frontend/
│   ├── favicon.svg
│   ├── graph.js               # D3.js force graph + WebSocket client
│   ├── index.html             # Single-page app shell
│   └── styles.css             # Dark theme, CSS vars, animations
└── graph/
    ├── delta_emitter.py       # WebSocket pub/sub
    ├── graph_manager.py       # Neo4j CRUD — ONLY file with Cypher
    └── schema.py              # Dataclasses, enums, serializers
```

---

## Data Schemas (Current — Do Not Change)

### Claim node (Neo4j + frontend)
```python
{
    "id": "uuid",
    "paper_id": "uuid",
    "text": "str",
    "type": "finding|method|assumption|limitation",
    "confidence": 0.0–1.0,
    "section": "abstract|intro|methods|results|discussion|unknown",
    "embedding": [float],           # stored in Neo4j, excluded from WS events
    "source_chunk_text": "str",     # raw text the claim was extracted from
    "created_at": "iso8601"
}
```

### Edge relationship (Neo4j + frontend)
```python
{
    "id": "uuid",
    "source_claim_id": "uuid",
    "target_claim_id": "uuid",
    "type": "supports|contradicts|extends|replicates|refines",
    "strength": 0.0–1.0,
    "reasoning": "str",             # Comparator's explanation
    "created_at": "iso8601"
}
```

### Paper node
```python
{
    "id": "uuid",
    "title": "str",
    "authors": ["str"],
    "year": int | None,
    "abstract": "str",
    "status": "queued|extracting|claims_ready|comparing|edges_ready|gap_finding|complete|error"
}
```

---

## API Contract (Current)

### REST
```
POST /upload                        → { paper_id, status: "queued" }
GET  /graph                         → { nodes, edges, questions }
GET  /paper/{paper_id}/status       → { paper_id, status, progress_pct }
GET  /edge/{edge_id}                → EdgeDetailResponse  ← TO BE BUILT
GET  /claim/{claim_id}/consensus    → ConsensusResponse   ← TO BE BUILT
GET  /verify?statement={text}       → VerificationResponse ← TO BE BUILT
```

### WebSocket  `WS /ws/graph`
```
Server → Client:
  { "type": "node_added",         "data": { node },          "timestamp": "iso" }
  { "type": "edge_added",         "data": { edge },          "timestamp": "iso" }
  { "type": "edge_updated",       "data": { edge },          "timestamp": "iso" }
  { "type": "question_added",     "data": { question },      "timestamp": "iso" }
  { "type": "question_resolved",  "data": { question_id },   "timestamp": "iso" }
  { "type": "paper_status",       "data": { paper_id, status }, "timestamp": "iso" }
```

---

## Frontend Architecture (graph.js)

The entire frontend is one IIFE in `graph.js`. Key objects:

```javascript
state = {
    nodes: Map<id, node>,       // all nodes keyed by id
    edges: Map<id, edge>,       // all edges keyed by id
    simulation: d3.forceSimulation,
    svg: d3Selection,
    g: d3Selection,             // main group (zoom/pan target)
    edgeGroup: d3Selection,     // edges rendered below nodes
    nodeGroup: d3Selection,     // nodes rendered above edges
    selectedNodeId: str | null,
    ws: WebSocket,
    zoom: d3.zoom
}

dom = {
    // All DOM element references — populated in init()
    detailPanel, panelTitle, panelContent,
    statPapers, statClaims, statEdges, statQuestions, statConcepts,
    statContradictions, statLimitations,
    uploadDropzone, fileInput, ...
}
```

Key functions:
- `render(animate: bool)` — debounced (50ms), full D3 update cycle
- `openDetailPanel(node)` — renders node details in right sidebar
- `handleWsEvent(msg)` — WebSocket message dispatcher
- `recomputeDerivedFields()` — recalculates `_connectionCount` and `_hasContradiction` on all nodes

**When adding a new panel type** (e.g., edge detail panel):
- Add the HTML section to `index.html` inside `#detail-panel`
- Add the rendering function to `graph.js` (follow `openDetailPanel` pattern)
- Add CSS to `styles.css` using existing CSS vars

---

## CSS Design System (styles.css)

All colors via CSS custom properties — never hardcode hex values in JS or HTML:

```css
--color-paper: #4a9eff
--color-finding: #00ff88
--color-method: #ffd700
--color-contradiction: #ff4444
--color-question: #ffffff
--color-concept: #9b59b6

--edge-supports: #00ff88
--edge-contradicts: #ff4444
--edge-extends: #4a9eff
--edge-replicates: #6b7280
--edge-refines: #6b7280

--bg-primary: #0a0a1a
--bg-glass: rgba(15, 16, 28, 0.72)
--border-glass: rgba(255, 255, 255, 0.08)
--panel-width: 420px
```

Use `backdrop-filter: blur(20px)` for glass panels. Use `var(--transition-normal)` for animations.

---

## graph_manager.py Conventions

Every new query follows this pattern:

```python
# Read query
async def get_something(self, param: str) -> list[dict[str, Any]]:
    query = """
    MATCH (n:NodeType {id: $id})
    RETURN n
    """
    return await self._read_nodes(query, {"id": param}, "n")

# Write query
async def add_something(self, obj: SomeDataclass) -> None:
    query = """
    MERGE (n:NodeType {id: $id})
    SET n += $props
    """
    await self._write(query, {"id": obj.id, "props": to_props(obj)}, "add_something")
```

For queries returning multiple node types (e.g., edge + two claims + two papers):
use `_read_raw(query, params)` which returns raw Neo4j records.

---

## models.py Conventions

Every new endpoint gets a Pydantic response model:

```python
class EdgeDetailResponse(BaseModel):
    edge: dict[str, Any]
    source_claim: dict[str, Any]
    target_claim: dict[str, Any]
    source_paper: dict[str, Any]
    target_paper: dict[str, Any]
```

---

## Security Rules

- All credentials in `.env` only — see SECURITY.md
- Run `git diff --cached` before every commit
- Never commit `.env` — it is gitignored
- No real values in `.env.example`
- No PII, no internal Microsoft info, no API keys in code or comments

---

## Priorities for AI Agents

1. **Never break working code.** The pipeline runs. Don't refactor it.
2. **Phase 2 features in order** — see TODO.md. Contradiction drill-down is next.
3. **Read the feature spec file** before implementing any Phase 2 feature.
4. **Demo video papers** — transformer papers listed in TODO.md. Use these.
5. **Submission deadline: June 14, 2026 11:59 PM PT.** No extensions.

---

## Key Links

- Foundry IQ docs: https://learn.microsoft.com/azure/foundry/agents/concepts/what-is-foundry-iq
- A2A Protocol: https://aka.ms/a2a
- IQ Series: https://aka.ms/iq-series
- Discord: https://aka.ms/agentsleague/discord
- Foundry Forum: https://aka.ms/foundry/forum
