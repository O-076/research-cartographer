# ✅ TODO.md — Task Breakdown

> Status legend: ⬜ Not started · 🔄 In progress · ✅ Done · ⏭️ Skipped

---

## Days 1–8: Core Pipeline ✅ COMPLETE

Full pipeline: PDF → Foundry IQ → Extractor → Comparator → Gap Finder (OpenAlex)
→ Neo4j → FastAPI WebSocket → D3.js force graph + A2A orchestration.

---

## Phase 2: Research Intelligence Features

### P1 — Contradiction Drill-Down ✅ COMPLETE AND TESTED
### P2 — Field Consensus Meter + AI Explanation ✅ COMPLETE AND TESTED

---

### P3 — Claim Verification ✅ COMPLETE

**Backend**
- ✅ Create `src/agents/claim_verifier.py`
- ✅ Add `get_claims_for_verification()` to `graph_manager.py`
- ✅ Add `VerificationResultItem` + `VerificationResponse` to `models.py`
- ✅ Add `GET /verify` endpoint to `graph.py` (add `Query` to fastapi imports)
- ✅ Initialize `ClaimVerifierAgent()` in `main.py` lifespan step 6

**Frontend**
- ✅ Add `search-btn` to header in `index.html`
- ✅ Add search overlay HTML before `</body>` in `index.html`
- ✅ Add `dom.searchBtn`, `dom.searchOverlay`, `dom.searchInput` to dom object in `graph.js`
- ✅ Call `initSearch()` at end of `init()` in `graph.js`
- ✅ Add `initSearch()`, `openSearchOverlay()`, `closeSearchOverlay()` to `graph.js`
- ✅ Add `verifyStatement()` to `graph.js`
- ✅ Add `openVerificationPanel()` to `graph.js`
- ✅ Add `renderVerifyResults()` to `graph.js`
- ✅ Add all CSS to end of `styles.css`

**Testing**
- ✅ `/` key → overlay opens, input focused
- ✅ Valid statement + Enter → loading → results grouped correctly
- ✅ Click result → navigates to claim node in graph
- ✅ Empty corpus → "No relevant claims found" message
- ✅ Delete `FEATURE_claim_verification.md` after passing

---

### P4 — Research Thread Tracer

- ⬜ Add `GET /trace?from={node_id}&to={node_id}` endpoint
- ⬜ Neo4j shortest path across semantic edge types
- ⬜ Shift+click second node to trigger
- ⬜ Highlight path in graph with animated pulsing

### P5 — Literature Review Generator

- ⬜ Add `POST /generate/review` endpoint (SSE streaming)
- ⬜ Agent walks graph: concepts → clusters → gaps → structured markdown
- ⬜ Stream to modal with copy button

### P6 — Relationship Filter Bar

- ⬜ Filter strip: `All · Supports · Contradicts · Extends · Questions`
- ⬜ Dims non-matching edges and unconnected nodes
- ⬜ Pure frontend, no API calls

### P7 — Batch Upload

- ⬜ Multi-file drop (up to 5 PDFs at once)
- ⬜ Per-file progress indicators
- ⬜ Parallel pipelines via `asyncio.gather()`

---

## Demo Video ← DO AFTER P3

- ⬜ Download 5 transformer papers from arXiv:
  - Attention Is All You Need (Vaswani et al. 2017)
  - BERT (Devlin et al. 2018)
  - RoBERTa (Liu et al. 2019)
  - Longformer (Beltagy et al. 2020)
  - Are Transformers Effective for Time Series? (Zeng et al. 2022) ← generates red edges
- ⬜ Script demo: empty → papers load → contradiction drill-down → consensus meter
  + explain → verify a statement live
- ⬜ Record at 1920×1080, 60fps, under 3 minutes
- ⬜ Upload YouTube (unlisted), add link to README

---

## Day 9: Submission Checklist ← Do the day BEFORE June 14

- ⬜ `git log --all --full-history -- .env` → confirm .env never committed
- ⬜ Verify `.env.example` has only placeholder values
- ⬜ Confirm all FEATURE_*.md files deleted
- ⬜ README: add demo video link, update build status
- ⬜ Confirm repo is public on GitHub
- ⬜ Submit before **11:59 PM PT June 14, 2026**
- ⬜ Post in Discord: https://aka.ms/agentsleague/discord

---

## Backlog (Post-submission)

- ⬜ Time travel slider
- ⬜ Graph export as PNG
- ⬜ Docker Compose for local Neo4j
- ⬜ Azure Container Apps deployment
