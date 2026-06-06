# 🤖 AGENTS.md — Instructions for AI Coding Agents

> This file is the primary seed for AI coding agents (Claude Code, GitHub Copilot, Codex, Cursor, etc.).
> Read this file fully before writing a single line of code. It contains all decisions already made — do not revisit them.

---

## 🧭 What This Project Is

**Research Cartographer** is a multi-agent system submitted to the Microsoft Agents League Hackathon 2026 (Reasoning Agents track). It ingests scientific PDFs, reasons across them using 4 coordinated AI agents, and produces a live D3.js force-directed knowledge graph streamed via WebSocket.

**Deadline:** June 14, 2026 · 11:59 PM PT — velocity matters.

---

## 🚫 Non-Negotiables (Do Not Change These)

These decisions are final. Do not suggest alternatives.

- **Agent framework:** Microsoft Agent Framework 1.0 — not LangChain, not CrewAI
- **Agent coordination:** A2A Protocol — not custom message passing
- **Knowledge base:** Azure AI Foundry IQ — not a custom vector store
- **Web grounding:** Semantic Scholar API — not Web IQ (limited access)
- **Graph DB:** Neo4j — not a plain dict or NetworkX (though NetworkX may be used for local testing)
- **Backend:** FastAPI — not Flask, not Django
- **Frontend graph:** D3.js v7 force-directed — not Cytoscape.js, not vis.js
- **PDF parsing:** PyMuPDF (fitz) primary, pdfplumber fallback for complex layouts
- **Embeddings:** `text-embedding-3-large` via Azure OpenAI — not ada-002
- **All secrets via .env** — never hardcoded, never committed

---

## 📁 Codebase Map

Build files in this exact structure. Do not invent new top-level directories.

```
src/
├── agents/
│   ├── extractor.py       # Agent 1: claim extraction per paper
│   ├── comparator.py      # Agent 2: cross-paper edge detection
│   ├── gap_finder.py      # Agent 3: open question discovery
│   ├── cartographer.py    # Agent 4: A2A orchestrator
│   └── base_agent.py      # Shared base class for all agents
├── ingestion/
│   ├── pdf_parser.py      # PDF → structured chunks
│   └── foundry_uploader.py # Chunks → Foundry IQ knowledge base
├── graph/
│   ├── graph_manager.py   # Neo4j CRUD + query interface
│   ├── schema.py          # Node/edge type definitions
│   └── delta_emitter.py   # Emits graph change events for WebSocket
├── api/
│   ├── main.py            # FastAPI app entry point
│   ├── routes/
│   │   ├── upload.py      # POST /upload
│   │   └── graph.py       # GET /graph, WS /ws/graph
│   └── models.py          # Pydantic request/response models
└── frontend/
    ├── index.html         # Single-page app shell
    ├── graph.js           # D3.js force graph + WebSocket client
    └── styles.css         # Tailwind + custom graph styling
```

---

## 🧠 Agent Definitions

### Agent 1 — Extractor (`src/agents/extractor.py`)

**Purpose:** Given a paper's chunks from Foundry IQ, extract structured claims.

**Input:** `paper_id: str`, chunks fetched from Foundry IQ
**Output:** List of `Claim` objects written to Neo4j

```python
# Claim schema
{
    "id": "uuid",
    "paper_id": "str",
    "text": "str",              # The claim in plain language
    "type": "finding|method|assumption|limitation",
    "confidence": 0.0–1.0,
    "section": "abstract|intro|methods|results|discussion",
    "embedding": [float]        # text-embedding-3-large vector
}
```

**System prompt direction:** Extract factual, falsifiable claims only. Ignore background summaries. Each claim must be standalone and self-contained. Output strict JSON array.

---

### Agent 2 — Comparator (`src/agents/comparator.py`)

**Purpose:** Given any two claims, determine their relationship and write a typed edge.

**Trigger:** Fires after every new paper is ingested. Re-evaluates ALL edges involving new claims.
**Input:** Pairs of `Claim` objects from Neo4j
**Output:** `Edge` objects written to Neo4j

```python
# Edge schema
{
    "id": "uuid",
    "source_claim_id": "str",
    "target_claim_id": "str",
    "type": "supports|contradicts|extends|replicates|refines",
    "strength": 0.0–1.0,        # Semantic similarity + LLM confidence
    "reasoning": "str",          # Why this relationship exists
    "created_at": "datetime"
}
```

**Key behavior:** When a new paper is added, existing edges are NOT deleted — they are re-scored. The graph is additive.

---

### Agent 3 — Gap Finder (`src/agents/gap_finder.py`)

**Purpose:** Look across all claims in the graph and identify questions the corpus doesn't answer. Cross-reference with Semantic Scholar to score novelty.

**Trigger:** Runs after Comparator finishes. Re-runs on every new paper.
**Input:** Full claim graph from Neo4j + Semantic Scholar API search
**Output:** `OpenQuestion` nodes written to Neo4j

```python
# OpenQuestion schema
{
    "id": "uuid",
    "question": "str",
    "novelty_score": 0.0–1.0,   # How unexplored this is (Semantic Scholar informed)
    "related_claim_ids": ["str"],
    "web_evidence": "str",       # What Semantic Scholar found (or didn't find)
    "status": "open|partially_answered|resolved"
}
```

**Visual representation:** OpenQuestion nodes render as glowing white nodes on the graph ("white space").

---

### Agent 4 — Cartographer (`src/agents/cartographer.py`)

**Purpose:** A2A orchestrator. Coordinates the other three agents, maintains pipeline state, decides when re-analysis is needed.

**Responsibilities:**
- Receive upload events from FastAPI
- Dispatch Extractor → await completion → dispatch Comparator → await completion → dispatch Gap Finder
- Emit graph delta events at each stage via `delta_emitter.py`
- Track pipeline state per paper (queued / extracting / comparing / gap_finding / complete)
- Handle failures gracefully — partial results are still pushed to graph

**State machine per paper:**
```
QUEUED → EXTRACTING → CLAIMS_READY → COMPARING → EDGES_READY → GAP_FINDING → COMPLETE
                                                                               ↕
                                                                           ERROR
```

---

## 🔌 API Contract

### REST Endpoints

```
POST /upload
  Body: multipart/form-data { file: PDF }
  Response: { paper_id: str, status: "queued" }

GET /graph
  Response: { nodes: [...], edges: [...], questions: [...] }

GET /paper/{paper_id}/status
  Response: { paper_id, status, progress_pct }
```

### WebSocket

```
WS /ws/graph
  Server → Client messages (JSON):
  
  { "type": "node_added",    "data": { node } }
  { "type": "edge_added",    "data": { edge } }
  { "type": "edge_updated",  "data": { edge } }
  { "type": "question_added","data": { question } }
  { "type": "question_resolved", "data": { question_id } }
  { "type": "paper_status",  "data": { paper_id, status } }
```

The frontend ONLY uses WebSocket deltas after initial load. Never re-fetch the full graph.

---

## 🗄️ Neo4j Graph Schema

### Node Labels
- `:Paper` — `{id, title, authors, year, abstract}`
- `:Claim` — `{id, paper_id, text, type, confidence, section}`
- `:Concept` — `{id, name, embedding}` — auto-extracted shared themes
- `:OpenQuestion` — `{id, question, novelty_score, status}`

### Relationship Types
- `(:Claim)-[:SUPPORTS]→(:Claim)`
- `(:Claim)-[:CONTRADICTS]→(:Claim)`
- `(:Claim)-[:EXTENDS]→(:Claim)`
- `(:Claim)-[:REPLICATES]→(:Claim)`
- `(:Claim)-[:REFINES]→(:Claim)`
- `(:Paper)-[:CONTAINS]→(:Claim)`
- `(:Claim)-[:RELATES_TO]→(:Concept)`
- `(:OpenQuestion)-[:GAPS]→(:Claim)`

---

## 🌊 Async Pipeline (Critical — Read This)

The async behavior is the #1 visual differentiator. Implement it correctly.

```python
# Pseudocode for the async flow
async def process_paper(paper_id: str):
    # Stage 1: Extraction (emit node events as claims are found)
    async for claim in extractor.run(paper_id):
        await graph_manager.add_claim(claim)
        await delta_emitter.emit("node_added", claim)

    # Stage 2: Comparison (emit edge events as relationships are found)
    async for edge in comparator.run(paper_id):
        await graph_manager.add_or_update_edge(edge)
        event = "edge_updated" if edge.existed else "edge_added"
        await delta_emitter.emit(event, edge)

    # Stage 3: Gap Finding (emit question events)
    async for question in gap_finder.run():
        await graph_manager.upsert_question(question)
        await delta_emitter.emit("question_added", question)
```

Use `asyncio.Queue` for the pipeline. Do not use threading.

---

## 🎨 Frontend Behavior (D3.js)

- **Node size:** proportional to number of connections
- **Node color:**
  - Blue = Paper nodes
  - Green = Claim nodes (finding/result)
  - Yellow = Claim nodes (method/assumption)
  - Red = Claims involved in contradictions
  - White/Glowing = OpenQuestion nodes
  - Purple = Concept nodes
- **Edge color:**
  - Green = supports
  - Red = contradicts
  - Blue = extends
  - Grey = replicates/refines
- **Edge thickness:** proportional to `strength` score
- **Click behavior:** clicking any node opens a side panel with full details + agent reasoning
- **New nodes/edges:** animate in with a brief glow effect (CSS transition)
- **Contradiction clusters:** nodes with many red edges get a pulsing red halo

---

## 🧪 Testing Strategy

- Unit test each agent with 2–3 mock papers (include test PDFs in `tests/fixtures/`)
- Test WebSocket delta stream with a mock pipeline
- Test Neo4j queries with an in-memory Neo4j or mocked driver
- Do NOT write tests before the feature exists — test as you build

---

## 🔐 Security Rules (Enforced)

See [SECURITY.md](SECURITY.md) for full details. Summary:

- All credentials in `.env` only — never in code, never in comments
- `.env` is gitignored — use `.env.example` with placeholder values
- No PII, no customer data, no internal Microsoft info
- Run `git diff --cached` before every commit to check for secrets
- If you accidentally stage a secret: `git reset HEAD <file>` immediately

---

## 📋 Environment Variables Required

See `.env.example` for the full list. Key ones:

```
AZURE_FOUNDRY_IQ_ENDPOINT=
AZURE_FOUNDRY_IQ_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_KEY=
NEO4J_URI=
NEO4J_USERNAME=
NEO4J_PASSWORD=
```

---

## ⚡ Priorities for AI Agents

When choosing what to build next, follow this priority order:

1. **Working pipeline first** — PDF in, claims in Neo4j, even if ugly
2. **WebSocket streaming second** — the live graph is the demo
3. **D3.js visualization third** — the wow factor
4. **Gap Finder last** — most complex, least critical for MVP

If time is short, a working Extractor + Comparator + live D3 graph is a complete, submittable demo.

---

## 🔗 Key References

- [Microsoft Agent Framework 1.0 Docs](https://aka.ms/agentframework)
- [A2A Protocol Spec](https://aka.ms/a2a)
- [Foundry IQ Docs](https://learn.microsoft.com/azure/foundry/agents/concepts/what-is-foundry-iq)
- [Web IQ Docs](https://learn.microsoft.com/azure/foundry/agents/concepts/what-is-web-iq)
- [IQ Series Learning](https://aka.ms/iq-series)
- [Hackathon Discord](https://aka.ms/agentsleague/discord)
