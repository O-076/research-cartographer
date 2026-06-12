# 📄 FEATURE: Literature Review Draft Generator

> Spec for implementing a one-click APA-formatted literature review generator.
> Viewable in browser, downloadable as .docx.
>
> PREREQUISITE: Implement FEATURE_research_thread_tracer.md first.
> The dom refs added in Step 6f of that spec are required here.
>
> Read AGENTS.md fully before starting.
> After completing and testing, delete this file and tick TODO.md.

---

## What This Builds

A "Generate Review" button in the header triggers a backend agent that:
1. Gathers from Neo4j: all complete papers, top 8 concept clusters, up to 5 contradiction pairs, up to 8 open questions
2. Formats APA in-text citations in Python (so the LLM uses correct citations)
3. Sends all data to LiteratureReviewAgent in one structured prompt
4. Returns a JSON object: title, abstract, sections array, references array

The result displays in a large scrollable modal styled like an academic paper.
A "Download .docx" button generates an APA-formatted Word document server-side
using python-docx and triggers a browser download.

Anti-slop measures are in the system prompt: thematic synthesis (not sequential
paper summaries), citation-backed claims only, explicit contradiction discussion,
banned filler phrases.

---

## Files to Change

| File | Change |
|------|--------|
| `src/agents/literature_review_agent.py` | New file |
| `src/graph/graph_manager.py` | Add `get_review_data()` |
| `src/api/models.py` | Add review models + download request |
| `src/api/routes/graph.py` | Add `POST /generate/review` + `POST /generate/review/docx` + `build_apa_docx()` |
| `src/api/main.py` | Initialize `LiteratureReviewAgent()` in lifespan |
| `src/frontend/index.html` | Add review button to header + review modal before `</body>` |
| `src/frontend/graph.js` | Add `initReview()`, `openReviewModal()`, `closeReviewModal()`, `renderReview()`, `downloadReviewDocx()` |
| `src/frontend/styles.css` | Add review modal CSS at end of file |
| `requirements.txt` | Add `python-docx==1.1.2` |

---

## Step 1 — requirements.txt: Add python-docx

Add this line to `requirements.txt` after the existing dependencies:

```
python-docx==1.1.2
```

After editing, run:
```bash
pip install python-docx==1.1.2 --break-system-packages
```

---

## Step 2 — New file: src/agents/literature_review_agent.py

```python
"""Literature Review Agent.

Gathers corpus data from Neo4j, formats APA citations in Python,
and generates a structured APA-format literature review via a single LLM call.
Returns a dict with keys: title, abstract, sections, references.
"""

import json
import logging
from typing import Any

from src.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are an academic writer producing a formal scientific literature review.

CRITICAL RULES — every violation makes the output unusable:
1. Write in formal academic prose. No conversational or AI-assistant language.
2. BANNED phrases (do not use): "It is important to note", "Overall, the literature suggests",
   "In conclusion, this review has demonstrated", "It is worth noting", "It is evident that",
   "This comprehensive review", "Notably,", "Importantly,", starting sentences with "Furthermore," or "Moreover,".
3. Every factual claim MUST have an APA in-text citation. Use ONLY the citations provided — never invent them.
4. Do NOT summarize papers individually. Synthesize thematically: compare, contrast, connect across papers.
5. Contradictions must be named explicitly: "Author (Year) directly challenge Author (Year) by arguing..."
6. Each thematic section must integrate claims from at least 2 different papers per paragraph.
7. Research gaps must reference the specific questions provided, not generic "more research is needed."
8. The abstract has NO citations.
9. References section must list every paper cited in the body.

OUTPUT: Return ONLY valid JSON — no preamble, no markdown backticks:
{
  "title": "Literature Review: [specific, descriptive title — not generic]",
  "abstract": "150-200 word summary of the corpus scope, key findings, and tensions. No citations.",
  "sections": [
    {"heading": "Introduction", "content": "200-250 words. Establish the research domain, scope of this review, why it matters. Cite the papers that define the field."},
    {"heading": "[Theme derived from concept cluster 1]", "content": "250-350 words with in-text citations. Synthesize across papers."},
    {"heading": "[Theme derived from concept cluster 2]", "content": "250-350 words with in-text citations."},
    [add 1-2 more thematic sections if concept data warrants it],
    {"heading": "Synthesis and Ongoing Debates", "content": "200-250 words. Explicitly name contradictions. Who argues what against whom, and why the debate matters."},
    {"heading": "Research Gaps and Future Directions", "content": "150-200 words. Reference specific open questions from the provided list."},
    {"heading": "Conclusion", "content": "100-150 words. Summarize key contributions and tensions. No new citations."}
  ],
  "references": [
    "APA-formatted reference string for every paper cited in the body."
  ]
}
"""


class LiteratureReviewAgent(BaseAgent):
    """Generates a full APA-format literature review from corpus graph data."""

    SYSTEM_PROMPT = _SYSTEM_PROMPT

    async def generate(self, review_data: dict[str, Any]) -> dict[str, Any]:
        """Generate the literature review.

        Args:
            review_data: Dict from graph_manager.get_review_data() with keys:
                papers, concepts, contradictions, questions.

        Returns:
            Dict with keys: title, abstract, sections (list of {heading, content}),
            references (list of str).
        """
        prompt = self._build_prompt(review_data)
        raw = await self.chat_completion(
            user_prompt=prompt,
            json_mode=True,
            max_tokens=4096,
            temperature=0.2,
        )
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.error("LiteratureReviewAgent: JSON parse failed", extra={"error": str(exc)})
            raise

        return parsed

    def _build_prompt(self, data: dict[str, Any]) -> str:
        papers = data.get("papers") or []
        concepts = data.get("concepts") or []
        contradictions = data.get("contradictions") or []
        questions = data.get("questions") or []

        # ── Papers with APA in-text and reference format ────────────
        paper_lines = []
        for p in papers:
            intext = self.apa_intext(p.get("authors"), p.get("year"))
            abstract_snippet = str(p.get("abstract") or "")[:300]
            paper_lines.append(
                f"- {intext}: \"{p.get('title', 'Untitled')}\""
                + (f" | Abstract: {abstract_snippet}" if abstract_snippet else "")
            )

        # ── Concept clusters ─────────────────────────────────────────
        concept_lines = []
        for c in concepts:
            claims_summary = " | ".join(
                f"{claim.get('text', '')[:100]} {self.apa_intext(claim.get('authors'), claim.get('paper_year'))}"
                for claim in (c.get("claims") or [])[:5]
            )
            concept_lines.append(
                f"CONCEPT [{c['concept']}] ({c['claim_count']} claims): {claims_summary}"
            )

        # ── Contradictions ───────────────────────────────────────────
        contra_lines = []
        for c in contradictions:
            cite1 = self.apa_intext(c.get("paper1_authors"), c.get("paper1_year"))
            cite2 = self.apa_intext(c.get("paper2_authors"), c.get("paper2_year"))
            contra_lines.append(
                f"- {cite1}: \"{str(c.get('claim1_text',''))[:150]}\"\n"
                f"  CONTRADICTS {cite2}: \"{str(c.get('claim2_text',''))[:150]}\"\n"
                f"  Comparator reasoning: \"{str(c.get('reasoning',''))[:200]}\""
            )

        # ── Open questions ───────────────────────────────────────────
        question_lines = [
            f"- (novelty {round((q.get('novelty_score') or 0) * 100)}%): {q.get('question', '')}"
            for q in questions
        ]

        lines = [
            "PAPERS IN CORPUS (use these exact APA citations):",
            *paper_lines,
            "",
            "CONCEPT CLUSTERS (derive thematic section headings from these):",
            *(concept_lines or ["None detected."]),
            "",
            "CONTRADICTIONS (must be discussed explicitly in Synthesis section):",
            *(contra_lines or ["None detected yet."]),
            "",
            "OPEN RESEARCH QUESTIONS (use in Research Gaps section):",
            *(question_lines or ["None detected yet."]),
            "",
            "Write the literature review following the system prompt instructions.",
        ]
        return "\n".join(lines)

    @staticmethod
    def apa_intext(authors: list[str] | None, year: int | None) -> str:
        """Format APA in-text citation: (Last, Year), (Last & Last, Year), or (Last et al., Year)."""
        authors = authors or []
        year_str = str(year) if year else "n.d."
        last_names = [a.strip().split()[-1] for a in authors if a.strip()]
        if not last_names:
            return f"(Anonymous, {year_str})"
        if len(last_names) == 1:
            return f"({last_names[0]}, {year_str})"
        if len(last_names) == 2:
            return f"({last_names[0]} & {last_names[1]}, {year_str})"
        return f"({last_names[0]} et al., {year_str})"
```

---

## Step 3 — graph_manager.py: Add get_review_data()

Add this method after `get_claims_for_verification()`:

```python
async def get_review_data(self) -> dict[str, Any]:
    """Gather all data needed to generate a literature review.

    Returns: papers, concept clusters (≥2 claims), contradiction pairs, open questions.
    """
    papers_query = """
    MATCH (p:Paper) WHERE p.status = 'complete'
    RETURN p.id AS id, p.title AS title, p.authors AS authors,
           p.year AS year, p.abstract AS abstract
    ORDER BY coalesce(p.year, 9999) ASC
    """

    concepts_query = """
    MATCH (concept:Concept)<-[:RELATES_TO]-(claim:Claim)<-[:CONTAINS]-(paper:Paper)
    WITH concept.name AS concept_name,
         count(DISTINCT claim) AS claim_count,
         collect(DISTINCT {
             text: claim.text,
             paper_title: paper.title,
             paper_year: paper.year,
             authors: paper.authors,
             claim_type: claim.type
         }) AS all_claims
    WHERE claim_count >= 2
    WITH concept_name, claim_count, all_claims[0..6] AS claims
    RETURN concept_name AS concept, claim_count, claims
    ORDER BY claim_count DESC
    LIMIT 8
    """

    contradictions_query = """
    MATCH (c1:Claim)-[r:CONTRADICTS]->(c2:Claim)
    MATCH (p1:Paper)-[:CONTAINS]->(c1)
    MATCH (p2:Paper)-[:CONTAINS]->(c2)
    RETURN c1.text AS claim1_text,
           p1.title AS paper1_title, p1.authors AS paper1_authors, p1.year AS paper1_year,
           c2.text AS claim2_text,
           p2.title AS paper2_title, p2.authors AS paper2_authors, p2.year AS paper2_year,
           r.reasoning AS reasoning
    LIMIT 5
    """

    questions_query = """
    MATCH (q:OpenQuestion) WHERE q.status = 'open'
    RETURN q.question AS question, q.novelty_score AS novelty_score
    ORDER BY q.novelty_score DESC
    LIMIT 8
    """

    async with self._driver.session() as session:
        papers_r = await session.run(papers_query, {})
        papers = [dict(r) async for r in papers_r]

        concepts_r = await session.run(concepts_query, {})
        concepts = [dict(r) async for r in concepts_r]

        contradictions_r = await session.run(contradictions_query, {})
        contradictions = [dict(r) async for r in contradictions_r]

        questions_r = await session.run(questions_query, {})
        questions = [dict(r) async for r in questions_r]

    return {
        "papers": papers,
        "concepts": concepts,
        "contradictions": contradictions,
        "questions": questions,
    }
```

---

## Step 4 — models.py: Add review models

Add these classes after `TraceResponse`. Do not modify existing classes.

```python
class ReviewSection(BaseModel):
    """A single section in the literature review."""
    heading: str
    content: str


class LiteratureReviewData(BaseModel):
    """The structured review document."""
    title: str
    abstract: str
    sections: list[ReviewSection]
    references: list[str]


class LiteratureReviewResponse(BaseModel):
    """Returned by POST /generate/review."""
    review: LiteratureReviewData
    paper_count: int


class ReviewDownloadRequest(BaseModel):
    """Body for POST /generate/review/docx."""
    review: dict[str, Any]
```

---

## Step 5 — graph.py routes: Add review endpoints + docx builder

### 5a — Add imports at top of graph.py

Add to the FastAPI imports line:
```python
from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect, Query, Response
```

(`Response` is new — needed for the binary docx download.)

Add to model imports:
```python
from src.api.models import (
    GraphResponse, PaperStatusResponse, PIPELINE_PROGRESS,
    EdgeDetailResponse, ConsensusExplainResponse,
    VerificationResultItem, VerificationResponse,
    TracePathNode, TracePathEdge, TraceResponse,
    ReviewSection, LiteratureReviewData, LiteratureReviewResponse, ReviewDownloadRequest,  # ← new
)
```

Add to standard library imports at the very top of the file:
```python
from io import BytesIO
from typing import Any
```

### 5b — Add build_apa_docx() function

Add this module-level function immediately before the `router = APIRouter()` line:

```python
def build_apa_docx(review: dict[str, Any]) -> bytes:
    """Convert a review dict to an APA-formatted .docx file.

    Requires python-docx (python-docx==1.1.2 in requirements.txt).
    APA 7th edition: Times New Roman 12pt, double spacing, 1" margins,
    hanging indent for references.
    """
    from docx import Document                                    # deferred: not all routes need it
    from docx.shared import Pt, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING

    doc = Document()

    # ── Page margins: 1" all sides ──────────────────────────────────
    sec = doc.sections[0]
    sec.top_margin = Inches(1)
    sec.bottom_margin = Inches(1)
    sec.left_margin = Inches(1)
    sec.right_margin = Inches(1)

    # ── Default style: Times New Roman 12pt ─────────────────────────
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(12)

    def para(text: str = "", bold: bool = False,
             align=WD_ALIGN_PARAGRAPH.LEFT,
             first_indent: float = 0.0,
             left_indent: float = 0.0) -> None:
        p = doc.add_paragraph()
        p.alignment = align
        fmt = p.paragraph_format
        fmt.line_spacing_rule = WD_LINE_SPACING.DOUBLE
        fmt.space_before = Pt(0)
        fmt.space_after = Pt(0)
        if first_indent:
            fmt.first_line_indent = Inches(first_indent)
        if left_indent:
            fmt.left_indent = Inches(left_indent)
        if text:
            run = p.add_run(text)
            run.bold = bold
            run.font.name = "Times New Roman"
            run.font.size = Pt(12)

    # ── Title ────────────────────────────────────────────────────────
    para(review.get("title", "Literature Review"),
         bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)

    # ── Abstract ─────────────────────────────────────────────────────
    if review.get("abstract"):
        para("Abstract", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
        para(review["abstract"])

    # ── Body sections ────────────────────────────────────────────────
    for section in review.get("sections", []):
        heading = section.get("heading", "")
        content = section.get("content", "")
        # APA Level 1 heading: centered, bold
        para(heading, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
        # Body paragraph: 0.5" first-line indent
        para(content, first_indent=0.5)

    # ── References ───────────────────────────────────────────────────
    para("References", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    for ref in review.get("references", []):
        # APA hanging indent: 0.5" left, -0.5" first line
        para(ref, left_indent=0.5, first_indent=-0.5)

    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()
```

### 5c — Add POST /generate/review endpoint

Add after `trace_thread()`:

```python
# ---------------------------------------------------------------------------
# REST — literature review generator
# ---------------------------------------------------------------------------

@router.post("/generate/review", response_model=LiteratureReviewResponse)
async def generate_review(request: Request) -> LiteratureReviewResponse:
    """Generate a full APA-format literature review from the loaded corpus."""
    graph_manager = request.app.state.graph_manager
    agent = request.app.state.literature_review

    review_data = await graph_manager.get_review_data()

    if not review_data.get("papers"):
        raise HTTPException(
            400,
            "No complete papers in corpus. Upload and process papers before generating a review.",
        )

    review_dict = await agent.generate(review_data)

    return LiteratureReviewResponse(
        review=LiteratureReviewData(**review_dict),
        paper_count=len(review_data["papers"]),
    )


@router.post("/generate/review/docx")
async def download_review_docx(payload: ReviewDownloadRequest) -> Response:
    """Convert a review JSON object to APA-formatted .docx for download."""
    try:
        docx_bytes = build_apa_docx(payload.review)
    except ImportError:
        raise HTTPException(
            500,
            "python-docx is not installed. Add python-docx==1.1.2 to requirements.txt and run pip install.",
        )

    title = str(payload.review.get("title", "literature_review"))
    filename = title.lower().replace(" ", "_")[:50].strip("_") + ".docx"

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

---

## Step 6 — main.py: Initialize LiteratureReviewAgent in lifespan

Add this import after the ThreadTracerAgent import:
```python
from src.agents.literature_review_agent import LiteratureReviewAgent
```

Add this line in the lifespan after `app.state.thread_tracer = ThreadTracerAgent()`:
```python
    app.state.literature_review = LiteratureReviewAgent()
```

---

## Step 7 — index.html: Add review button + modal

### 7a — Review button in header

Find this exact block (lines 4468–4470):
```html
            <button id="search-btn" class="header-search-btn" title="Verify a claim (press /)">
                <i class="fa-solid fa-magnifying-glass"></i>
            </button>
```

Add the review button immediately after it (before the closing `</div>` of `header-right`):
```html
            <button id="review-btn" class="header-search-btn" title="Generate Literature Review">
                <i class="fa-solid fa-book-open"></i>
            </button>
```

### 7b — Review modal

Add this block immediately before the `</body>` tag (after the search overlay):

```html
<!-- ── Literature Review Modal ─────────────────────────── -->
<div id="review-modal" class="review-modal hidden" role="dialog" aria-modal="true">
    <div class="review-modal-inner">
        <div class="review-modal-header">
            <div class="review-modal-title">
                <i class="fa-solid fa-book-open"></i>
                <span id="review-modal-heading">Literature Review</span>
            </div>
            <div class="review-modal-actions">
                <button id="review-download-btn" class="review-download-btn" disabled>
                    <i class="fa-solid fa-file-word"></i> Download .docx
                </button>
                <button id="review-close-btn" class="review-close-btn" title="Close">✕</button>
            </div>
        </div>
        <div id="review-content" class="review-content">
            <!-- Populated by renderReview() -->
        </div>
    </div>
</div>
```

---

## Step 8 — graph.js: Add review functions

### 8a — Add initReview() call in init()

Find this line in `init()`:
```javascript
        initSearch();
```

Add immediately after it:
```javascript
        initReview();
```

### 8b — Add review functions to graph.js

Add all of the following functions after `renderVerifyResults()` (the last function
added in the claim verification feature). Add them as one contiguous block.

```javascript
// ─── Literature Review Generator ─────────────────────────────────────────

// Stores the current review data for the download button
let _currentReview = null;

function initReview() {
    if (!dom.reviewBtn || !dom.reviewModal) return; // safety

    dom.reviewBtn.addEventListener("click", generateReview);

    if (dom.reviewCloseBtn) {
        dom.reviewCloseBtn.addEventListener("click", closeReviewModal);
    }

    if (dom.reviewDownloadBtn) {
        dom.reviewDownloadBtn.addEventListener("click", () => {
            if (_currentReview) downloadReviewDocx(_currentReview);
        });
    }

    // Click backdrop to close
    dom.reviewModal.addEventListener("click", e => {
        if (e.target === dom.reviewModal) closeReviewModal();
    });

    // Esc to close
    document.addEventListener("keydown", e => {
        if (e.key === "Escape" && dom.reviewModal && !dom.reviewModal.classList.contains("hidden")) {
            closeReviewModal();
        }
    });
}

function openReviewModal() {
    if (!dom.reviewModal) return;
    dom.reviewModal.classList.remove("hidden");
}

function closeReviewModal() {
    if (!dom.reviewModal) return;
    dom.reviewModal.classList.add("hidden");
}

async function generateReview() {
    if (!dom.reviewModal || !dom.reviewContent) return;

    openReviewModal();
    _currentReview = null;

    if (dom.reviewDownloadBtn) dom.reviewDownloadBtn.disabled = true;
    if (dom.reviewModalHeading) dom.reviewModalHeading = document.getElementById("review-modal-heading");

    dom.reviewContent.innerHTML = `
        <div class="review-loading">
            <div class="loading-spinner" style="width:32px;height:32px;border-width:3px"></div>
            <p>Analyzing corpus and generating review…</p>
            <p class="review-loading-hint">This may take 10–20 seconds.</p>
        </div>
    `;

    try {
        const res = await fetch(`${CONFIG.api.base}/generate/review`, { method: "POST" });
        if (res.status === 400) {
            const err = await res.json();
            dom.reviewContent.innerHTML = `
                <div class="review-empty">
                    <i class="fa-solid fa-circle-info"></i>
                    <p>${esc(err.detail || "No papers available.")}</p>
                </div>
            `;
            return;
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();
        _currentReview = data.review;
        renderReview(data);

        if (dom.reviewDownloadBtn) dom.reviewDownloadBtn.disabled = false;

    } catch (err) {
        console.error("Review generation failed:", err);
        dom.reviewContent.innerHTML = `
            <div class="review-empty">
                <i class="fa-solid fa-triangle-exclamation"></i>
                <p>Review generation failed.</p>
                <p style="opacity:0.5;font-size:12px">${esc(err.message)}</p>
            </div>
        `;
        showToast("Review generation failed", "error");
    }
}

function renderReview(data) {
    const review = data.review;
    const heading = document.getElementById("review-modal-heading");
    if (heading) heading.textContent = review.title || "Literature Review";

    let html = `<div class="review-document">`;

    // Title page area
    html += `<h1 class="review-title">${esc(review.title || "Literature Review")}</h1>`;
    html += `<p class="review-meta">${data.paper_count} paper${data.paper_count !== 1 ? "s" : ""} · Generated ${new Date().toLocaleDateString()}</p>`;

    // Abstract
    if (review.abstract) {
        html += `<div class="review-abstract">
            <h2 class="review-section-heading">Abstract</h2>
            <p class="review-body-text">${esc(review.abstract)}</p>
        </div>`;
    }

    // Sections
    for (const sec of (review.sections || [])) {
        html += `<div class="review-section">
            <h2 class="review-section-heading">${esc(sec.heading)}</h2>
            <p class="review-body-text">${esc(sec.content)}</p>
        </div>`;
    }

    // References
    if (review.references && review.references.length > 0) {
        html += `<div class="review-references">
            <h2 class="review-section-heading review-references-heading">References</h2>
            <ul class="review-ref-list">`;
        for (const ref of review.references) {
            html += `<li class="review-ref-item">${esc(ref)}</li>`;
        }
        html += `</ul></div>`;
    }

    html += `</div>`;
    dom.reviewContent.innerHTML = html;
}

async function downloadReviewDocx(review) {
    if (dom.reviewDownloadBtn) {
        dom.reviewDownloadBtn.disabled = true;
        dom.reviewDownloadBtn.innerHTML = `<div class="loading-spinner" style="width:14px;height:14px;border-width:2px;margin:0"></div> Generating…`;
    }

    try {
        const res = await fetch(`${CONFIG.api.base}/generate/review/docx`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ review }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = (review.title || "literature_review")
            .toLowerCase().replace(/\s+/g, "_").substring(0, 50) + ".docx";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

    } catch (err) {
        console.error("Download failed:", err);
        showToast("Download failed", "error");
    } finally {
        if (dom.reviewDownloadBtn) {
            dom.reviewDownloadBtn.disabled = false;
            dom.reviewDownloadBtn.innerHTML = `<i class="fa-solid fa-file-word"></i> Download .docx`;
        }
    }
}
```

---

## Step 9 — styles.css: Add review modal CSS at end of file

```css
/* ─── Literature Review Modal ─── */

.review-modal {
    position: fixed;
    inset: 0;
    z-index: 400;
    background: rgba(5, 5, 15, 0.82);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
    animation: overlay-in 0.2s ease forwards;
}

.review-modal.hidden { display: none; }

.review-modal-inner {
    background: var(--bg-glass);
    backdrop-filter: blur(32px);
    -webkit-backdrop-filter: blur(32px);
    border: 1px solid var(--border-glass);
    border-radius: var(--radius-md);
    width: min(820px, 95vw);
    height: min(88vh, 900px);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    box-shadow: 0 32px 80px rgba(0, 0, 0, 0.6);
    animation: search-drop-in 0.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.review-modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px;
    border-bottom: 1px solid var(--border-glass);
    flex-shrink: 0;
}

.review-modal-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
}

.review-modal-title i { color: var(--color-paper); }

.review-modal-actions {
    display: flex;
    align-items: center;
    gap: 8px;
}

.review-download-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(74, 158, 255, 0.1);
    border: 1px solid rgba(74, 158, 255, 0.3);
    color: var(--color-paper);
    font-size: 12px;
    font-weight: 500;
    font-family: inherit;
    padding: 6px 14px;
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: all var(--transition-fast);
}

.review-download-btn:hover:not(:disabled) {
    background: rgba(74, 158, 255, 0.18);
    border-color: rgba(74, 158, 255, 0.5);
}

.review-download-btn:disabled {
    opacity: 0.45;
    cursor: not-allowed;
}

.review-close-btn {
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: 1px solid var(--border-glass);
    border-radius: 6px;
    color: var(--text-muted);
    font-size: 13px;
    cursor: pointer;
    transition: all var(--transition-fast);
    font-family: inherit;
}

.review-close-btn:hover {
    background: rgba(255,255,255,0.07);
    color: var(--text-primary);
}

.review-content {
    flex: 1;
    overflow-y: auto;
    padding: 0;
    scrollbar-width: thin;
    scrollbar-color: var(--border-hover) transparent;
}

/* ── Document Styles (paper-like) ── */

.review-document {
    max-width: 680px;
    margin: 0 auto;
    padding: 48px 40px 64px;
    font-family: "Times New Roman", Times, serif;
}

.review-title {
    font-size: 18px;
    font-weight: 700;
    text-align: center;
    color: var(--text-primary);
    line-height: 1.4;
    margin-bottom: 6px;
    font-family: "Times New Roman", Times, serif;
}

.review-meta {
    text-align: center;
    font-size: 12px;
    color: var(--text-muted);
    font-family: inherit;
    margin-bottom: 32px;
    font-style: italic;
}

.review-abstract {
    margin-bottom: 28px;
}

.review-section {
    margin-bottom: 28px;
}

.review-section-heading {
    font-size: 14px;
    font-weight: 700;
    text-align: center;
    color: var(--text-primary);
    margin-bottom: 12px;
    font-family: "Times New Roman", Times, serif;
}

.review-body-text {
    font-size: 13.5px;
    line-height: 2;           /* APA double spacing */
    color: var(--text-primary);
    text-indent: 2em;         /* APA first-line indent */
    text-align: justify;
    font-family: "Times New Roman", Times, serif;
    margin: 0;
}

.review-abstract .review-body-text {
    text-indent: 0;           /* APA: abstract has no indent */
}

.review-references { margin-top: 32px; }

.review-references-heading { margin-bottom: 16px; }

.review-ref-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.review-ref-item {
    font-size: 13px;
    line-height: 1.8;
    color: var(--text-secondary);
    font-family: "Times New Roman", Times, serif;
    padding-left: 2em;
    text-indent: -2em;        /* APA hanging indent */
}

/* Loading / empty states inside modal */
.review-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    padding: 80px 40px;
    color: var(--text-secondary);
    font-size: 14px;
    text-align: center;
}

.review-loading-hint {
    font-size: 12px;
    color: var(--text-muted);
}

.review-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    padding: 80px 40px;
    color: var(--text-secondary);
    font-size: 14px;
    text-align: center;
}

.review-empty i {
    font-size: 28px;
    opacity: 0.4;
}
```

---

## Expected Behavior

**Button click → modal opens with spinner:**
"Analyzing corpus and generating review… This may take 10–20 seconds."

**Review renders:**
- Title centered at top
- Meta line: "5 papers · Generated 6/12/2026"
- Abstract section (no citations, no indent)
- Thematic sections (one per concept cluster, double-spaced, first-line indented)
- Synthesis and Debates (explicit contradiction discussion)
- Research Gaps (references specific OpenQuestion nodes)
- Conclusion
- References (hanging indent, APA format)

**"Download .docx" button:**
- Triggers spinner on button
- Browser downloads "literature_review_attention_mechanisms_in_deep_learning.docx"
- File opens in Word: Times New Roman 12pt, double spacing, 1" margins, APA headings

**Edge case — no papers:**
Modal opens, shows "No complete papers in corpus" message.

---

## Testing Checklist

- ⬜ Click "Generate Review" button → modal opens, spinner shows
- ⬜ Review renders with all sections: abstract, thematic sections, synthesis, gaps, conclusion, references
- ⬜ All in-text citations use format (Last, Year) — no invented citations
- ⬜ Contradictions are discussed by name in the Synthesis section
- ⬜ Research Gaps section references specific questions from the corpus
- ⬜ "Download .docx" button disabled during generation, enabled after
- ⬜ Click "Download .docx" → file downloads, opens in Word
- ⬜ Word file: Times New Roman 12pt, double spacing, 1" margins, centered headings, hanging refs
- ⬜ Esc key closes modal
- ⬜ Click backdrop closes modal
- ⬜ Empty corpus → friendly error message, no crash
- ⬜ No console errors
- ⬜ `pip install python-docx==1.1.2` ran successfully (check `python -c "import docx"`)

---

## Notes

**APA formatting in Python before LLM.** The `apa_intext()` static method runs in Python
to produce `(Vaswani et al., 2017)` strings before the LLM sees the prompt. This prevents
hallucinated citations — the LLM can only use citation strings explicitly provided.

**max_tokens=4096.** A full literature review is ~2000 words ≈ ~2500 tokens output.
The 4096 limit gives enough headroom. If the LLM truncates, raise to 8192.

**Deferred docx import.** `build_apa_docx()` uses `from docx import Document` inside
the function body. This means the server starts even if python-docx isn't installed yet,
and the error surfaces only when the download endpoint is called — with a clear 500
message telling the developer what to install.

**`_currentReview` module-level variable.** The review data is stored in a module-level
`let _currentReview = null` so the download button can access it without a second API call.
This is correct for a single-user hackathon demo. It would not be thread-safe in
a multi-user production deployment, but that's out of scope.

**review-modal z-index is 400** (above search-overlay z-index 300 and detail-panel).
