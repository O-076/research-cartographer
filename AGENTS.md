# AGENTS.md - Instructions for AI Coding Agents

> Primary seed file for Claude Code, GitHub Copilot, Codex, Cursor.
> Read this fully before writing a single line of code.
> Each feature has its own FEATURE_*.md — read it before touching any file.

---

## Project Status (as of June 11, 2026)

**All features complete and tested.**

- Core pipeline (PDF ingestion, 4 agents, Neo4j, WebSocket, D3.js graph)
- P1 Contradiction Drill-Down
- P2 Field Consensus Meter + AI Explanation
- P3 Claim Verification
- P4 Research Thread Tracer
- P5 Literature Review Generator + .docx download

**Remaining work: demo video and submission checklist.**
See TODO.md.

Do not refactor working code. Do not rename files. Do not restructure the pipeline.
**Deadline: June 14, 2026 11:59 PM PT**

---

## Track

**Creative Apps** - Microsoft Agents League Hackathon 2026
IQ layer: Foundry IQ

---

## Non-Negotiables

- Knowledge base: Azure AI Foundry IQ
- Graph DB: Neo4j - all Cypher stays in `graph_manager.py` only
- Backend: FastAPI
- Frontend: D3.js v7
- All secrets in `.env` - never hardcoded, never committed
- No Cypher outside `graph_manager.py`

---

## Codebase Map

```
src/
├── agents/
│   ├── base_agent.py                 # get_embedding(), cosine_similarity(), chat_completion()
│   ├── cartographer.py               # async pipeline orchestrator + metadata extraction
│   ├── claim_verifier.py             # cosine similarity pre-filter + batch LLM classify
│   ├── comparator.py                 # cross-paper edge detection
│   ├── consensus_explainer.py        # consensus narrative generation
│   ├── extractor.py                  # structured claim extraction from Foundry IQ chunks
│   ├── gap_finder.py                 # open question discovery via OpenAlex
│   ├── literature_review_agent.py    # APA-format literature review generation
│   └── thread_tracer.py              # reasoning chain narrative
├── api/
│   ├── routes/
│   │   ├── graph.py                  # all GET/POST endpoints + build_apa_docx()
│   │   └── upload.py                 # POST /upload
│   ├── limiter.py
│   ├── main.py                       # FastAPI app + lifespan
│   └── models.py                     # all Pydantic models
├── frontend/
│   ├── graph.js                      # D3.js IIFE - all client logic
│   ├── index.html
│   └── styles.css
└── graph/
    ├── delta_emitter.py              # WebSocket pub/sub
    ├── graph_manager.py              # ONLY file with Cypher
    └── schema.py
```

---

## API Contract (complete)

```
POST /upload                                → UploadResponse
GET  /graph                                 → GraphResponse
GET  /paper/{paper_id}/status              → PaperStatusResponse
GET  /edge/{edge_id}                       → EdgeDetailResponse
GET  /claim/{claim_id}/consensus/explain   → ConsensusExplainResponse
GET  /verify?statement={text}              → VerificationResponse
GET  /trace?from_id={id}&to_id={id}        → TraceResponse
POST /generate/review                      → LiteratureReviewResponse
POST /generate/review/docx                 → .docx binary download
WS   /ws/graph                             → delta event stream
```

---

## app.state Objects

```python
app.state.graph_manager        # GraphManager
app.state.cartographer         # CartographerAgent
app.state.emitter              # DeltaEmitter  (name is "emitter", not "delta_emitter")
app.state.consensus_explainer  # ConsensusExplainerAgent()
app.state.claim_verifier       # ClaimVerifierAgent()
app.state.thread_tracer        # ThreadTracerAgent()
app.state.literature_review    # LiteratureReviewAgent()
```

All agents: `AgentClass()` with no arguments.

---

## BaseAgent Methods

```python
await self.get_embedding(text: str) -> list[float]
self.cosine_similarity(a: list[float], b: list[float]) -> float
await self.chat_completion(user_prompt, json_mode, max_tokens, temperature) -> str
```

---

## Frontend (graph.js)

Single IIFE. The panel body element is `dom.panelBody` (#panel-body).

State object includes:
```javascript
state = {
    nodes: new Map(), edges: new Map(),
    simulation, svg, g, edgeGroup, nodeGroup,
    zoom, ws, wsReconnectTimer, wsReconnectDelay,
    selectedNodeId, tooltip,
    traceStartNodeId: null,
    tracePath: null,
}
```

Edge ID resolution (D3 mutates source/target after simulation starts):
```javascript
const srcId = typeof e.source === "object" ? e.source.id : (e.source_claim_id || e.source);
const tgtId = typeof e.target === "object" ? e.target.id : (e.target_claim_id || e.target);
```

---

## CSS Design System

```css
--color-paper: #4a9eff
--color-finding: #00ff88
--color-method: #ffd700
--color-contradiction: #EF4444
--color-concept: #8B5CF6
--color-question: #F3F4F6
--bg-glass: rgba(15, 16, 28, 0.72)
--border-glass: rgba(255, 255, 255, 0.08)
```

CONFIG.colors: `.supports = "#10B981"`, `.contradicts = "#ff4444"`, `.finding = "#00ff88"`

---

## Security

- All credentials in `.env` - never hardcoded
- `git diff --cached` before every commit
- No real values in `.env.example`
- No PII in code or comments
