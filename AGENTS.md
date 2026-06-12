# 🤖 AGENTS.md — Instructions for AI Coding Agents

> Primary seed file for Claude Code, GitHub Copilot, Codex, Cursor.
> Read this fully before writing a single line of code.
> NEXT_AGENT_PROMPT.md is deleted — do not recreate it.
> Each feature has its own FEATURE_*.md — read it before touching any file.
> Implement FEATURE_research_thread_tracer.md BEFORE FEATURE_literature_review.md.

---

## Project Status (as of June 11, 2026)

**Core pipeline: COMPLETE.**
**P1 Contradiction Drill-Down: COMPLETE.**
**P2 Field Consensus Meter + AI Explanation: COMPLETE.**
**P3 Claim Verification: COMPLETE.**
**Current: P4 Research Thread Tracer → then P5 Literature Review.**

Do not refactor working code. Do not rename files. Do not restructure the pipeline.
**Deadline: June 14, 2026 11:59 PM PT — 3 days left.**

---

## Non-Negotiables

- Agent framework: Microsoft Agent Framework 1.0
- Knowledge base: Azure AI Foundry IQ
- Graph DB: Neo4j — ALL Cypher stays in `graph_manager.py`
- Backend: FastAPI
- Frontend: D3.js v7
- All secrets in `.env` — never hardcoded
- No Cypher outside `graph_manager.py`

---

## Codebase Map

```
src/
├── agents/
│   ├── base_agent.py                 # BaseAgent with get_embedding(), cosine_similarity(),
│   │                                 #   chat_completion(), parse_json_list()
│   ├── cartographer.py               # A2A orchestrator
│   ├── claim_verifier.py             # ✅ P3: cosine similarity + batch LLM classify
│   ├── comparator.py
│   ├── consensus_explainer.py        # ✅ P2
│   ├── extractor.py
│   ├── gap_finder.py
│   ├── literature_review_agent.py    # ← P5: NEW
│   └── thread_tracer.py              # ← P4: NEW
├── api/
│   ├── routes/
│   │   ├── graph.py                  # All GET/POST endpoints + build_apa_docx()
│   │   └── upload.py
│   ├── limiter.py
│   ├── main.py                       # FastAPI app + lifespan
│   └── models.py
├── frontend/
│   ├── favicon.svg
│   ├── graph.js                      # D3.js IIFE — all client logic
│   ├── index.html
│   └── styles.css
└── graph/
    ├── delta_emitter.py
    ├── graph_manager.py              # ONLY file with Cypher
    └── schema.py
```

---

## API Contract (Current + P4 + P5)

```
POST /upload                                → UploadResponse
GET  /graph                                 → GraphResponse
GET  /paper/{paper_id}/status              → PaperStatusResponse
GET  /edge/{edge_id}                       → EdgeDetailResponse
GET  /claim/{claim_id}/consensus/explain   → ConsensusExplainResponse
GET  /verify?statement={text}              → VerificationResponse
GET  /trace?from_id={id}&to_id={id}        → TraceResponse          ← P4
POST /generate/review                      → LiteratureReviewResponse ← P5
POST /generate/review/docx                 → .docx binary download   ← P5
```

WebSocket `WS /ws/graph` — server pushes, client listens only.

---

## app.state Objects (set in main.py lifespan)

```python
app.state.graph_manager        # GraphManager
app.state.cartographer         # CartographerAgent
app.state.emitter              # DeltaEmitter  ← name is "emitter" not "delta_emitter"
app.state.consensus_explainer  # ConsensusExplainerAgent()
app.state.claim_verifier       # ClaimVerifierAgent()
app.state.thread_tracer        # ThreadTracerAgent()        ← P4
app.state.literature_review    # LiteratureReviewAgent()    ← P5
```

All agents instantiated with **no arguments**: `AgentClass()`.

---

## BaseAgent Methods

```python
await self.get_embedding(text: str) -> list[float]
self.cosine_similarity(a: list[float], b: list[float]) -> float   # pure Python, no numpy
await self.chat_completion(user_prompt, json_mode, max_tokens, temperature) -> str
self.parse_json_list(raw, model, list_key) -> list[T]
await self.query_foundry_iq(query, paper_id, section, top_k) -> list[dict]
```

---

## Frontend Architecture (graph.js)

Single IIFE. Key state fields (current + additions):

```javascript
const state = {
    nodes: new Map(),
    edges: new Map(),
    simulation: null, svg: null, g: null,
    edgeGroup: null, nodeGroup: null,
    zoom: null, ws: null,
    wsReconnectTimer: null,
    wsReconnectDelay: CONFIG.ws.reconnectDelay,
    selectedNodeId: null,
    tooltip: null,
    traceStartNodeId: null,   // ← P4: id of trace-start node | null
    tracePath: null,           // ← P4: { nodeIds: Set, edgeIds: Set } | null
};
```

Key DOM refs (current + additions):

```javascript
dom = {
    detailPanel, panelTitle, panelBody, panelClose,
    searchBtn, searchOverlay, searchInput,            // ← P3
    reviewBtn, reviewModal, reviewContent,            // ← P5
    reviewDownloadBtn, reviewCloseBtn,                // ← P5
    statPapers, statClaims, statEdges, statQuestions,
    uploadDropzone, fileInput, ...
}
```

**Note:** The dom refs for review elements are added in Step 6f of
FEATURE_research_thread_tracer.md (even though the HTML elements are added in P5).
They return `null` until the HTML is added — this is safe.

### Functions in graph.js — do not redefine

```javascript
openDetailPanel(node)
openEdgeDetailPanel(edge)        // async
computeConsensus(claimId)
explainConsensus(claimId, pct, btn)  // async
handleTraceClick(node)           // ← P4
traceThread(fromId, toId)        // ← P4, async
openTracePanel(data)             // ← P4
initSearch(), openSearchOverlay(), closeSearchOverlay()
verifyStatement(statement)       // async
openVerificationPanel(data)
renderVerifyResults(results)
initReview()                     // ← P5
generateReview()                 // ← P5, async
openReviewModal(), closeReviewModal()
renderReview(data)               // ← P5
downloadReviewDocx(review)       // ← P5, async
getConnections(nodeId)
closeDetailPanel()
render(animate)
section(title, html), badge(text, cls)
esc(str), truncate(str, len)
showToast(message, type)
```

### Node click handler (lines 3307–3312) — already modified in P4

```javascript
nodeEnter.on("click", (event, d) => {
    event.stopPropagation();
    if (event.shiftKey) {
        handleTraceClick(d);
    } else {
        openDetailPanel(d);
    }
})
```

### Edge resolution pattern

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
--border-hover: rgba(255, 255, 255, 0.15)
--panel-width: 420px
--radius-sm: 8px; --radius-md: 14px
--transition-fast: 0.15s ease; --transition-normal: 0.25s ease
```

CONFIG.colors in JS:
```javascript
CONFIG.colors = {
    paper: "#4a9eff", finding: "#00ff88", method: "#ffd700",
    contradiction: "#EF4444", concept: "#8B5CF6", question: "#F3F4F6",
    supports: "#10B981", contradicts: "#ff4444",
    extends: "#4a9eff", replicates: "#6b7280", refines: "#6b7280",
}
```

**Note:** `CONFIG.colors.supports = "#10B981"` (green) ≠ `CONFIG.colors.finding = "#00ff88"`.
Use `CONFIG.colors.supports` for edge support color, `CONFIG.colors.finding` for claim node color.

---

## graph_manager.py Pattern

```python
async with self._driver.session() as session:
    result = await session.run(query, params)
    records = [dict(r) async for r in result]   # for multiple rows
    record = await result.single()               # for single row (returns None if missing)
```

UNION ALL queries (used in get_claim_consensus_context):
```python
records = [dict(r) async for r in result]  # same pattern — async for works on UNION ALL
```

---

## index.html Key Locations

- Header right side buttons: after `#search-btn` (line 4468)
- Zoom controls: `.zoom-controls` div (lines 4516–4521)
- Search overlay: after `<script src="graph.js">` (line 4578)
- Before `</body>`: line 4598 — add review modal here

---

## Security

- All credentials in `.env` only
- `git diff --cached` before every commit
- No real values in `.env.example`
- No PII or internal info in code or comments

---

## Priorities

1. Never break working code
2. Read the FEATURE_*.md spec before touching any file
3. Implement in file order listed in the spec
4. P4 (thread tracer) before P5 (literature review) — P5 depends on dom refs added in P4
5. After completing: delete FEATURE_*.md, tick TODO.md
6. **Deadline: June 14, 2026 11:59 PM PT**
