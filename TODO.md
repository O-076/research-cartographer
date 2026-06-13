# ✅ TODO.md - Task Breakdown

> Status legend: ⬜ Not started · 🔄 In progress · ✅ Done · ⏭️ Skipped

---

## Core Pipeline ✅ COMPLETE
## P1 Contradiction Drill-Down ✅ COMPLETE AND TESTED
## P2 Field Consensus Meter + AI Explanation ✅ COMPLETE AND TESTED
## P3 Claim Verification ✅ COMPLETE AND TESTED

---

## P4 - Research Thread Tracer ← BUILD NEXT (see FEATURE_research_thread_tracer.md)

**Backend**
- [x] Create `src/agents/thread_tracer.py`
- [x] Add `get_path_between()` to `graph_manager.py`
- [x] Add `TracePathNode`, `TracePathEdge`, `TraceResponse` to `models.py`
- [x] Add `GET /trace` endpoint to `graph.py`
- [x] Initialize `ThreadTracerAgent()` in `main.py` lifespan

**Frontend**
- [x] Add `traceStartNodeId: null, tracePath: null` to state object
- [x] Modify node click handler for shift+click (lines 3307–3312)
- [x] Add trace highlighting in render() before `}, 50)` (line 3355)
- [x] Extend Escape handler in initSearch()
- [x] Add `handleTraceClick()`, `traceThread()`, `openTracePanel()` to graph.js
- [x] Add dom refs for review elements in cacheDom() (Step 6f - prereq for P5)
- [x] Add trace CSS to end of styles.css

**Testing**
- [x] Shift+click node → trace-start ring appears
- [x] Shift+click second node → loading → panel + path highlighted in graph
- [x] Esc → highlight clears
- [x] No path found → 404 → friendly message
- ⬜ Delete `FEATURE_research_thread_tracer.md` after passing

---

## P5 - Literature Review Generator ← AFTER P4 (see FEATURE_literature_review.md)

**Dependencies**
- [x] `pip install python-docx==1.1.2 --break-system-packages`
- [x] Add `python-docx==1.1.2` to `requirements.txt`

**Backend**
- [x] Create `src/agents/literature_review_agent.py`
- [x] Add `get_review_data()` to `graph_manager.py`
- [x] Add `ReviewSection`, `LiteratureReviewData`, `LiteratureReviewResponse`, `ReviewDownloadRequest` to `models.py`
- [x] Add `Response` to FastAPI imports in `graph.py`
- [x] Add `build_apa_docx()` function to `graph.py`
- [x] Add `POST /generate/review` and `POST /generate/review/docx` endpoints
- [x] Initialize `LiteratureReviewAgent()` in `main.py` lifespan

**Frontend**
- [x] Add `#review-btn` to header in `index.html` (after search-btn)
- [x] Add review modal HTML before `</body>` in `index.html`
- [x] Add `initReview()` call in `init()` after `initSearch()`
- [x] Add `initReview()`, `generateReview()`, `openReviewModal()`, `closeReviewModal()`, `renderReview()`, `downloadReviewDocx()` to graph.js
- [x] Add review modal CSS to end of `styles.css`

**Testing**
- [x] `python -c "import docx"` - no ImportError
- [x] Click review button → modal opens, spinner shows
- [x] Review renders with all sections, APA citations, references
- [x] No invented citations in output
- [x] Contradictions discussed by name in Synthesis section
- [x] Download .docx → file opens in Word with correct APA formatting
- [x] Esc / backdrop → closes modal
- [x] Empty corpus → friendly error message
- [x] Delete `FEATURE_literature_review.md` after passing

---

## Demo Video ← DO AFTER P4 OR P5 (whichever completes first)

⚠️ **3 days left. Do not skip this.**

- ⬜ Download 5 transformer papers from arXiv:
  - Attention Is All You Need (Vaswani et al. 2017) - arxiv.org/abs/1706.03762
  - BERT (Devlin et al. 2018) - arxiv.org/abs/1810.04805
  - RoBERTa (Liu et al. 2019) - arxiv.org/abs/1907.11692
  - Longformer (Beltagy et al. 2020) - arxiv.org/abs/2004.05150
  - Are Transformers Effective for Time Series? (Zeng et al. 2022) - arxiv.org/abs/2205.13504
- ⬜ Clear Neo4j DB before recording
- ⬜ Script demo sequence (2–3 min):
  1. Empty graph state (show "No papers yet")
  2. Upload paper 1 → watch graph animate live
  3. Upload papers 2-5 one by one → contradictions appear (red edges)
  4. Click a contradiction edge → drill-down panel
  5. Click a disputed claim → consensus meter + AI explain
  6. Press `/` → verify "attention mechanisms are sufficient for all sequence tasks"
  7. Shift+click two nodes → trace the reasoning chain
  8. Click "Generate Review" → APA review appears → Download .docx
- ⬜ Record at 1920×1080, 60fps (OBS or similar)
- ⬜ Edit to 2-3 minutes max - cut dead time aggressively
- ⬜ Upload to YouTube (unlisted), add link to README

---

## Day 9: Submission Checklist ← Do June 13

- ⬜ `git log --all --full-history -- .env` → confirm .env never committed
- ⬜ Verify `.env.example` has only placeholder values
- ⬜ Confirm all `FEATURE_*.md` files deleted from repo
- ⬜ README: add demo video link, update build status, verify setup instructions
- ⬜ Confirm repo is public on GitHub
- ⬜ Submit on hackathon platform before **11:59 PM PT June 14, 2026**
- ⬜ Post in Discord for community vote: https://aka.ms/agentsleague/discord

---

## Backlog (Post-submission)

- ⬜ Relationship filter bar (P6)
- ⬜ Batch upload (P7)
- ⬜ Time travel slider
- ⬜ Graph export as PNG
