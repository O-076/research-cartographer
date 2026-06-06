# 🗺️ Research Cartographer

> An autonomous multi-agent system that ingests scientific papers and builds a **living, evolving knowledge graph** — revealing how ideas connect, where fields agree, where they conflict, and what questions nobody has asked yet.

Built for the **[Microsoft Agents League Hackathon](https://aka.ms/agentsleague/aisf)** · June 4–14, 2026
**Track:** Reasoning Agents | **IQ Layers:** Foundry IQ + Web IQ | **Protocol:** A2A

---

## ✨ What It Does

1. **Upload** 1–20 scientific papers (PDF)
2. **Four specialized AI agents** coordinate autonomously via Microsoft's A2A protocol
3. **Watch the knowledge graph grow in real-time** — nodes and edges animate as agents reason
4. **Discover** semantic connections, contradiction clusters, and open research gaps

---

## 🎬 Demo

> *[Demo video — add before June 14 submission]*

---

## 🚧 Current Build Status

As of **June 6, 2026**:

- ✅ Committed foundation: seed docs, graph schema/manager, delta emitter, base agent, PDF parser, Foundry IQ uploader, Extractor, and Comparator.
- 🔄 Working tree WIP: Cartographer async orchestrator, FastAPI routes, D3 frontend, and MVP Gap Finder exist but still need review, runtime testing, and focused commits.
- ⬜ External setup pending: Azure resource group, Foundry IQ knowledge base, Azure OpenAI deployment, Neo4j AuraDB credentials, and real `.env` population.
- ⬜ Critical feature gaps: true Microsoft Agent Framework A2A setup, live Foundry IQ/Neo4j verification, Web IQ novelty scoring, WebSocket/browser QA, and end-to-end demo testing.

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
| 🔭 **Gap Finder** | Identifies unanswered questions, scores novelty via Web IQ | `query_all_claims`, `cross_reference_web`, `score_novelty` |
| 🗺️ **Cartographer** | A2A orchestrator — coordinates agents, maintains graph state | A2A protocol, `update_graph`, `trigger_reanalysis` |

---

## ⚡ The Async Magic

When you upload a new paper:
- The graph **visibly thinks** — nodes appear, edges animate, contradictions glow red
- The Comparator **re-evaluates existing edges** — nothing is static
- The Gap Finder **rescores open questions** — some resolve, new ones emerge
- Every delta is **streamed live** via WebSocket — no page reloads

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent Framework | Microsoft Agent Framework 1.0 (GA, Build 2026) |
| Agent Coordination | A2A Protocol |
| Knowledge Base | Azure AI Foundry IQ |
| Web Grounding | Web IQ |
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
# Edit .env with your credentials — NEVER commit .env
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
├── .env.example               # Template — no real values
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
- **IQ Requirement:** Foundry IQ + Web IQ (exceeds minimum of 1)
- **Prize pool:** $55,000 USD total

---

## ⚠️ Security Notice

This is a **public repository**. Never commit secrets, API keys, credentials, or personal data.
See [SECURITY.md](SECURITY.md) before every push.

---

## 📄 License

MIT © 2026 — See [LICENSE](LICENSE)
