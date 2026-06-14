# Research Cartographer

**Upload papers. Watch knowledge think.**

Research Cartographer takes scientific PDFs and turns them into a live knowledge graph. Four AI agents run in sequence per paper: one extracts structured claims, one compares them against every existing claim, and one identifies research gaps. A fourth agent orchestrates the pipeline and streams each step to the browser over a WebSocket. Every new paper causes the graph to re-evaluate itself in real time.

Built for the **Microsoft Agents League Hackathon 2026**, Creative Apps track.

---

## Demo

[![Research Cartographer Demo](https://img.youtube.com/vi/wnj3TmWvWkQ/maxresdefault.jpg)](https://youtu.be/wnj3TmWvWkQ)

---

## What it does

**Core pipeline.** Drop in a PDF and the system immediately begins extracting structured claims, comparing them against everything already in the graph, and streaming updates to your browser via WebSocket. The graph visibly thinks as each agent finishes its work.

**Contradiction detection.** When two papers disagree, the edge between their claims turns red. Click that edge and a panel opens showing both claims side by side, the source text each was drawn from, and the agent's full reasoning for why it flagged the conflict.

**Field consensus meter.** Click any claim node to see a percentage bar showing how much of the corpus agrees with that claim, broken down by supporting, disputing, and extending relationships. An "Ask AI to explain" button generates a 2-3 sentence qualitative interpretation grounded in the actual evidence.

**Claim verification.** Press `/` to open a search overlay. Type any statement and the system embeds it, finds the most semantically similar claims across all uploaded papers, and classifies each as supporting, contradicting, or neutral. Results link back to the graph nodes.

**Research thread tracer.** Shift-click two nodes to find the shortest reasoning path connecting them through the graph. The path highlights in the graph and the panel shows a step-by-step chain with an AI-generated narrative explaining the conceptual journey.

**Literature review generator.** One button produces a full APA-formatted literature review synthesized from the entire corpus: thematic sections grouped by concept clusters, explicit discussion of contradictions, and a research gaps section drawn from the graph's open question nodes. Viewable in the browser and downloadable as a `.docx` file.

---

## Architecture

```
PDF upload
  -> Cartographer (pipeline orchestrator)
       -> PyMuPDF parsing + LLM metadata extraction
       -> Foundry IQ knowledge base (chunk indexing)
       -> Extractor Agent (structured claim extraction)
       -> Comparator Agent (cross-paper edge detection)
       -> Gap Finder (open question discovery via OpenAlex)
  -> Neo4j graph database (all writes)
  -> DeltaEmitter -> WebSocket (live event streaming)
  -> D3.js force-directed graph (frontend)
```

The Cartographer runs the three sub-agents in sequence per paper. Each agent writes to Neo4j and emits delta events so the frontend updates as the pipeline progresses.

---

## Microsoft IQ Integration

**Foundry IQ** serves as the knowledge base for every agent query. Paper chunks are indexed on upload and all claim extraction, comparison, and gap-finding queries are grounded in the actual document content rather than generated from model memory. This is what keeps the reasoning accurate rather than associative.

---

## GitHub Copilot

This project was built using AI-assisted development throughout. GitHub Copilot accelerated the implementation of the FastAPI routes, D3.js force simulation, Neo4j Cypher queries, and python-docx generation. The agentic pipeline architecture and WebSocket streaming layer were developed iteratively with Copilot suggestions guiding the implementation of each component.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Knowledge base | Azure AI Foundry IQ |
| LLM | Azure OpenAI (o4-mini) |
| Embeddings | Azure OpenAI text-embedding-3-small |
| Web grounding | OpenAlex API |
| Graph database | Neo4j AuraDB |
| Backend | FastAPI + asyncio + WebSockets |
| PDF parsing | PyMuPDF + pdfplumber |
| Frontend graph | D3.js v7 |
| Document export | python-docx |
| Deployment | Local / Azure Container Apps |

---

## Getting Started

```bash
git clone https://github.com/YOUR_USERNAME/research-cartographer
cd research-cartographer
cp .env.example .env
# Fill in your credentials in .env - never commit this file
pip install -r requirements.txt
uvicorn src.api.main:app --reload
```

Open `http://localhost:8000`, upload a few PDFs on the same topic, and watch the graph build.

### Required environment variables

See `.env.example` for the full list. You will need:

- Azure AI Foundry IQ endpoint and key
- Azure OpenAI endpoint, key, and deployment names
- Neo4j AuraDB connection URI and credentials

---

## Hackathon

| | |
|---|---|
| Event | [Agents League @ AISF 2026](https://aka.ms/agentsleague/aisf) |
| Track | Creative Apps |
| IQ layer | Foundry IQ |
| Deadline | June 14, 2026 |

---

## Security note

This is a public repository. The `.env` file is gitignored and must never be committed. See `SECURITY.md` for the full checklist before every push.

---

## License

MIT
