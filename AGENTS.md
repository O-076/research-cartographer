# 🤖 AGENTS.md — Instructions for AI Coding Agents

> Primary seed file for Claude Code, GitHub Copilot, Codex, Cursor.
> Read this file fully before writing a single line of code.
> NEXT_AGENT_PROMPT.md is deleted — do not recreate it.
> Each feature has its own FEATURE_*.md spec — read it before touching any file.

---

## Project Status (as of June 9, 2026)

**Core pipeline: COMPLETE and tested.**
**P1 Contradiction Drill-Down: COMPLETE and tested.**
**P2 Field Consensus Meter + AI Explanation: COMPLETE and tested.**
**Current task: P3 Claim Verification.**
Spec: `FEATURE_claim_verification.md`

Do not refactor working code. Do not rename files.

---

## Non-Negotiables

- Agent framework: Microsoft Agent Framework 1.0 — not LangChain, not CrewAI
- Knowledge base: Azure AI Foundry IQ
- Graph DB: Neo4j — all Cypher queries stay in `graph_manager.py` only
- Backend: FastAPI
- Frontend: D3.js v7
- All secrets via `.env` — never hardcoded, never committed
- No Cypher outside `graph_manager.py`
- No Azure SDK calls outside agent classes and uploaders

---

## Codebase Map

```
src/
├── agents/
│   ├── base_agent.py              # BaseAgent: get_embedding(), cosine_similarity(),
│   │                              #   chat_completion(), parse_json_list()
│   ├── cartographer.py            # A2A orchestrator
│   ├── comparator.py              # Cross-paper edge detection
│   ├── consensus_explainer.py     # ✅ P2: consensus narrative (no args init)
│   ├── claim_verifier.py          # ← P3: NEW FILE
│   ├── extractor.py               # Claim extraction per paper
│   └── gap_finder.py              # Open question discovery via OpenAlex
├── api/
│   ├── routes/
│   │   ├── graph.py               # GET /graph, GET /edge/{id},
│   │   │                          #   GET /claim/{id}/consensus/explain,
│   │   │                          #   GET /verify ← P3 addition
│   │   └── upload.py              # POST /upload
│   ├── limiter.py                 # Rate limiting (slowapi)
│   ├── main.py                    # FastAPI app + lifespan
│   │                              #   app.state.graph_manager
│   │                              #   app.state.cartographer
│   │                              #   app.state.emitter          ← name is "emitter"
│   │                              #   app.state.consensus_explainer
│   │                              #   app.state.claim_verifier   ← P3 addition
│   └── models.py                  # Pydantic models
├── frontend/
│   ├── favicon.svg
│   ├── graph.js                   # D3.js + WebSocket + panel logic (IIFE)
│   ├── index.html                 # Single-page app shell
│   └── styles.css                 # Dark theme, CSS vars, animations
└── graph/
    ├── delta_emitter.py           # WebSocket pub/sub
    ├── graph_manager.py           # Neo4j CRUD — ONLY file with Cypher
    └── schema.py                  # Dataclasses, enums, serializers
```

---

## BaseAgent Methods (Available to All Agents)

```python
await self.get_embedding(text: str) -> list[float]
    # Embeds text using Azure OpenAI (text-embedding-3-small)

self.cosine_similarity(a: list[float], b: list[float]) -> float
    # Synchronous cosine similarity between two embedding vectors
    # Already used by ComparatorAgent._prefilter()

await self.chat_completion(
    user_prompt: str,
    json_mode: bool = True,
    max_tokens: int = 1024,
    temperature: float = 0.3,
) -> str
    # Returns raw LLM response string

self.parse_json_list(raw: str, model: Type[T], list_key: str) -> list[T]
    # Parses a JSON object with a list under list_key, validates each item

await self.query_foundry_iq(query, paper_id, section, top_k) -> list[dict]
    # Queries Foundry IQ knowledge base
```

**Instantiation:** All agents use `AgentClass()` with no arguments.
`from_env()` is inherited but `ConsensusExplainerAgent()` and all new agents
use the no-arg form (verified in main.py line 2353).

---

## API Contract (Current)

```
POST /upload                                → UploadResponse
GET  /graph                                 → GraphResponse
GET  /paper/{paper_id}/status              → PaperStatusResponse
GET  /edge/{edge_id}                       → EdgeDetailResponse
GET  /claim/{claim_id}/consensus/explain   → ConsensusExplainResponse
GET  /verify?statement={text}              → VerificationResponse  ← P3
```

WebSocket `WS /ws/graph` — server pushes, client listens.

---

## Frontend Architecture (graph.js)

Single IIFE. Key objects:

```javascript
state = {
    nodes: Map<id, node>,
    edges: Map<id, edge>,   // D3 mutates source/target to objects post-simulation
    simulation, svg, g, edgeGroup, nodeGroup,
    selectedNodeId, ws, zoom
}

dom = {
    detailPanel,    // #detail-panel
    panelTitle,     // #panel-title
    panelBody,      // #panel-body  ← NOT panelContent
    panelClose,
    searchBtn,      // #search-btn      ← P3 addition
    searchOverlay,  // #search-overlay  ← P3 addition
    searchInput,    // #search-input    ← P3 addition
    statPapers, statClaims, statEdges, statQuestions, ...
}
```

### Functions already in graph.js — do not redefine

```javascript
openDetailPanel(node)         // renders node detail in panel
openEdgeDetailPanel(edge)     // async, fetches /edge/{id}
computeConsensus(claimId)     // returns consensus object from state.edges
explainConsensus(claimId, pct, btn)  // async LLM explanation
getConnections(nodeId)        // returns connected edges from state.edges
closeDetailPanel()
render(animate)               // debounced D3 update
section(title, contentHtml)  // panel section HTML
badge(text, cls)              // badge span HTML
esc(str)                      // HTML-escape — always use for user data
showToast(message, type)
```

### Edge ID resolution (D3 mutates edges after simulation start)

```javascript
const srcId = typeof e.source === "object" ? e.source.id : (e.source_claim_id || e.source);
const tgtId = typeof e.target === "object" ? e.target.id : (e.target_claim_id || e.target);
```

### Edge type field

```javascript
const type = (e.type || e.rel_type || "").toLowerCase();
// values: "supports","contradicts","extends","replicates","refines","contains","relates_to"
```

---

## CSS Design System

```css
--color-paper: #4a9eff
--color-finding: #00ff88       /* green / supports */
--color-method: #ffd700        /* yellow / contested */
--color-contradiction: #ff4444 /* red */
--color-question: #ffffff
--color-concept: #8B5CF6
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

`CONFIG.colors` in JS mirrors these:
```javascript
CONFIG.colors.paper, .finding, .method, .contradiction, .concept, .question,
.supports, .contradicts, .extends, .replicates, .refines
```

---

## graph_manager.py Pattern

```python
async def get_claims_for_verification(self) -> list[dict[str, Any]]:
    query = """
    MATCH (p:Paper)-[:CONTAINS]->(c:Claim)
    WHERE c.embedding IS NOT NULL AND size(c.embedding) > 0
    RETURN c.id AS id, c.text AS text, ...
    """
    async with self._driver.session() as session:
        result = await session.run(query, {})
        return [dict(r) async for r in result]
```

---

## main.py app.state

Note: the WebSocket emitter is stored as `app.state.emitter` (not `delta_emitter`).

```python
app.state.graph_manager        # GraphManager
app.state.cartographer         # CartographerAgent
app.state.emitter              # DeltaEmitter ← name is "emitter"
app.state.consensus_explainer  # ConsensusExplainerAgent()
app.state.claim_verifier       # ClaimVerifierAgent() ← P3
```

---

## Security Rules

- All credentials in `.env` only
- `git diff --cached` before every commit
- `.env` is gitignored — never commit it
- No real values in `.env.example`

---

## Priorities

1. Never break working code
2. Read the FEATURE_*.md spec before touching any file
3. Implement in the file order listed in the spec
4. After completing: delete FEATURE_*.md, tick TODO.md
5. **Deadline: June 14, 2026 11:59 PM PT**
