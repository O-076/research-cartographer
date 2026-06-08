# 🔴 FEATURE: Contradiction Drill-Down

> Spec file for implementing edge click → side panel showing two claims in detail.
> Read this fully before writing any code.
> After completing this feature, delete this file and mark the tasks done in TODO.md.

---

## What to Build

When a user clicks any edge in the D3.js graph, a side panel opens showing:
- The edge type and relationship strength
- The Comparator's full reasoning for why this relationship exists
- The two claims side by side with a visual divider
- For each claim: the full claim text, its type, section, confidence score, and the source chunk text it was extracted from
- For each claim: which paper it belongs to (title + authors)

Clicking a contradiction edge (red) is the primary use case and the demo moment.
All edge types (supports, extends, replicates, refines) should also open the panel.

---

## Files to Change

| File | Change |
|------|--------|
| `src/graph/graph_manager.py` | Add `get_edge_with_claims()` method |
| `src/api/models.py` | Add `EdgeDetailResponse` Pydantic model |
| `src/api/routes/graph.py` | Add `GET /edge/{edge_id}` endpoint |
| `src/frontend/graph.js` | Add edge click handler + `openEdgeDetailPanel()` |
| `src/frontend/index.html` | No changes needed — reuse existing `#detail-panel` |
| `src/frontend/styles.css` | Add styles for claim cards and VS divider |

---

## Step 1 — graph_manager.py

Add this method to the `GraphManager` class.
Place it after `add_edge()` in the Edge CRUD section.

```python
async def get_edge_with_claims(
    self, edge_id: str
) -> dict[str, Any] | None:
    """Fetch a relationship and both connected claims with their papers.

    Returns a dict with keys: edge, source_claim, target_claim,
    source_paper, target_paper. Returns None if the edge is not found.
    """
    query = """
    MATCH (src:Claim)-[r {id: $edge_id}]->(tgt:Claim)
    MATCH (p1:Paper)-[:CONTAINS]->(src)
    MATCH (p2:Paper)-[:CONTAINS]->(tgt)
    RETURN
        r.id           AS edge_id,
        r.type         AS edge_type,
        r.strength     AS edge_strength,
        r.reasoning    AS edge_reasoning,
        r.created_at   AS edge_created_at,
        src.id         AS src_id,
        src.text       AS src_text,
        src.type       AS src_type,
        src.confidence AS src_confidence,
        src.section    AS src_section,
        src.source_chunk_text AS src_chunk,
        src.paper_id   AS src_paper_id,
        tgt.id         AS tgt_id,
        tgt.text       AS tgt_text,
        tgt.type       AS tgt_type,
        tgt.confidence AS tgt_confidence,
        tgt.section    AS tgt_section,
        tgt.source_chunk_text AS tgt_chunk,
        tgt.paper_id   AS tgt_paper_id,
        p1.id          AS src_paper_id_full,
        p1.title       AS src_paper_title,
        p1.authors     AS src_paper_authors,
        p1.year        AS src_paper_year,
        p2.id          AS tgt_paper_id_full,
        p2.title       AS tgt_paper_title,
        p2.authors     AS tgt_paper_authors,
        p2.year        AS tgt_paper_year
    """
    async with self._driver.session() as session:
        result = await session.run(query, {"edge_id": edge_id})
        record = await result.single()
        if not record:
            return None

        data = dict(record)
        return {
            "edge": {
                "id": data["edge_id"],
                "type": data["edge_type"],
                "strength": data["edge_strength"] or 0.0,
                "reasoning": data["edge_reasoning"] or "",
                "created_at": data["edge_created_at"],
            },
            "source_claim": {
                "id": data["src_id"],
                "text": data["src_text"],
                "type": data["src_type"],
                "confidence": data["src_confidence"] or 0.0,
                "section": data["src_section"],
                "source_chunk_text": data["src_chunk"] or "",
                "paper_id": data["src_paper_id"],
            },
            "target_claim": {
                "id": data["tgt_id"],
                "text": data["tgt_text"],
                "type": data["tgt_type"],
                "confidence": data["tgt_confidence"] or 0.0,
                "section": data["tgt_section"],
                "source_chunk_text": data["tgt_chunk"] or "",
                "paper_id": data["tgt_paper_id"],
            },
            "source_paper": {
                "id": data["src_paper_id_full"],
                "title": data["src_paper_title"],
                "authors": data["src_paper_authors"] or [],
                "year": data["src_paper_year"],
            },
            "target_paper": {
                "id": data["tgt_paper_id_full"],
                "title": data["tgt_paper_title"],
                "authors": data["tgt_paper_authors"] or [],
                "year": data["tgt_paper_year"],
            },
        }
```

---

## Step 2 — models.py

Add this class to `src/api/models.py`, after `GraphResponse`:

```python
class EdgeDetailResponse(BaseModel):
    """Returned by GET /edge/{edge_id}."""

    edge: dict[str, Any]
    source_claim: dict[str, Any]
    target_claim: dict[str, Any]
    source_paper: dict[str, Any]
    target_paper: dict[str, Any]
```

---

## Step 3 — graph.py (routes)

Add this endpoint to `src/api/routes/graph.py`.
Place it after the existing `GET /graph` endpoint.

Import `EdgeDetailResponse` from models at the top of the file.

```python
@router.get("/edge/{edge_id}", response_model=EdgeDetailResponse)
async def get_edge_detail(
    edge_id: str,
    request: Request,
) -> EdgeDetailResponse:
    """Fetch full details for a relationship: both claims + their papers."""
    graph: GraphManager = request.app.state.graph
    result = await graph.get_edge_with_claims(edge_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Edge {edge_id!r} not found")
    return EdgeDetailResponse(**result)
```

---

## Step 4 — graph.js (frontend)

### 4a — Add edge click handler

In the `render()` function, find the `edgeEnter` block where edges are created.
It currently looks like this:

```javascript
const edgeEnter = edgeSel.enter()
    .append("line")
    .attr("class", d => `edge-line ${getEdgeClass(d)}${animate ? " edge-enter" : ""}`)
    // ... more .attr() calls
```

Add these three lines immediately after the last `.attr()` call on `edgeEnter`,
before `const edgeMerge = edgeEnter.merge(edgeSel)`:

```javascript
edgeEnter
    .style("cursor", "pointer")
    .on("click", (event, d) => {
        event.stopPropagation();
        openEdgeDetailPanel(d);
    })
    .on("mouseenter", function(event, d) {
        d3.select(this)
            .transition().duration(150)
            .attr("stroke-opacity", 0.85)
            .attr("stroke-width", edgeWidth(d) * 1.8);
        const label = `${d.type || "edge"} (${Math.round((d.strength || 0) * 100)}%)`;
        showTooltip(label, event.clientX, event.clientY);
    })
    .on("mousemove", (event) => {
        state.tooltip.style.left = `${event.clientX + 14}px`;
        state.tooltip.style.top = `${event.clientY - 10}px`;
    })
    .on("mouseleave", function(event, d) {
        d3.select(this)
            .transition().duration(150)
            .attr("stroke-opacity", 0.45)
            .attr("stroke-width", edgeWidth(d));
        hideTooltip();
    });
```

### 4b — Add openEdgeDetailPanel function

Add this function to `graph.js` immediately after the `openDetailPanel(node)` function.
Do not modify `openDetailPanel` — add this as a new separate function.

```javascript
async function openEdgeDetailPanel(edge) {
    // Show loading state immediately
    dom.detailPanel.classList.add("open");
    dom.panelTitle.innerHTML = `<i class="fa-solid fa-arrow-right-arrow-left"></i> Relationship`;
    dom.panelContent.innerHTML = `
        <div class="panel-loading">
            <div class="loading-spinner"></div>
            <p>Loading relationship details…</p>
        </div>
    `;

    try {
        const res = await fetch(`${CONFIG.api.base}/edge/${encodeURIComponent(edge.id)}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        const { edge: e, source_claim, target_claim, source_paper, target_paper } = data;
        const edgeType = (e.type || "supports").toLowerCase();
        const edgeColor = CONFIG.colors[edgeType] || CONFIG.colors.replicates;
        const strengthPct = Math.round((e.strength || 0) * 100);

        // Set panel title with colored edge type badge
        dom.panelTitle.innerHTML = `<i class="fa-solid fa-arrow-right-arrow-left"></i> Relationship`;

        let html = "";

        // Edge type badge + strength
        html += `<div class="panel-badges">
            ${badge(edgeType.toUpperCase(), `edge-badge edge-type-${edgeType}`)}
        </div>`;

        // Strength bar
        html += section("Strength", `
            <div class="confidence-meter">
                <div class="confidence-bar-bg">
                    <div class="confidence-bar-fill"
                         style="width:${strengthPct}%;background:${edgeColor}"></div>
                </div>
                <span class="confidence-value">${strengthPct}%</span>
            </div>
        `);

        // Reasoning
        if (e.reasoning) {
            html += section("Agent Reasoning", `
                <p class="panel-text reasoning-text">${esc(e.reasoning)}</p>
            `);
        }

        // Two claims side by side
        html += `<div class="claims-comparison">
            <div class="claim-card claim-card-source">
                <div class="claim-card-header">
                    <span class="claim-card-label source-label">
                        <i class="fa-solid fa-arrow-up-from-bracket"></i> Source Claim
                    </span>
                    <span class="claim-card-paper">${esc(source_paper.title || "Unknown paper")}</span>
                    ${source_paper.year ? `<span class="claim-card-year">${source_paper.year}</span>` : ""}
                </div>
                <p class="claim-card-text">${esc(source_claim.text || "")}</p>
                <div class="claim-card-meta">
                    ${badge(source_claim.type || "finding", `type-${(source_claim.type || "finding").toLowerCase()}`)}
                    ${badge(source_claim.section || "unknown", "type-paper")}
                    <span class="claim-confidence">${Math.round((source_claim.confidence || 0) * 100)}% confidence</span>
                </div>
                ${source_claim.source_chunk_text ? `
                <details class="source-chunk-details">
                    <summary>Source text</summary>
                    <p class="panel-text source-chunk-text">${esc(source_claim.source_chunk_text)}</p>
                </details>` : ""}
            </div>

            <div class="claims-vs-divider">
                <div class="vs-line"></div>
                <span class="vs-badge" style="color:${edgeColor};border-color:${edgeColor}">
                    ${edgeType.toUpperCase()}
                </span>
                <div class="vs-line"></div>
            </div>

            <div class="claim-card claim-card-target">
                <div class="claim-card-header">
                    <span class="claim-card-label target-label">
                        <i class="fa-solid fa-arrow-down-to-bracket"></i> Target Claim
                    </span>
                    <span class="claim-card-paper">${esc(target_paper.title || "Unknown paper")}</span>
                    ${target_paper.year ? `<span class="claim-card-year">${target_paper.year}</span>` : ""}
                </div>
                <p class="claim-card-text">${esc(target_claim.text || "")}</p>
                <div class="claim-card-meta">
                    ${badge(target_claim.type || "finding", `type-${(target_claim.type || "finding").toLowerCase()}`)}
                    ${badge(target_claim.section || "unknown", "type-paper")}
                    <span class="claim-confidence">${Math.round((target_claim.confidence || 0) * 100)}% confidence</span>
                </div>
                ${target_claim.source_chunk_text ? `
                <details class="source-chunk-details">
                    <summary>Source text</summary>
                    <p class="panel-text source-chunk-text">${esc(target_claim.source_chunk_text)}</p>
                </details>` : ""}
            </div>
        </div>`;

        dom.panelContent.innerHTML = html;

    } catch (err) {
        console.error("Failed to load edge detail:", err);
        dom.panelContent.innerHTML = `
            <div class="panel-error">
                <i class="fa-solid fa-triangle-exclamation"></i>
                <p>Could not load relationship details.</p>
                <p class="panel-text" style="opacity:0.5">${esc(err.message)}</p>
            </div>
        `;
    }
}
```

### 4c — Verify `section()` and `badge()` helpers exist

These functions are already defined in `graph.js`. Do not redefine them.
Confirm they exist by searching for `function section(` and `function badge(`.
If for some reason they are missing, add them:

```javascript
function section(title, contentHtml) {
    return `<div class="panel-section">
        <div class="panel-section-title">${esc(title)}</div>
        <div class="panel-section-body">${contentHtml}</div>
    </div>`;
}

function badge(text, cls) {
    return `<span class="badge ${cls}">${esc(text)}</span>`;
}
```

---

## Step 5 — styles.css

Add these styles at the END of `styles.css`. Do not modify existing styles.

```css
/* ─── Edge Detail Panel — Claim Comparison ─── */

.claims-comparison {
    display: flex;
    flex-direction: column;
    gap: 0;
    margin-top: 12px;
}

.claim-card {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--border-glass);
    border-radius: var(--radius-md);
    padding: 14px;
    transition: border-color var(--transition-normal);
}

.claim-card:hover {
    border-color: var(--border-hover);
}

.claim-card-source {
    border-top: 2px solid var(--color-paper);
}

.claim-card-target {
    border-top: 2px solid var(--color-paper);
}

.claim-card-header {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    margin-bottom: 10px;
}

.claim-card-label {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
}

.claim-card-paper {
    font-size: 11px;
    font-weight: 600;
    color: var(--color-paper);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 200px;
}

.claim-card-year {
    font-size: 11px;
    color: var(--text-muted);
    background: rgba(255,255,255,0.06);
    padding: 1px 6px;
    border-radius: 4px;
}

.claim-card-text {
    font-size: 13px;
    line-height: 1.55;
    color: var(--text-primary);
    margin-bottom: 10px;
}

.claim-card-meta {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
}

.claim-confidence {
    font-size: 11px;
    color: var(--text-muted);
    margin-left: auto;
}

.claims-vs-divider {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 10px 0;
    padding: 0 4px;
}

.vs-line {
    flex: 1;
    height: 1px;
    background: var(--border-glass);
}

.vs-badge {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    padding: 3px 10px;
    border: 1px solid;
    border-radius: 100px;
    white-space: nowrap;
}

.source-chunk-details {
    margin-top: 8px;
}

.source-chunk-details summary {
    font-size: 11px;
    color: var(--text-muted);
    cursor: pointer;
    user-select: none;
    padding: 4px 0;
}

.source-chunk-details summary:hover {
    color: var(--text-secondary);
}

.source-chunk-text {
    font-size: 12px;
    font-style: italic;
    opacity: 0.7;
    margin-top: 6px;
    padding: 8px;
    background: rgba(255,255,255,0.03);
    border-radius: var(--radius-sm);
    border-left: 2px solid var(--border-glass);
}

/* Edge type badges */
.edge-badge {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.06em;
    padding: 3px 10px;
    border-radius: 100px;
    border: 1px solid transparent;
}

.edge-type-contradicts {
    background: rgba(255, 68, 68, 0.15);
    color: var(--color-contradiction);
    border-color: rgba(255, 68, 68, 0.3);
}

.edge-type-supports {
    background: rgba(0, 255, 136, 0.12);
    color: var(--color-finding);
    border-color: rgba(0, 255, 136, 0.25);
}

.edge-type-extends {
    background: rgba(74, 158, 255, 0.12);
    color: var(--color-paper);
    border-color: rgba(74, 158, 255, 0.25);
}

.edge-type-replicates,
.edge-type-refines {
    background: rgba(107, 114, 128, 0.15);
    color: #9aa0a8;
    border-color: rgba(107, 114, 128, 0.25);
}

/* Loading / error states inside panel */
.panel-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    padding: 40px 20px;
    color: var(--text-muted);
    font-size: 13px;
}

.loading-spinner {
    width: 24px;
    height: 24px;
    border: 2px solid var(--border-glass);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

.panel-error {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 40px 20px;
    color: var(--color-contradiction);
    font-size: 13px;
    text-align: center;
}

.reasoning-text {
    font-size: 13px;
    line-height: 1.6;
    color: var(--text-secondary);
    background: rgba(255, 255, 255, 0.03);
    border-left: 2px solid var(--border-hover);
    padding: 10px 12px;
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}
```

---

## Expected Behavior After Implementation

1. Hover any edge → edge thickens, tooltip shows "contradicts (87%)"
2. Click any edge → side panel opens with loading spinner
3. Panel renders within ~200ms with:
   - Edge type badge at top (red for CONTRADICTS)
   - Strength bar filled to the percentage
   - Reasoning paragraph
   - Source Claim card (paper title in blue, claim text, type/section badges)
   - VS divider with edge type label
   - Target Claim card (same structure)
   - "Source text" collapsible showing the raw extracted chunk
4. Click the ✕ button to close (already implemented in existing panel close handler)

---

## Testing Checklist

- ⬜ Click a CONTRADICTS edge → panel opens, both claims visible, red VS badge
- ⬜ Click a SUPPORTS edge → panel opens, green VS badge
- ⬜ Click a CONTAINS edge → panel should NOT open (CONTAINS edges link Paper→Claim, not Claim→Claim; the Neo4j query will return null → 404 → show error state gracefully)
- ⬜ Hover edge → thickens, tooltip shows type + strength
- ⬜ Mouse leave → edge returns to normal width
- ⬜ Panel loading state visible for slow connections
- ⬜ Panel error state renders if edge_id not found
- ⬜ Source text collapsible works (expand/collapse)
- ⬜ Panel close button still works after edge panel opened
- ⬜ Clicking a node after clicking an edge correctly replaces the panel content

---

## Note on CONTAINS Edges

CONTAINS edges (Paper → Claim) are rendered in the graph but should NOT open the drill-down panel when clicked, because they don't connect two Claims. The `get_edge_with_claims` Cypher query only matches Claim-to-Claim relationships, so it will return null for a CONTAINS edge, and the API will return 404. The `openEdgeDetailPanel` error handler will catch this and show the error state — this is acceptable behavior. Optionally, you can filter CONTAINS edges out of the click handler:

```javascript
.on("click", (event, d) => {
    event.stopPropagation();
    const relType = (d.rel_type || d.type || "").toUpperCase();
    if (relType === "CONTAINS" || relType === "RELATES_TO") return;
    openEdgeDetailPanel(d);
})
```

This is cleaner UX — add this check.
