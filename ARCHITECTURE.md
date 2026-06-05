# 🏗️ ARCHITECTURE.md — Technical Specification

## System Overview

Research Cartographer is a **pipeline-based multi-agent system** with async event streaming. The core idea: every component emits events, nothing blocks, and the frontend reflects the system's live state.

---

## Component Breakdown

### 1. Ingestion Layer

**`src/ingestion/pdf_parser.py`**

Uses PyMuPDF (`fitz`) as the primary parser. Falls back to pdfplumber for PDFs with complex layouts (tables, multi-column).

```
PDF bytes
  └→ fitz.open()
       └→ extract text per page
            └→ heuristic section detection (regex on headers)
                 └→ chunk by token count (500 tokens, 50 token overlap)
                      └→ List[PaperChunk]
```

`PaperChunk` schema:
```python
@dataclass
class PaperChunk:
    paper_id: str
    chunk_index: int
    text: str
    section: str  # abstract|intro|methods|results|discussion|other
    token_count: int
    page_numbers: list[int]
```

**`src/ingestion/foundry_uploader.py`**

Uploads chunks to Foundry IQ. Each chunk is a document in the knowledge base with metadata for filtering.

Key design: chunks are tagged with `paper_id` and `section` so agents can query "all results-section chunks from paper X" or "all methods sections across all papers."

---

### 2. Agent Layer

All agents inherit from `BaseAgent` in `src/agents/base_agent.py`.

`BaseAgent` provides:
- Foundry IQ query wrapper with retry + exponential backoff
- Azure OpenAI client (shared, rate-limited)
- Structured JSON output parser with validation
- Agent-level logging with paper_id correlation

#### Extractor Agent

**Core loop:**
```
for each chunk in paper:
    query Foundry IQ with chunk context
    prompt: "Extract all falsifiable claims from this text. JSON only."
    parse response → List[Claim]
    write to Neo4j
    emit "node_added" event
```

**Prompt strategy:** Zero-shot with strict JSON schema in the prompt. Output format enforced via Azure OpenAI `response_format={"type": "json_object"}`.

**Claim deduplication:** Before writing, check embedding similarity against existing claims from the same paper. Skip if cosine similarity > 0.95 (likely duplicate from overlapping chunks).

#### Comparator Agent

**Pre-filter strategy (critical for cost):**

Comparing every claim pair is O(n²). With 10 papers × ~20 claims = 200 claims → 19,900 pairs. We can't LLM-compare all of them.

Solution: **embedding pre-filter**
```
for each new claim C:
    fetch embeddings of all existing claims
    compute cosine similarity
    candidates = claims where similarity > 0.60
    for each candidate:
        LLM-compare C vs candidate
        if relationship found: write edge
```

This reduces LLM calls by ~80%.

**Edge conflict resolution:** If a new paper creates an edge that contradicts an existing edge (e.g., was "supports", now becomes "contradicts"), keep both with timestamps. Show evolution on click.

#### Gap Finder Agent

**Algorithm:**
```
1. Fetch all Concept nodes from Neo4j
2. For each concept pair (C1, C2) with no bridging claims:
   a. Generate a potential research question: "What is the relationship between C1 and C2?"
   b. Query Web IQ: "research on [C1] AND [C2]"
   c. If Web IQ finds <3 relevant papers: novelty_score += 0.3
   d. If no direct papers found: novelty_score = 0.9+
3. Write OpenQuestion nodes for gaps with novelty_score > 0.5
```

**Concept extraction:** Concepts are extracted as a side-effect of the Extractor agent. Named entities, domain terms, and methodology names are tagged as `:Concept` nodes.

#### Cartographer Orchestrator

Uses **Microsoft Agent Framework 1.0 A2A protocol** for agent dispatch.

```python
# A2A dispatch pseudocode
async def orchestrate(paper_id: str):
    await self.dispatch_agent(
        agent_id="extractor",
        task={"paper_id": paper_id},
        on_complete=self.after_extraction
    )

async def after_extraction(paper_id: str):
    await self.dispatch_agent(
        agent_id="comparator",
        task={"new_paper_id": paper_id},
        on_complete=self.after_comparison
    )

async def after_comparison(paper_id: str):
    await self.dispatch_agent(
        agent_id="gap_finder",
        task={},  # gap finder always re-runs on full graph
        on_complete=self.pipeline_complete
    )
```

---

### 3. Graph Layer

**Neo4j AuraDB** — cloud-managed, free tier sufficient for hackathon scale.

**`src/graph/schema.py`** defines all node/relationship types as Python dataclasses + Neo4j constraint scripts.

**`src/graph/graph_manager.py`** is the single interface to Neo4j. Never write Cypher outside this file.

Key queries:
```cypher
// Get all claims similar to a given claim (for Comparator pre-filter)
MATCH (c:Claim) WHERE c.paper_id <> $paper_id
RETURN c, gds.similarity.cosine(c.embedding, $embedding) AS score
ORDER BY score DESC LIMIT 50

// Get full graph for initial frontend load
MATCH (n) OPTIONAL MATCH (n)-[r]->(m)
RETURN n, r, m

// Get contradiction clusters
MATCH (c1:Claim)-[r:CONTRADICTS]-(c2:Claim)
RETURN c1, r, c2, count(r) as tension_score
ORDER BY tension_score DESC
```

**`src/graph/delta_emitter.py`**

Pub/sub within the FastAPI process. WebSocket connections subscribe to the emitter. When an agent writes to Neo4j, it also calls `delta_emitter.emit(event_type, data)`, which pushes to all connected WebSocket clients.

```python
class DeltaEmitter:
    def __init__(self):
        self.subscribers: list[WebSocket] = []

    async def subscribe(self, ws: WebSocket):
        self.subscribers.append(ws)

    async def emit(self, event_type: str, data: dict):
        message = json.dumps({"type": event_type, "data": data})
        dead = []
        for ws in self.subscribers:
            try:
                await ws.send_text(message)
            except:
                dead.append(ws)
        for ws in dead:
            self.subscribers.remove(ws)
```

---

### 4. API Layer

FastAPI with three main concerns:
- File upload → pipeline trigger
- Full graph snapshot (initial load)
- WebSocket for live deltas

The FastAPI app and the agent pipeline share the same process. The pipeline runs as asyncio tasks — not separate processes, not threads.

```python
# main.py structure
app = FastAPI()
delta_emitter = DeltaEmitter()  # singleton
cartographer = CartographerAgent(delta_emitter)

@app.post("/upload")
async def upload(file: UploadFile):
    paper_id = generate_id()
    asyncio.create_task(cartographer.process_paper(paper_id, await file.read()))
    return {"paper_id": paper_id, "status": "queued"}

@app.websocket("/ws/graph")
async def websocket_graph(ws: WebSocket):
    await ws.accept()
    await delta_emitter.subscribe(ws)
    await ws.wait()  # keep connection open
```

---

### 5. Frontend

Single HTML file with embedded D3.js. No build step, no npm. Served as static file by FastAPI.

**D3.js force simulation config:**
```javascript
const simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id(d => d.id).distance(80))
    .force("charge", d3.forceManyBody().strength(-300))
    .force("collision", d3.forceCollide().radius(d => nodeRadius(d) + 5))
    .force("center", d3.forceCenter(width / 2, height / 2));
```

**WebSocket delta handler:**
```javascript
ws.onmessage = (event) => {
    const { type, data } = JSON.parse(event.data);
    switch(type) {
        case "node_added":   addNode(data);    break;
        case "edge_added":   addEdge(data);    break;
        case "edge_updated": updateEdge(data); break;
        case "question_added": addQuestion(data); break;
    }
    simulation.alpha(0.3).restart(); // re-energize simulation
};
```

**Critical:** After every delta update, call `simulation.alpha(0.3).restart()` to smoothly re-layout the graph. Do not call `.restart()` with alpha=1 — it will cause a jarring jump.

---

## Data Flow Summary

```
[User] → uploads PDF
  → [FastAPI /upload]
    → [Cartographer] dispatches via A2A
      → [Extractor] reads Foundry IQ, writes Claims to Neo4j
        → emits "node_added" events
      → [Comparator] queries Neo4j, writes Edges to Neo4j
        → emits "edge_added"/"edge_updated" events
      → [Gap Finder] queries Neo4j + Web IQ, writes OpenQuestions
        → emits "question_added"/"question_resolved" events
  → [DeltaEmitter] pushes events to all WebSocket connections
    → [Frontend D3.js] adds/updates nodes/edges with animations
```

---

## Environment Variables

```bash
# Azure AI / Foundry IQ
AZURE_FOUNDRY_IQ_ENDPOINT=         # e.g. https://xxx.services.ai.azure.com
AZURE_FOUNDRY_IQ_KEY=              # Foundry IQ API key
AZURE_FOUNDRY_IQ_KB_ID=            # Knowledge base ID

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=             # e.g. https://xxx.openai.azure.com
AZURE_OPENAI_KEY=                  # Azure OpenAI API key
AZURE_OPENAI_DEPLOYMENT=           # Deployment name (e.g. gpt-4o)
AZURE_OPENAI_EMBEDDING_DEPLOYMENT= # e.g. text-embedding-3-large

# Web IQ
AZURE_WEB_IQ_ENDPOINT=
AZURE_WEB_IQ_KEY=

# Neo4j
NEO4J_URI=                         # e.g. neo4j+s://xxx.databases.neo4j.io
NEO4J_USERNAME=                    # usually "neo4j"
NEO4J_PASSWORD=                    # AuraDB generated password

# App
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO
```

All values go in `.env` only. `.env` is gitignored. `.env.example` has these keys with empty values.
