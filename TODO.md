# ✅ TODO.md — Task Breakdown

> Status legend: ⬜ Not started · 🔄 In progress · ✅ Done · ⏭️ Skipped

---

## Days 1–8: Core Pipeline ✅ COMPLETE

Full pipeline operational and tested: PDF ingestion → Foundry IQ → Extractor → Comparator →
Gap Finder (OpenAlex) → Neo4j → FastAPI WebSocket → D3.js force graph + A2A orchestration.

---

## Phase 2: Research Intelligence Features

### P1 — Contradiction Drill-Down ✅ COMPLETE AND TESTED

Backend: `get_edge_with_claims()`, `GET /edge/{edge_id}`, `EdgeDetailResponse`.
Frontend: edge click handler, `openEdgeDetailPanel()`, CSS.

---

### P2 — Field Consensus Meter + AI Explanation ← BUILD NEXT

Full spec in `FEATURE_field_consensus_meter.md`. Two parts — implement in order.

**Part 1: Auto-computed bar (frontend only)**
- ⬜ Add `computeConsensus(claimId)` to `graph.js` before `openDetailPanel()`
- ⬜ Insert consensus meter HTML into Claim branch of `openDetailPanel()`
- ⬜ Bind explain button click handler after `dom.panelBody.innerHTML = html`
- ⬜ Add Part 1 CSS to end of `styles.css`
- ⬜ Test: 1 paper → "No cross-paper data yet" message
- ⬜ Test: 2+ papers → bar renders with correct color + breakdown

**Part 2: AI explanation button (backend + frontend)**
- ⬜ Create `src/agents/consensus_explainer.py`
- ⬜ Add `get_claim_consensus_context()` to `graph_manager.py`
- ⬜ Add `ConsensusExplainResponse` to `models.py`
- ⬜ Add `GET /claim/{claim_id}/consensus/explain` to `graph.py` routes
- ⬜ Initialize `ConsensusExplainerAgent.from_env()` in `main.py` lifespan
- ⬜ Add `explainConsensus()` async function to `graph.js`
- ⬜ Add Part 2 CSS to end of `styles.css`
- ⬜ Test: button click → loading state → explanation fades in
- ⬜ Test: explanation is 2-3 sentences, mentions specific papers
- ⬜ Test: Re-explain works, network errors show toast
- ⬜ Delete `FEATURE_field_consensus_meter.md` after completion

---

### P3 — Claim Verification

- ⬜ Add search box to UI (keyboard shortcut `/` to focus)
- ⬜ Add `GET /verify?statement={text}` endpoint
- ⬜ Embed statement, query Neo4j top-5 similar claims by cosine similarity
- ⬜ Return `{ supports: [...], contradicts: [...], neutral: [...] }`
- ⬜ Render results panel

### P4 — Research Thread Tracer

- ⬜ Add `GET /trace?from={node_id}&to={node_id}` endpoint
- ⬜ Neo4j shortest path across all edge types
- ⬜ Shift+click second node to trigger
- ⬜ Highlight path in graph with animated pulsing

### P5 — Literature Review Generator

- ⬜ Add `POST /generate/review` endpoint (SSE streaming)
- ⬜ Agent walks graph: concepts → clusters → gaps
- ⬜ Stream markdown to modal with copy button

### P6 — Relationship Filter Bar

- ⬜ Filter strip: `All · Supports · Contradicts · Extends · Questions`
- ⬜ Dims non-matching edges and unconnected nodes
- ⬜ Pure frontend

### P7 — Batch Upload

- ⬜ Multi-file drop (up to 5 PDFs)
- ⬜ Per-file progress indicators
- ⬜ Parallel pipelines via `asyncio.gather()`

---

## Demo Video ← DO AFTER P2

- ⬜ Download 5 transformer papers from arXiv:
  - Attention Is All You Need (Vaswani et al. 2017)
  - BERT (Devlin et al. 2018)
  - RoBERTa (Liu et al. 2019)
  - Longformer (Beltagy et al. 2020)
  - Are Transformers Effective for Time Series? (Zeng et al. 2022) ← generates red edges
- ⬜ Script the sequence: empty graph → papers added one by one → graph thinks live →
      click contradiction edge (drill-down) → click disputed claim (consensus meter + explain)
- ⬜ Record at 1920×1080, 60fps
- ⬜ Edit to 2–3 minutes max
- ⬜ Upload to YouTube (unlisted), add link to README

---

## Day 9: Submission Checklist ← Do the day BEFORE June 14

- ⬜ `git log --all --full-history -- .env` → confirm .env never committed
- ⬜ Verify `.env.example` has only placeholder values
- ⬜ Confirm NEXT_AGENT_PROMPT.md is deleted
- ⬜ All FEATURE_*.md files deleted
- ⬜ README: add demo video link, verify setup instructions accurate
- ⬜ Confirm repo is public on GitHub
- ⬜ Submit before **11:59 PM PT June 14, 2026**
- ⬜ Post in Discord: https://aka.ms/agentsleague/discord

---

## Backlog (Post-submission)

- ⬜ Time travel slider
- ⬜ Graph export as PNG
- ⬜ Docker Compose for local Neo4j
- ⬜ Azure Container Apps deployment
