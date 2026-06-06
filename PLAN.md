# 📋 PLAN.md — Project Vision & Strategy

## Vision

Research Cartographer turns a pile of PDFs into a **living map of human knowledge** — showing not just what researchers found, but how ideas relate, where the field argues with itself, and what questions are still waiting to be asked.

The key insight: most AI tools *summarize* papers. We *reason across* them. The output isn't text — it's a navigable, evolving graph that *updates as you add more papers*.

---

## Why This Wins the Hackathon

### Judging Criteria Alignment

| Criterion | Weight | How We Hit It |
|-----------|--------|---------------|
| Accuracy & Relevance | 20% | Foundry IQ grounds all reasoning in actual paper content — no hallucination |
| Reasoning & Multi-step Thinking | 20% | 4 agents reason in sequence: extract → compare → gap-find → orchestrate |
| Creativity & Originality | 15% | Nobody at 135 projects is building a live, async reasoning graph with A2A |
| User Experience & Presentation | 15% | The animated graph evolution IS the demo — visually unlike anything else |
| Reliability & Safety | 20% | Agent state machine, typed edges, scored confidence, graceful failure handling |
| Community Vote | 10% | The demo video will be uniquely striking — vote-worthy |

### Microsoft Technology Alignment

- **Foundry IQ** — core knowledge base, directly integrated
- **Semantic Scholar API** — used by Gap Finder for novelty scoring (free web grounding)
- **A2A Protocol** — just went GA at Build 2026, we're an early adopter showcase
- **Microsoft Agent Framework 1.0** — GA, production-grade, exactly what judges want to see
- **Azure Container Apps** — deployment stays in the Microsoft ecosystem

---

## What Makes The Demo Unforgettable

The demo video must capture this specific moment:

1. Start with 3 papers already loaded — a modest graph is visible
2. Upload paper #4 — live on screen
3. **The graph starts thinking:** a new paper node appears
4. Claims animate in one by one — new nodes populating
5. Edges re-draw — some existing edges change color (Comparator re-evaluating)
6. A RED edge appears — contradiction detected
7. Two existing OpenQuestion nodes pulse and disappear — resolved
8. One new glowing white node appears — a new gap discovered
9. Click the red edge — side panel shows the agent's full contradiction reasoning

**That 60-second sequence is worth 1000 lines of code.** Everything else serves it.

---

## Scope Decisions

### In Scope (MVP — must have for submission)

- PDF upload (up to 10 papers)
- Extractor Agent — claim extraction
- Comparator Agent — edge detection and typing
- Cartographer Agent — A2A orchestration
- Neo4j graph storage
- FastAPI WebSocket streaming
- D3.js live force graph
- Foundry IQ knowledge base integration
- Basic click-to-inspect side panel

### In Scope (Stretch — add if time allows)

- Gap Finder Agent (open question discovery)
- Semantic Scholar API novelty scoring
- "Tension cluster" visual highlighting
- Paper search within the graph
- Export graph as JSON

### Out of Scope (do not build)

- User authentication
- Multi-user sessions
- Real-time collaboration
- Mobile responsiveness
- Paper recommendations
- Citation import (DOI lookup)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| A2A Protocol setup complexity | Medium | High | Start Day 1, use Discord for help |
| Foundry IQ indexing latency | Medium | Medium | Show "indexing..." state in UI, async |
| Neo4j on Azure setup time | Low | Medium | Use Neo4j AuraDB free tier (instant) |
| D3.js live updates complexity | Medium | High | Build static graph first, add live second |
| Gap Finder quality low | Medium | Low | It's a stretch goal — skip if needed |
| Demo video quality | Low | High | Record on Day 8, full day buffer Day 9 |

---

## Competitive Differentiation

What other submissions likely look like:
- Chat interfaces with RAG
- Document summarizers
- Q&A bots over documents
- Single-agent task runners

What we look like:
- **Multi-agent autonomous reasoning system**
- **Live, animated knowledge graph**
- **Contradiction and gap detection** — not just retrieval
- **A2A protocol** — newest GA Microsoft technology
- **Two IQ layers** — exceeds minimum requirement

---

## 9-Day Build Timeline

| Day | Focus | Definition of Done |
|-----|-------|-------------------|
| 1 | Foundation | Repo up, Foundry IQ KB created, PDF → chunks working |
| 2 | Extractor Agent | Claims extracted from 3 test papers, stored in Neo4j |
| 3 | Comparator Agent | Edges typed and stored, re-evaluation on new paper works |
| 4 | Cartographer + A2A | Full pipeline: PDF in → graph updated, no human steps |
| 5 | FastAPI + WebSocket | Delta events streaming, frontend receives them |
| 6 | D3.js Graph | Static graph renders, click-to-inspect works |
| 7 | Live Updates + Polish | New paper upload → graph animates live |
| 8 | Gap Finder (stretch) + Demo video | Video recorded |
| 9 | Buffer + Submit | Submitted by 11:59 PM PT |

---

## Definition of "Done" for Submission

- [ ] Public GitHub repo with this README
- [ ] All source code present and runnable from README instructions
- [ ] `.env.example` with all required variables (no real values)
- [ ] Demo video uploaded (max 3 minutes)
- [ ] At least Foundry IQ integrated (Semantic Scholar API for web grounding is bonus)
- [ ] A2A protocol used for agent coordination
- [ ] No secrets, PII, or confidential info in repo (see SECURITY.md)
- [ ] No confidential information anywhere (see Microsoft DISCLAIMER)
