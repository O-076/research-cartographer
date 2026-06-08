# ✅ TODO.md — Task Breakdown

> Status legend: ⬜ Not started · 🔄 In progress · ✅ Done · ⏭️ Skipped

---

## Days 1–8: Core Pipeline ✅ COMPLETE

All pipeline work is done and tested. See git history for details.
Summary: PDF ingestion → Foundry IQ → Extractor → Comparator → Gap Finder (OpenAlex) →
Neo4j → FastAPI WebSocket → D3.js force graph — fully operational with A2A orchestration.

---

## Day 8–9: Demo Video ← DO THIS FIRST

- ⬜ Download 5 papers from the same domain (recommended: transformer architecture papers from arXiv)
  - "Attention Is All You Need" (Vaswani et al. 2017)
  - "BERT: Pre-training of Deep Bidirectional Transformers" (Devlin et al. 2018)
  - "RoBERTa: A Robustly Optimized BERT Pretraining Approach" (Liu et al. 2019)
  - "Longformer: The Long-Document Transformer" (Beltagy et al. 2020)
  - "Are Transformers Effective for Time Series Forecasting?" (Zeng et al. 2022) ← known contrarian paper, will generate red edges
- ⬜ Script the 60-second demo sequence (see PLAN.md)
- ⬜ Record at 1920×1080, 60fps
- ⬜ Edit to 2–3 minutes max
- ⬜ Upload to YouTube (unlisted) and add link to README

---

## Phase 2: Research Intelligence Features

### P1 — Contradiction Drill-Down ✅ COMPLETED

- ✅ **Backend**: Add `get_edge_with_claims(edge_id)` to `graph_manager.py`
- ✅ **Backend**: Add `GET /edge/{edge_id}` endpoint to `src/api/routes/graph.py`
- ✅ **Backend**: Add `EdgeDetailResponse` Pydantic model to `src/api/models.py`
- ✅ **Frontend**: Add click handler on edge `<line>` elements in `graph.js`
- ✅ **Frontend**: Add `openEdgeDetailPanel(edge)` function in `graph.js`
- ✅ **Frontend**: Add edge detail panel HTML section in `index.html`
- ✅ **Frontend**: Add CSS for edge panel, claim cards, VS divider in `styles.css`
- ✅ Test: click a CONTRADICTS edge → panel shows two claims side by side
- ✅ Test: reasoning text, strength bar, source paper info all render correctly

### P2 — Field Consensus Meter

- ⬜ Add `get_claim_consensus(claim_id)` to `graph_manager.py`
  - Cypher: count SUPPORTS vs CONTRADICTS edges, weight by strength
  - Returns: `{ support_pct, against_pct, neutral_pct, total_edges }`
- ⬜ Add `GET /claim/{claim_id}/consensus` endpoint
- ⬜ Add arc gauge component to the Claim node detail panel in `graph.js`
- ⬜ Test with a claim that has multiple edges of different types

### P3 — Claim Verification

- ⬜ Add search box to the UI (keyboard shortcut: `/` to focus)
- ⬜ Add `GET /verify?statement={text}` endpoint
  - Embeds the statement text
  - Queries Neo4j for top-5 most similar claims by cosine similarity
  - Returns: `{ supports: [...], contradicts: [...], neutral: [...] }`
- ⬜ Add verification results panel in `index.html`
- ⬜ Style results with green/red/grey claim cards

### P4 — Research Thread Tracer

- ⬜ Add `GET /trace?from={node_id}&to={node_id}` endpoint
  - Uses Neo4j shortest path query across all edge types
  - Returns: ordered list of nodes + edges forming the reasoning chain
  - Falls back to LLM-generated narrative if no direct path exists
- ⬜ Add "Trace Thread" button when two nodes are selected (shift+click second node)
- ⬜ Highlight the path in the graph with animated pulsing

### P5 — Literature Review Generator

- ⬜ Add `POST /generate/review` endpoint (async, streams via SSE)
  - Agent walks graph: most-connected concepts → support/contradiction clusters → gaps
  - Outputs structured markdown: intro, thematic sections, contradictions callout, gaps
- ⬜ Add "Generate Review" button to the UI
- ⬜ Show streaming output in a modal with copy-to-clipboard

### P6 — Relationship Filter Bar

- ⬜ Add filter strip above graph: `All · Supports · Contradicts · Extends · Questions`
- ⬜ Clicking a filter dims all non-matching edges and their unconnected nodes
- ⬜ Pure frontend — no API calls needed

### P7 — Batch Upload

- ⬜ Allow multi-file drop (up to 5 PDFs at once)
- ⬜ Show per-file progress indicators
- ⬜ Launch all pipelines in parallel via `asyncio.gather()`
- ⬜ Graph explodes into life from multiple directions simultaneously

---

## Day 9: Submission Checklist ← Do the day BEFORE submission

- ⬜ `git log --all --full-history -- .env` → confirm .env never committed
- ⬜ `git diff HEAD` → no secrets, no hardcoded values, no TODO in shipped code
- ⬜ Verify `.env.example` has only placeholder values
- ⬜ Delete `NEXT_AGENT_PROMPT.md` if still present
- ⬜ README: add demo video link, add A2A fallback note, verify setup instructions
- ⬜ Confirm repo is public on GitHub
- ⬜ Submit on hackathon platform before **11:59 PM PT June 14, 2026**
- ⬜ Post in Discord for community vote: https://aka.ms/agentsleague/discord

---

## Backlog (Post-submission / Nice to Have)

- ⬜ Time travel slider (scrub graph to see it build paper-by-paper)
- ⬜ Graph export as PNG (html2canvas)
- ⬜ Docker Compose for local Neo4j
- ⬜ Azure Container Apps deployment
- ⬜ Automated tests with pytest
