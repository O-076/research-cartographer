# ARCHITECTURE.md

## System Overview

Research Cartographer is a multi-agent pipeline that turns scientific PDFs into a live knowledge graph. Papers are parsed, chunked, and indexed in Azure AI Foundry IQ. Four agents then run in sequence: one extracts structured claims, one compares them against existing claims, and one identifies research gaps using OpenAlex. A fourth agent (the Cartographer) orchestrates the whole sequence and streams delta events over a WebSocket so the D3.js frontend can update the graph in real time.

Four additional agents handle interactive features triggered by user actions: consensus explanation, claim verification, thread tracing, and literature review generation.

---

## Codebase Layout

```
src/
  agents/
    base_agent.py               # shared Azure OpenAI + Foundry IQ client, retry logic, JSON parsing
    cartographer.py              # pipeline orchestrator (Agent 4)
    extractor.py                 # claim extraction from Foundry IQ chunks (Agent 1)
    comparator.py                # cross-paper edge detection via embedding pre-filter + LLM (Agent 2)
    gap_finder.py                # open question discovery using OpenAlex (Agent 3)
    consensus_explainer.py       # generates qualitative consensus narratives
    claim_verifier.py            # verifies user statements against corpus claims
    thread_tracer.py             # narrates shortest-path reasoning chains
    literature_review_agent.py   # produces APA-format literature reviews
  api/
    main.py                      # FastAPI app, lifespan, agent initialization, static file serving
    models.py                    # all Pydantic request/response models
    limiter.py                   # slowapi rate limiter config
    routes/
      upload.py                  # POST /upload
      graph.py                   # all GET/POST/WS endpoints
  frontend/
    index.html                   # single-page app shell
    graph.js                     # D3.js IIFE (all client logic)
    styles.css                   # dark theme with CSS custom properties
  graph/
    schema.py                    # dataclasses (Paper, Claim, Edge, Concept, OpenQuestion), Neo4j DDL
    graph_manager.py             # sole file containing Cypher queries
    delta_emitter.py             # WebSocket pub/sub for graph change events
  ingestion/
    pdf_parser.py                # PyMuPDF + pdfplumber, section detection, token-based chunking
    foundry_uploader.py          # uploads PaperChunk list to Foundry IQ knowledge base
```

---

## Ingestion Layer

### pdf_parser.py

Parses PDF bytes into a list of `PaperChunk` objects. Uses PyMuPDF (`fitz`) as the primary text extractor. Falls back to pdfplumber when PyMuPDF yields fewer than 100 characters (common with scanned or multi-column layouts).

Text is split into sections using regex matching against common academic headings (Abstract, Introduction, Methods, Results, Discussion). Sections are then chunked by whitespace tokens with configurable size (default 500 tokens, 50-token overlap).

```python
@dataclass(frozen=True, slots=True)
class PaperChunk:
    paper_id: str
    chunk_index: int
    text: str
    section: str       # abstract | intro | methods | results | discussion | other | unknown
    token_count: int
    page_numbers: list[int]
```

### foundry_uploader.py

Takes a list of `PaperChunk` objects and uploads them as documents to the Foundry IQ knowledge base. Each document is tagged with `paper_id` and `section` metadata so agents can filter their queries (e.g., "all results-section chunks from paper X"). Waits for Foundry IQ indexing to complete before returning.

---

## Agent Layer

All agents inherit from `BaseAgent` (`base_agent.py`), which provides:

- `chat_completion()` - Azure OpenAI chat with retry/backoff. Adapts automatically for o-series reasoning models (uses `developer` role, drops `temperature`, swaps `max_tokens` for `max_completion_tokens`).
- `get_embedding()` / `get_embeddings_batch()` - Azure OpenAI embeddings via `text-embedding-3-small`.
- `query_foundry_iq()` - Foundry IQ knowledge base query with optional paper_id/section filters.
- `parse_json_response()` / `parse_json_list()` - strips markdown fences, parses JSON, validates against Pydantic models.
- `cosine_similarity()` - numpy-free dot-product implementation.

HTTP calls use `httpx.AsyncClient` with `tenacity` retry (3 attempts, exponential backoff 1-16s).

### Pipeline Agents (run automatically per upload)

**Cartographer (`cartographer.py`)**
Orchestrates the pipeline as a single async method `process_paper()`. Steps:

1. Create Paper node in Neo4j
2. Parse PDF into chunks
3. Extract metadata (title, authors, year, abstract) from the first few chunks via LLM
4. Upload chunks to Foundry IQ
5. Run Extractor
6. Run Comparator against all existing claims
7. Run Gap Finder against the full claim set
8. Mark pipeline complete

Tracks per-paper state through: `QUEUED -> EXTRACTING -> CLAIMS_READY -> COMPARING -> EDGES_READY -> GAP_FINDING -> COMPLETE` (or `ERROR`). Each transition emits a `paper_status` WebSocket event and updates the Neo4j Paper node.

Sub-agents are lazily instantiated and reused across papers.

**Extractor (`extractor.py`)**
Queries Foundry IQ for each section type (results, methods, discussion, intro, abstract), sends the retrieved chunks to the LLM with a structured extraction prompt, and yields `Claim` + `Concept` objects. Each claim gets an embedding. Claims with >0.95 cosine similarity to an existing claim from the same paper are skipped (deduplication of overlapping chunks).

**Comparator (`comparator.py`)**
Compares new claims against all existing claims from other papers. Uses a cosine similarity pre-filter (threshold 0.60) to avoid sending every pair to the LLM. Candidate pairs are classified into: `supports`, `contradicts`, `extends`, `replicates`, `refines`, or `none`. Edges are written to Neo4j with a strength score and reasoning text.

**Gap Finder (`gap_finder.py`)**
Takes all claims in the graph, prompts the LLM to identify open research questions, then scores novelty by querying the OpenAlex API. Questions with high novelty scores are written as `OpenQuestion` nodes linked to their related claims.

### Interactive Agents (triggered by user actions)

**Consensus Explainer (`consensus_explainer.py`)**
Called by `GET /claim/{id}/consensus/explain`. Receives a claim, its connected edges, and a pre-computed consensus percentage. Produces a 2-3 sentence narrative explaining the field's agreement or disagreement on that claim.

**Claim Verifier (`claim_verifier.py`)**
Called by `GET /verify?statement=...`. Embeds the user's statement, retrieves the top 15 most similar claims by cosine similarity (threshold 0.40), then sends a single batched LLM call to classify each as `supports`, `contradicts`, or `neutral`.

**Thread Tracer (`thread_tracer.py`)**
Called by `GET /trace?from_id=...&to_id=...`. Receives the shortest path between two nodes (computed by `graph_manager.get_path_between()` using Cypher `shortestPath`, max 6 hops). Generates a 3-5 sentence narrative explaining the conceptual chain.

**Literature Review Agent (`literature_review_agent.py`)**
Called by `POST /generate/review`. Queries Neo4j for all papers, concept clusters, contradictions, and open questions via `graph_manager.get_review_data()`. Formats APA citations in Python, then sends a single LLM call to produce a structured review (title, abstract, thematic sections, references). The result can be downloaded as a `.docx` file via `POST /generate/review/docx`.

---

## Graph Layer

### schema.py

Defines all graph types as frozen dataclasses:

| Node type      | Key fields                                          |
|----------------|-----------------------------------------------------|
| `Paper`        | id, title, authors, year, abstract, status          |
| `Claim`        | id, paper_id, text, type, confidence, embedding     |
| `Concept`      | id, name, embedding                                 |
| `OpenQuestion` | id, question, novelty_score, related_claim_ids      |

| Edge type    | Between         |
|--------------|-----------------|
| `SUPPORTS`   | Claim -> Claim  |
| `CONTRADICTS`| Claim -> Claim  |
| `EXTENDS`    | Claim -> Claim  |
| `REPLICATES` | Claim -> Claim  |
| `REFINES`    | Claim -> Claim  |
| `CONTAINS`   | Paper -> Claim  |
| `RELATES_TO` | Claim -> Concept|
| `GAPS`       | OpenQuestion -> Claim |

Also defines `*_to_props()` serialization helpers for converting dataclasses to Neo4j property maps, and `ALL_NEO4J_DDL` (uniqueness constraints + indexes).

### graph_manager.py

The only file with Cypher. Provides async methods for all graph reads and writes through `neo4j.AsyncDriver`. Key operations:

- `add_paper()`, `add_claim()`, `add_edge()`, `add_concept()`, `upsert_question()`
- `get_full_graph()` - full snapshot for initial frontend load
- `get_edge_with_claims()` - edge detail with both claims and their parent papers
- `get_claim_consensus_context()` - claim plus all its semantic edges
- `get_path_between()` - Cypher `shortestPath` up to 6 hops
- `get_review_data()` - papers, concept clusters, contradictions, open questions for the literature review agent
- `update_paper_metadata()` - sets title, authors, year, abstract after LLM extraction
- `clear_all()` - wipes the database

Connects via `GraphManager.from_env()` using `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`.

### delta_emitter.py

Process-level pub/sub. WebSocket connections register via `subscribe()`. When any agent writes to Neo4j, it also calls the appropriate `emit_*()` method, which JSON-serializes a `GraphDelta` (type, data, timestamp) and sends it to every subscriber. Dead connections are removed after each emit cycle. Protected by `asyncio.Lock`.

Event types: `node_added`, `edge_added`, `edge_updated`, `question_added`, `question_resolved`, `paper_status`.

---

## API Layer

FastAPI app defined in `main.py`. Uses `@asynccontextmanager` lifespan to initialize all dependencies at startup:

1. Load `.env` from project root
2. Create `GraphManager`, run Neo4j schema DDL
3. Create `DeltaEmitter`
4. Create `CartographerAgent` (with graph_manager + emitter)
5. Create interactive agents (`ConsensusExplainerAgent`, `ClaimVerifierAgent`, `ThreadTracerAgent`, `LiteratureReviewAgent`)

All agents are stored on `app.state` and accessed by route handlers via `request.app.state.*`.

### Endpoints

| Method | Path                              | Response model             |
|--------|-----------------------------------|----------------------------|
| POST   | `/upload`                         | `UploadResponse`           |
| GET    | `/graph`                          | `GraphResponse`            |
| GET    | `/paper/{paper_id}/status`        | `PaperStatusResponse`      |
| GET    | `/edge/{edge_id}`                 | `EdgeDetailResponse`       |
| GET    | `/claim/{claim_id}/consensus/explain` | `ConsensusExplainResponse` |
| GET    | `/verify?statement={text}`        | `VerificationResponse`     |
| GET    | `/trace?from_id={id}&to_id={id}`  | `TraceResponse`            |
| POST   | `/generate/review`                | `LiteratureReviewResponse` |
| POST   | `/generate/review/docx`           | `.docx` binary             |
| WS     | `/ws/graph`                       | delta event stream         |

The upload endpoint reads PDF bytes, creates a Paper node, then launches `cartographer.process_paper()` as a detached `asyncio.Task` so the client gets an immediate response.

Pipeline progress is mapped to percentages in `models.py`:
```
queued: 0% -> extracting: 15% -> claims_ready: 35% -> comparing: 50%
-> edges_ready: 70% -> gap_finding: 85% -> complete: 100%
```

---

## Frontend

Three static files served by FastAPI from `src/frontend/`.

### graph.js

Single IIFE. Manages the full client: D3.js force simulation, SVG rendering, WebSocket connection with auto-reconnect, drag, zoom, tooltips, and all interactive panels.

Key design decisions:
- Nodes and edges stored in `Map` objects keyed by ID for O(1) lookups
- `render()` is debounced (50ms) to batch rapid delta events
- After every data update: `simulation.alpha(0.3).restart()` (not 1.0, to avoid jarring jumps)
- Edge IDs resolved carefully because D3 mutates `source`/`target` from strings to objects after simulation starts
- `CONTAINS` and `RELATES_TO` edges are excluded from consensus calculations (they are structural, not semantic)

Interactive features in graph.js:
- Click a node to open the detail panel (shows claim text, paper info, source chunk, consensus meter)
- Click an edge to see both claims side-by-side with the comparator's reasoning
- Press `/` to open the search overlay (claim verification)
- Shift-click two nodes to trace the shortest path between them
- "Generate Review" button in the header to produce a literature review

### styles.css

Dark theme built on CSS custom properties. Key color mappings:
```
Paper:         #4a9eff (blue)
Finding:       #00ff88 (green)
Method:        #ffd700 (gold)
Contradiction: #EF4444 (red)
Concept:       #8B5CF6 (purple)
OpenQuestion:  #F3F4F6 (light gray)
```

---

## Environment Variables

All values in `.env` (gitignored). See `.env.example` for the full list.

Required:
- `AZURE_FOUNDRY_IQ_ENDPOINT`, `AZURE_FOUNDRY_IQ_KEY`, `AZURE_FOUNDRY_IQ_KB_ID`
- `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`
- `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`

Optional:
- `APP_HOST` (default `0.0.0.0`), `APP_PORT` (default `8000`), `LOG_LEVEL` (default `INFO`)
- `EMBEDDING_SIMILARITY_THRESHOLD` (default `0.60`), `CLAIM_DEDUP_THRESHOLD` (default `0.95`)
