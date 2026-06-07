# 🗺️ Research Cartographer

> An autonomous multi-agent system that ingests scientific papers and builds a dynamic knowledge graph. It reveals how ideas connect, identifies areas of agreement and conflict, and highlights unanswered questions.

Built for the **[Microsoft Agents League Hackathon](https://aka.ms/agentsleague/aisf)** · June 4–14, 2026
**Track:** Reasoning Agents | **IQ Layers:** Foundry IQ | **Web Grounding:** OpenAlex API | **Protocol:** A2A Protocol

---

## ✨ What It Does

1. **Upload** 1–20 scientific papers (PDF)
2. **Four specialized AI agents** coordinate via the **Microsoft Agent Framework A2A Protocol**
3. **Real-time graph visualization:** Nodes and edges animate as agents process information
4. **Discover** semantic connections, contradiction clusters, and open research gaps

---

## 🎬 Demo

> *[Demo video: add before June 14 submission]*

---

## 🚧 Current Build Status

As of **June 6, 2026**:

- ✅ Committed foundation: seed docs, graph schema/manager, delta emitter, base agent, PDF parser, Foundry IQ uploader, Extractor, Comparator, A2A Cartographer orchestrator, FastAPI backend, D3 frontend, and Gap Finder.
- ✅ Frontend UI polish: upgraded to Font Awesome vector icons, sleek animations, Limitations tracking, and legend integration.
- ✅ Web Grounding: Gap Finder fully wired to the free OpenAlex API for novelty scoring (replacing Semantic Scholar due to rate limits).
- ✅ Agent Coordination: Fully implemented the Microsoft Agent Framework A2A Protocol for orchestration.
- ⬜ External setup pending: Azure resource group, Foundry IQ knowledge base, Azure OpenAI deployment, Neo4j AuraDB credentials.

### Caveat Resolution Plan

| Caveat | Solution |
|--------|----------|
| Local imports fail without dependencies | Create a virtual environment, install pinned `requirements.txt`, then run import and FastAPI smoke tests. |
| Web IQ novelty scoring is in limited access | Replaced with free OpenAlex API in `GapFinderAgent` for web grounding and novelty scoring. |
| Neo4j/Foundry tests are not run | Populate `.env` locally only, initialize Neo4j constraints, upload one real PDF, and verify chunks/claims/edges. |
| Browser/WebSocket QA is pending | Run the FastAPI app locally, open `http://localhost:8000`, upload a PDF, and verify deltas animate without full graph re-fetches. |
| JS syntax check via shell was blocked | Validate the frontend through the browser/devtools or an approved Node runtime once dependencies are installed. |

---

## 🏗️ Architecture at a Glance

```
PDF Upload ──→ Foundry IQ Knowledge Base ──→ Multi-Agent Reasoning Layer
                                                       │
                              ┌────────────────────────┼────────────────────────┐
                              ↓                        ↓                        ↓
                         Extractor              Comparator               Gap Finder
                         (claims)               (edges)                  (white space)
                              └────────────────────────┼────────────────────────┘
                                                       ↓
                                              Cartographer (A2A Orchestrator)
                                                       │
                                                       ↓
                                          Neo4j Graph Database
                                                       │
                                                       ↓
                                    FastAPI WebSocket (delta streaming)
                                                       │
                                                       ↓
                                      D3.js Force-Directed Live Graph
```

---

## 🤖 The Four Agents

| Agent | Role | Tools |
|-------|------|-------|
| 🔍 **Extractor** | Pulls claims, methodology, and findings from each paper section | `read_chunk`, `write_claim`, `tag_methodology` |
| ⚖️ **Comparator** | Cross-references claims across all papers, labels edges | `query_foundry_iq`, `semantic_diff`, `write_edge` |
| 🔭 **Gap Finder** | Identifies unanswered questions, scores novelty via OpenAlex API | `query_all_claims`, `cross_reference_web`, `score_novelty` |
| 🗺️ **Cartographer** | A2A orchestrator that coordinates agents and maintains graph state | A2A protocol, `update_graph`, `trigger_reanalysis` |

---

## ⚡ The Async Magic

When you upload a new paper:
- The graph updates dynamically: nodes appear, edges animate, and contradictions glow red.
- The Comparator **re-evaluates existing edges** automatically.
- The Gap Finder **rescores open questions**, resolving existing ones and finding new ones.
- Every delta is **streamed live** via WebSocket without page reloads.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent Framework | Microsoft Agent Framework 1.0 (GA, Build 2026) |
| Agent Coordination | Microsoft Agent Framework 1.0 A2A Protocol |
| Knowledge Base | Azure AI Foundry IQ |
| Web Grounding | OpenAlex API |
| Graph Database | Neo4j |
| Backend | FastAPI + asyncio + WebSockets |
| Frontend | D3.js v7 + custom CSS |
| PDF Parsing | PyMuPDF + pdfplumber |
| Embeddings | Azure OpenAI `text-embedding-3-large` |
| Deployment | Azure Container Apps |

---

## 🚀 Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/research-cartographer
cd research-cartographer
cp .env.example .env
# Edit .env with your credentials (NEVER commit .env)
pip install -r requirements.txt
uvicorn src.api.main:app --reload
```

Open `http://localhost:8000`.

---

## 📁 Project Structure

```
research-cartographer/
├── src/
│   ├── agents/
│   │   ├── extractor.py       # Claim extraction agent
│   │   ├── comparator.py      # Cross-paper edge detection agent
│   │   ├── gap_finder.py      # Open question discovery agent
│   │   └── cartographer.py    # A2A orchestrator agent
│   ├── ingestion/
│   │   └── pdf_parser.py      # PDF → chunks → Foundry IQ
│   ├── graph/
│   │   └── graph_manager.py   # Neo4j interface + graph operations
│   ├── api/
│   │   └── main.py            # FastAPI app + WebSocket endpoints
│   └── frontend/
│       ├── index.html
│       ├── graph.js           # D3.js force graph + live updates
│       └── styles.css
├── tests/
├── docs/
├── .env.example               # Template (no real values)
├── requirements.txt
├── README.md
├── AGENTS.md                  # 🤖 Instructions for AI coding agents
├── PLAN.md                    # Full project vision and strategy
├── TODO.md                    # Granular task breakdown
├── ARCHITECTURE.md            # Deep technical spec
├── CHALLENGES.md              # Known hard problems + approaches
├── CONTEXT.md                 # Hackathon rules, judging, links
├── SECURITY.md                # What NEVER to commit (read before pushing)
└── CONVENTIONS.md             # Code style and naming rules
```

---

## 🏆 Hackathon Details

- **Event:** [Agents League @ AISF 2026](https://aka.ms/agentsleague/aisf)
- **Submission deadline:** June 14, 2026 · 11:59 PM PT
- **Track:** Reasoning Agents (Microsoft Foundry)
- **IQ Requirement:** Foundry IQ (meets minimum of 1) + OpenAlex API for web grounding
- **Prize pool:** $55,000 USD total

---

## ⚠️ Security Notice

This is a **public repository**. Never commit secrets, API keys, credentials, or personal data.
See [SECURITY.md](SECURITY.md) before every push.

---

## 📄 License

MIT © 2026: See [LICENSE](LICENSE)
