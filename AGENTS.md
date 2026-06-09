# 🤖 AGENTS.md — Instructions for AI Coding Agents

> Primary seed file for Claude Code, GitHub Copilot, Codex, Cursor.
> Read this file fully before writing a single line of code.
> NEXT_AGENT_PROMPT.md is deleted — do not recreate it.
> Each feature has its own FEATURE_*.md spec — read it before touching any file.

---

## Project Status (as of June 8, 2026)

**Core pipeline: COMPLETE and tested.**
**P1 Contradiction Drill-Down: COMPLETE and tested.**
**Current task: P2 Field Consensus Meter + AI Explanation.**
Spec: `FEATURE_field_consensus_meter.md`

What works today:
- Full pipeline: PDF → Foundry IQ → Extractor → Comparator → Gap Finder → Neo4j → WebSocket → D3.js
- A2A orchestration via Microsoft Agent Framework 1.0
- Live animated force graph with contradiction detection
- Node detail panel (click any node)
- Edge drill-down panel (click any edge) — shows two claims + Comparator reasoning

Do not refactor working code. Do not rename files. Do not restructure the pipeline.

---

## Non-Negotiables

- Agent framework: Microsoft Agent Framework 1.0 — not LangChain, not CrewAI
- Knowledge base: Azure AI Foundry IQ — not a custom vector store
- Graph DB: Neo4j — all Cypher queries stay in `graph_manager.py` only
- Backend: FastAPI — not Flask, not Django
- Frontend: D3.js v7 — not Cytoscape, not vis.js
- All secrets via `.env` — never hardcoded, never committed
- No Cypher outside `graph_manager.py`
- No Azure SDK calls outside agent classes and uploaders

---

## Codebase Map

```
src/
├── agents/
│   ├── base_agent.py              # BaseAgent: OpenAI + Foundry IQ + retry + from_env()
│   ├── cartographer.py            # A2A orchestrator
│   ├── comparator.py              # Cross-paper edge detection
│   ├── consensus_explainer.py     # ← NEW (P2): thin BaseAgent for consensus narrative
│   ├── extractor.py               # Claim extraction per paper
│   └── gap_finder.py              # Open question discovery via OpenAlex
├── api/
│   ├── routes/
│   │   ├── graph.py               # GET /graph, GET /edge/{id}, GET /claim/{id}/consensus/explain, WS /ws/graph
│   │   └── upload.py              # POST /upload
│   ├── limiter.py                 # Rate limiting (slowapi)
│   ├── main.py                    # FastAPI app + lifespan (initializes all app.state objects)
│   └── models.py                  # Pydantic models
├── frontend/
│   ├── favicon.svg
│   ├── graph.js                   # D3.js force graph + WebSocket + panel logic (IIFE)
│   ├── index.html                 # Single-page app shell
│   └── styles.css                 # Dark theme, CSS vars, all animations
└── graph/
    ├── delta_emitter.py           # WebSocket pub/sub
    ├── graph_manager.py           # Neo4j CRUD — ONLY file with Cypher
    └── schema.py                  # Dataclasses, enums, serializers
```

---

## API Contract (Current + P2)

```
POST /upload                                → { paper_id, status: "queued" }
GET  /graph                                 → { nodes, edges, questions }
GET  /paper/{paper_id}/status              → { paper_id, status, progress_pct }
GET  /edge/{edge_id}                       → EdgeDetailResponse
GET  /claim/{claim_id}/consensus/explain   → ConsensusExplainResponse  ← P2
```

WebSocket `WS /ws/graph` — server pushes delta events, client listens only.

---

## Frontend Architecture (graph.js)

Single IIFE. Key objects:

```javascript
state = {
    nodes: Map<id, node>,
    edges: Map<id, edge>,   // D3 mutates source/target to objects after simulation start
    simulation, svg, g, edgeGroup, nodeGroup,
    selectedNodeId, ws, zoom
}

dom = {
    detailPanel,   // #detail-panel
    panelTitle,    // #panel-title
    panelBody,     // #panel-body  ← NOT panelContent
    panelClose,
    statPapers, statClaims, statEdges, statQuestions, ...
}
```

### Functions already in graph.js — do not redefine

```javascript
openDetailPanel(node)          // renders node detail
openEdgeDetailPanel(edge)      // async, fetches /edge/{id}
getConnections(nodeId)         // returns connected edges from state.edges
closeDetailPanel()
render(animate)                // debounced D3 update
section(title, contentHtml)   // returns panel section HTML
badge(text, cls)               // returns badge span HTML
esc(str)                       // HTML-escapes — always use for user content
showToast(message, type)
```

### Edge ID resolution (critical — D3 mutates edges)

```javascript
const srcId = typeof e.source === "object" ? e.source.id : (e.source_claim_id || e.source);
const tgtId = typeof e.target === "object" ? e.target.id : (e.target_claim_id || e.target);
```

Always use this pattern when iterating `state.edges`. See `computeConsensus()` in the feature spec.

### Edge type field

```javascript
const type = (e.type || e.rel_type || "").toLowerCase();
// values: "supports", "contradicts", "extends", "replicates", "refines", "contains", "relates_to"
```

---

## CSS Design System

```css
--color-paper: #4a9eff
--color-finding: #00ff88      /* green / supports / consensus */
--color-method: #ffd700       /* yellow / contested */
--color-contradiction: #ff4444
--color-question: #ffffff
--color-concept: #9b59b6
--bg-primary: #0a0a1a
--bg-glass: rgba(15, 16, 28, 0.72)
--border-glass: rgba(255, 255, 255, 0.08)
--border-hover: rgba(255, 255, 255, 0.15)
--panel-width: 420px
--radius-sm: 8px
--radius-md: 14px
--transition-normal: 0.25s ease
--transition-fast: 0.15s ease
```

Reuse `.confidence-meter`, `.confidence-bar-bg`, `.confidence-bar-fill` for any percentage bar.
Use `backdrop-filter: blur(20px)` for glass panels.
Never hardcode hex values in JS or HTML — always `CONFIG.colors.*` or CSS vars.

---

## graph_manager.py Pattern

```python
# Read query
async def get_something(self, param: str) -> dict | None:
    query = "MATCH (n:Node {id: $id}) RETURN n"
    async with self._driver.session() as session:
        result = await session.run(query, {"id": param})
        record = await result.single()
        if not record:
            return None
        return dict(record["n"])

# Multi-node query (edge + connected nodes)
async def get_complex(self, param: str) -> dict | None:
    query = """
    MATCH (a)-[r]->(b)
    WHERE r.id = $id
    RETURN a, r, b
    """
    async with self._driver.session() as session:
        result = await session.run(query, {"id": param})
        record = await result.single()
        if not record:
            return None
        return {"a": dict(record["a"]), "r": dict(record["r"]), "b": dict(record["b"])}
```

For UNION ALL queries (see `get_claim_consensus_context`), collect with:
```python
records = [dict(r) async for r in edges_result]
```

---

## app.state Objects (set in main.py lifespan)

```python
app.state.graph_manager       # GraphManager — Neo4j interface
app.state.cartographer        # CartographerAgent — pipeline orchestrator
app.state.delta_emitter       # DeltaEmitter — WebSocket pub/sub
app.state.consensus_explainer # ConsensusExplainerAgent ← added in P2
```

Access in route handlers via `request.app.state.*`.

---

## BaseAgent.from_env()

All agents call `ClassName.from_env()` for instantiation — reads from environment variables.
`ConsensusExplainerAgent` inherits this from `BaseAgent`. No custom `__init__` needed.

---

## Security Rules

- All credentials in `.env` only
- Run `git diff --cached` before every commit
- `.env` is gitignored — never commit it
- No real values in `.env.example`
- No PII, no internal Microsoft info in code or comments

---

## Priorities for AI Agents

1. Never break working code
2. Read the FEATURE_*.md spec before touching any file
3. Implement in file order as listed in the spec
4. After completing a feature: delete FEATURE_*.md, tick TODO.md
5. Deadline: **June 14, 2026 11:59 PM PT**
