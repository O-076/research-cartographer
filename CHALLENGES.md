# ⚠️ CHALLENGES.md: Known Hard Problems & Approaches

> This file documents the hard technical problems anticipated in this project.
> AI agents: read this before attempting to solve any of these problems independently.
> The approaches below are pre-decided (follow them).

---

## Challenge 1: Claim Deduplication Across Chunked Text

**Problem:** Papers are split into overlapping chunks. The same claim can appear in multiple chunks, leading to duplicate `Claim` nodes.

**Approach:**
- After extracting claims from a chunk, compute embeddings for each
- Before writing to Neo4j, query existing claims for the same paper
- Skip if cosine similarity > 0.95 against any existing claim
- Use `text-embedding-3-large` embeddings stored on each `Claim` node

**Do NOT:** Try to deduplicate with string matching (paraphrases will slip through).

---

## Challenge 2: O(n²) Comparator Scaling

**Problem:** Comparing every claim against every other claim is quadratic. With 10 papers × 20 claims = 200 claims → 19,900 pairs. This is too expensive for real-time LLM comparison.

**Approach:**
- Embedding pre-filter: only compare pairs with cosine similarity > 0.60
- Batch the surviving pairs into groups of 10 for the LLM (ask it to compare multiple pairs in one prompt)
- Cap Comparator runs at 500 LLM calls total (if exceeded, sample randomly)

**Do NOT:** Try to compare all pairs with the LLM directly.

---

## Challenge 3: WebSocket Connection Management

**Problem:** FastAPI WebSocket connections die silently. Emitting to a dead connection throws an exception that can kill the emitter loop.

**Approach:**
- Wrap every `ws.send_text()` in try/except
- Collect dead connections in a list
- Remove dead connections after the emit loop (not during)
- See `DeltaEmitter` in ARCHITECTURE.md for the exact pattern

**Do NOT:** Remove connections during iteration (this causes index errors).

---

## Challenge 4: D3.js Simulation Jank on Live Updates

**Problem:** Adding nodes/edges to a running D3.js force simulation causes the graph to jump and re-layout aggressively, which looks broken.

**Approach:**
- After every delta update, call `simulation.alpha(0.3).restart()` (do not use `1.0`)
- New nodes enter at the position of their connected node (not random)
- Use `simulation.alphaDecay(0.05)` for slower, smoother settling
- Pin the Paper nodes at fixed positions (they're the anchors)

**Do NOT:** Call `simulation.restart()` without setting alpha. It defaults to 1.0 and causes a full re-layout.

---

## Challenge 5: A2A Protocol Setup Complexity

**Problem:** Microsoft Agent Framework A2A is new (GA at Build 2026). Documentation may be sparse and examples are few.

**Resolution:**
- We successfully integrated the Microsoft Agent Framework A2A Protocol for all agent orchestration.
- The fallback `asyncio` task chain was completely removed in favor of proper A2A dispatching.

---

## Challenge 6: Foundry IQ Indexing Latency

**Problem:** After uploading chunks to Foundry IQ, there's an indexing delay before they're queryable. Agents querying immediately after upload may get empty results.

**Approach:**
- After upload, poll `GET /knowledge-base/{id}/status` until status is `ready`
- Implement with exponential backoff: 2s, 4s, 8s, 16s, 32s, then fail
- Show "Indexing paper..." status to the user via WebSocket event during this wait
- This is normal and expected. Do not treat it as an error

---

## Challenge 7: Section Detection in PDFs

**Problem:** Not all PDFs use standard section headers. Academic PDFs vary wildly in structure (two-column, no headers, scanned images).

**Approach:**
- Attempt regex-based section detection first (common patterns: "Abstract", "1. Introduction", "Methods", "Results", etc.)
- If section detection fails: use sliding window chunks with `section="unknown"`
- Never fail hard: a paper without section metadata is still valid
- For image-based/scanned PDFs: log a warning and skip (out of scope)

---

## Challenge 8: LLM Hallucination in Claim Extraction

**Problem:** The Extractor LLM may invent claims not actually in the paper.

**Approach:**
- Always include the source chunk text in the claim object
- Before writing, verify: does the claim text appear semantically in the source chunk? (embedding similarity check)
- Discard claims with source similarity < 0.50
- Surface `confidence` score in the UI side panel so users can see low-confidence claims

---

## Challenge 9: Neo4j AuraDB Free Tier Limits

**Problem:** AuraDB free tier has node/relationship limits (~200k nodes, 2.5GB).

**Reality:** We will never hit these limits in a hackathon demo. 10 papers × ~20 claims = 200 nodes. Completely fine.

**If somehow exceeded:** Export to a local Neo4j Docker instance.

---

## Challenge 10: Demo Video Quality

**Problem:** The demo only works well if the graph animation is visually compelling. A laggy, unstyled graph kills the presentation score.

**Approach:**
- Use a dark background (graphs look dramatically better on dark)
- Use the exact color scheme defined in AGENTS.md
- Record with OBS or similar at 1080p 60fps
- Use real papers from the same domain (not random ones) so real contradictions and gaps will appear organically
- Recommended domain for demo: **COVID-19 treatment papers** (many contradictions, well-known to judges) or **transformer architecture papers** (judges will recognize the concepts)

---

## Challenge 11: API Rate Limits on Shared IPs

**Problem:** The free Semantic Scholar API heavily rate-limits requests originating from shared cloud IPs (like those used in Hackathon cloud dev environments), resulting in constant `429 Too Many Requests` errors during Web Grounding.

**Resolution:**
- We migrated from Semantic Scholar to the **OpenAlex API** for the Gap Finder agent.
- OpenAlex provides a highly generous "polite pool" (via a `mailto` parameter) that completely bypassed the IP rate-limiting issues while providing identical (and often superior) web grounding metadata.
