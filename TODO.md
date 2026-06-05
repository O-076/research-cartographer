# ✅ TODO.md — Task Breakdown

> Status legend: ⬜ Not started · 🔄 In progress · ✅ Done · ⏭️ Skipped

---

## Day 1 — Foundation

### Repo & Environment
- ⬜ Initialize git repo and push to GitHub (public)
- ⬜ Add all .md seed files (README, AGENTS, PLAN, TODO, ARCHITECTURE, CHALLENGES, CONTEXT, SECURITY, CONVENTIONS)
- ⬜ Create `.gitignore` (Python, .env, Neo4j, IDE files)
- ⬜ Create `.env.example` with all required variable names (no values)
- ⬜ Create `requirements.txt` with pinned versions
- ⬜ Create `src/` directory structure (empty `__init__.py` files)

### Azure Setup
- ⬜ Create Azure resource group for the project
- ⬜ Provision Azure AI Foundry workspace
- ⬜ Create Foundry IQ knowledge base (empty)
- ⬜ Obtain Azure OpenAI endpoint + key → `.env` only
- ⬜ Verify `text-embedding-3-large` model is available

### Neo4j Setup
- ⬜ Create Neo4j AuraDB free tier instance
- ⬜ Store connection URI + credentials in `.env` only
- ⬜ Test connection with a simple Python script (not committed)

### PDF Ingestion
- ⬜ Build `src/ingestion/pdf_parser.py`
  - ⬜ Extract text per section (abstract, intro, methods, results, discussion)
  - ⬜ Split into chunks (~500 tokens with overlap)
  - ⬜ Return structured `PaperChunk` objects
- ⬜ Build `src/ingestion/foundry_uploader.py`
  - ⬜ Upload chunks to Foundry IQ knowledge base
  - ⬜ Tag chunks with paper_id and section metadata
- ⬜ Test with 1 real PDF — verify chunks appear in Foundry IQ

---

## Day 2 — Extractor Agent

- ⬜ Build `src/agents/base_agent.py` — shared base class
  - ⬜ Logging, error handling, retry logic
  - ⬜ Foundry IQ query wrapper
- ⬜ Build `src/agents/extractor.py`
  - ⬜ System prompt for claim extraction (strict JSON output)
  - ⬜ Iterate over paper chunks from Foundry IQ
  - ⬜ Parse and validate claim objects
  - ⬜ Assign claim types: finding / method / assumption / limitation
- ⬜ Build `src/graph/schema.py`
  - ⬜ Define `Claim`, `Paper`, `Concept`, `OpenQuestion`, `Edge` dataclasses
  - ⬜ Neo4j constraint definitions
- ⬜ Build `src/graph/graph_manager.py` (partial)
  - ⬜ `add_paper(paper)`
  - ⬜ `add_claim(claim)`
  - ⬜ `get_claims_for_paper(paper_id)`
- ⬜ Test: run Extractor on 3 papers, verify claims in Neo4j

---

## Day 3 — Comparator Agent

- ⬜ Build `src/agents/comparator.py`
  - ⬜ Fetch all claim pairs to compare (new paper's claims vs. all existing)
  - ⬜ System prompt for relationship classification (supports/contradicts/extends/replicates/refines)
  - ⬜ Batch processing — don't compare every pair naively (use embedding similarity pre-filter)
  - ⬜ Write typed edges with reasoning and strength score
- ⬜ Extend `src/graph/graph_manager.py`
  - ⬜ `add_edge(edge)`
  - ⬜ `update_edge(edge)` — for re-scoring
  - ⬜ `get_all_claims()`
  - ⬜ `get_edges_for_claim(claim_id)`
- ⬜ Build embedding pre-filter (cosine similarity threshold before LLM comparison)
  - ⬜ Only send claim pairs with similarity > 0.6 to the LLM
  - ⬜ This dramatically reduces API calls
- ⬜ Test: upload 2 papers that are known to agree/disagree — verify edges

---

## Day 4 — Cartographer Orchestrator + A2A

- ⬜ Build `src/agents/cartographer.py`
  - ⬜ Implement A2A protocol setup (Microsoft Agent Framework 1.0)
  - ⬜ Define pipeline state machine per paper
  - ⬜ Dispatch Extractor → await → dispatch Comparator → await → dispatch Gap Finder
  - ⬜ Handle partial failures — log and continue
  - ⬜ Track pipeline status: QUEUED → EXTRACTING → COMPARING → GAP_FINDING → COMPLETE
- ⬜ Build `src/graph/delta_emitter.py`
  - ⬜ Event queue for graph changes
  - ⬜ `emit(event_type, data)` method
  - ⬜ Subscriber pattern for WebSocket connections
- ⬜ Integration test: full pipeline on 3 papers without UI

---

## Day 5 — FastAPI Backend + WebSocket

- ⬜ Build `src/api/models.py`
  - ⬜ Pydantic models for all request/response shapes
  - ⬜ WebSocket message schemas
- ⬜ Build `src/api/routes/upload.py`
  - ⬜ `POST /upload` — receive PDF, trigger Cartographer pipeline
  - ⬜ Return `{ paper_id, status: "queued" }`
- ⬜ Build `src/api/routes/graph.py`
  - ⬜ `GET /graph` — return full graph snapshot for initial load
  - ⬜ `GET /paper/{paper_id}/status` — pipeline progress
  - ⬜ `WS /ws/graph` — stream delta events to frontend
- ⬜ Build `src/api/main.py`
  - ⬜ Mount all routes
  - ⬜ CORS config
  - ⬜ Serve `src/frontend/` as static files
- ⬜ Test WebSocket with `wscat` — verify events stream correctly

---

## Day 6 — D3.js Frontend

- ⬜ Build `src/frontend/index.html`
  - ⬜ App shell: graph canvas + sidebar + upload button
  - ⬜ Upload drag-and-drop zone
  - ⬜ Paper pipeline status indicator
- ⬜ Build `src/frontend/graph.js`
  - ⬜ Initial graph load from `GET /graph`
  - ⬜ D3.js v7 force-directed simulation
  - ⬜ Node rendering with color-coding by type
  - ⬜ Edge rendering with color-coding by relationship type
  - ⬜ Node size proportional to connection count
  - ⬜ WebSocket connection to `WS /ws/graph`
  - ⬜ Delta event handlers: `node_added`, `edge_added`, `edge_updated`, `question_added`
  - ⬜ Animate new nodes/edges with brief glow effect
  - ⬜ Click handler: opens side panel with node details
- ⬜ Build `src/frontend/styles.css`
  - ⬜ Dark background (#0a0a1a — space-like)
  - ⬜ Glow effects for new nodes (CSS animation)
  - ⬜ Pulsing red halo for contradiction nodes
  - ⬜ White glow for OpenQuestion nodes
  - ⬜ Clean, readable side panel

---

## Day 7 — Integration + Live Demo Flow

- ⬜ End-to-end test: upload paper → see graph animate live in browser
- ⬜ Verify contradiction detection is visually distinct (red edges glow)
- ⬜ Verify new paper upload triggers re-evaluation of existing edges
- ⬜ Add loading state to upload button
- ⬜ Add error handling — show user-friendly messages on failure
- ⬜ Polish: smooth force simulation, no overlapping labels
- ⬜ Add legend panel (what each color/shape means)
- ⬜ Performance test: 10 papers, verify no UI freeze

---

## Day 8 — Gap Finder (Stretch) + Demo Video

### Gap Finder (if time allows)
- ⬜ Build `src/agents/gap_finder.py`
  - ⬜ Query all claims from Neo4j
  - ⬜ Identify conceptual "spaces" between claims with no bridging paper
  - ⬜ Cross-reference with Web IQ to verify these gaps exist in real literature
  - ⬜ Score novelty: 0 = well-studied, 1 = truly unexplored
  - ⬜ Write OpenQuestion nodes to Neo4j
- ⬜ Add OpenQuestion rendering in D3.js (glowing white nodes)
- ⬜ Add "question resolves" animation when a new paper answers a gap

### Demo Video
- ⬜ Prepare 5 test papers from the same research domain (download real PDFs)
- ⬜ Script the demo flow (see PLAN.md for the 60-second sequence)
- ⬜ Record screen capture — 1920x1080, 60fps
- ⬜ Edit to 2–3 minutes max
- ⬜ Upload to YouTube (unlisted) or include in project submission

---

## Day 9 — Buffer + Submission

- ⬜ Final code review: no secrets, no hardcoded values, no TODO comments in shipped code
- ⬜ Run `git log --all --full-history` — check no secrets in history
- ⬜ Verify `.env` is gitignored and NOT pushed
- ⬜ Verify `.env.example` has placeholder values only
- ⬜ Final README review — all links work, setup instructions accurate
- ⬜ Confirm repo is public on GitHub
- ⬜ Submit on hackathon platform before **11:59 PM PT June 14, 2026**
- ⬜ Post in Discord for community vote

---

## Backlog (Nice to Have, Don't Block On)

- ⬜ Docker Compose setup for local Neo4j
- ⬜ Graph export as JSON/PNG
- ⬜ Paper search / filter within graph
- ⬜ "Time travel" — slider to see graph evolve as papers were added
- ⬜ Azure Container Apps deployment
- ⬜ Automated tests with pytest
