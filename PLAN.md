# PLAN.md — Project Vision and Strategy

## What Research Cartographer is

A tool that takes scientific PDFs and turns them into an interactive, reasoning knowledge graph. The core insight is simple: most tools that work with research papers operate on one document at a time. This system reads across the whole corpus simultaneously, finds where papers agree and disagree, and makes those relationships navigable.

The live graph animation is the demo moment. Upload a paper, and the graph visibly processes it: claim nodes appear, edges animate between them, contradiction clusters light up red, open question nodes emerge. It looks like the system is thinking because it is.

---

## Why this fits Creative Apps

The track rewards novel concept, clear user value, and thoughtful UX. Research Cartographer delivers all three in a way that is immediately visible in a demo video:

- The animated knowledge graph is visually unlike anything else in the submission pool
- The features (contradiction drill-down, consensus meter, claim verification, thread tracing, literature review) each solve a real problem researchers face
- Every feature has a clear "wow moment" that works on camera

---

## Judging alignment

| Criterion | How we hit it |
|-----------|--------------|
| Accuracy & Relevance (20%) | Foundry IQ grounds all reasoning in actual document content. Claims trace to source chunks. |
| Reasoning & Multi-step Thinking (20%) | Four agents coordinate: extract, compare, find gaps, orchestrate. Each step is traceable. |
| Creativity & Originality (15%) | A live reasoning graph is not a chat interface. The visual output is the differentiator. |
| User Experience (15%) | Dark-theme D3.js graph, click-to-inspect, keyboard shortcuts, downloadable .docx output. |
| Reliability & Safety (20%) | Async pipeline with state machine, graceful failure handling, no hardcoded credentials. |
| Community vote (10%) | Demo video will be visually striking enough to win Discord votes. |

---

## Feature set (all complete)

| Feature | What it shows judges |
|---------|---------------------|
| Live graph animation | Creativity, UX |
| Contradiction drill-down | Reasoning, UX |
| Field consensus meter + AI explain | Reasoning, Creativity |
| Claim verification | Reasoning, UX |
| Research thread tracer | Reasoning, Creativity |
| Literature review + .docx | Creativity, UX, practical value |

---

## The demo video is the submission

Code quality, architecture, and feature depth only matter if the demo video communicates them clearly. The video should be 2-3 minutes and follow this sequence:

1. Empty graph state
2. Upload papers one by one, graph animates live
3. Red edges appear between contradicting papers
4. Click a red edge — contradiction panel opens
5. Click a disputed claim — consensus bar, AI explanation
6. Press `/` — verify a statement against the corpus
7. Shift-click two nodes — trace the reasoning chain
8. Click Generate Review — APA review appears, download .docx

Every feature gets one clear moment. No dead time. The graph should be clearly visible throughout.

---

## GitHub Copilot documentation

For the submission, the README includes a section on GitHub Copilot usage covering:
- Code completion for FastAPI routes and Neo4j Cypher queries
- Copilot Chat for debugging WebSocket streaming and D3.js simulation tuning
- Iterative development of the python-docx APA formatting logic

---

## What is not in scope

- User authentication
- Multi-user sessions
- Mobile responsiveness
- Real-time collaboration
- Any features not currently implemented

---

## Submission checklist

- [ ] Public GitHub repo
- [ ] README with demo video link, setup instructions, Copilot documentation
- [ ] Demo video uploaded (YouTube unlisted)
- [ ] `.env` confirmed never committed
- [ ] All `FEATURE_*.md` files deleted
- [ ] Submitted on platform before June 14, 2026 11:59 PM PT
- [ ] Posted in Discord for community vote
