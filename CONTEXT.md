# CONTEXT.md - Hackathon Context

> AI agents: this file gives you the external constraints and requirements the project must satisfy.
> Every technical decision in this repo exists to produce a strong submission for this event.

---

## The Event

**Agents League Hackathon @ Microsoft AI Skills Fest 2026**
- Hosted by: Microsoft
- Dates: June 4-14, 2026
- Submission deadline: **June 14, 2026, 11:59 PM PT**
- Prize pool: $55,000 USD
- Open to everyone

---

## Our Track: Creative Apps

Build innovative creative applications using AI-assisted development with GitHub Copilot.

**Three required elements:**

1. **GitHub Copilot usage** - meaningful use during development, documented in the README
2. **Microsoft IQ integration** - at least one IQ layer (we use Foundry IQ)
3. **Creative application** - novel concept, clear user value, thoughtful UX

There is no required scenario for this track. Application type is open.

---

## Our IQ Integration

**Foundry IQ** - the primary knowledge layer for all agents.

Paper chunks are indexed into a Foundry IQ knowledge base on upload. Every agent query goes through Foundry IQ to retrieve grounded context from the actual documents. This prevents hallucination and ensures all reasoning is traceable back to specific source material.

OpenAlex API is used by the Gap Finder for novelty scoring of discovered research gaps. Web IQ was evaluated but access was unavailable during the build period.

---

## Judging Rubric

Projects are scored by Microsoft experts and product teams:

| Criterion | Weight | What judges look for |
|-----------|--------|---------------------|
| Accuracy & Relevance | 20% | Meets track requirements, IQ integration works correctly |
| Reasoning & Multi-step Thinking | 20% | Clear multi-step logic, explainable agent decisions |
| Creativity & Originality | 15% | Novel concept, unexpected execution |
| User Experience & Presentation | 15% | Polished, clear, compelling demo |
| Reliability & Safety | 20% | Graceful error handling, no obvious failure modes |
| Community vote | 10% | Discord poll |

---

## Submission Requirements

From the official rules:

- Repository must be **public** on GitHub
- Must include a **README.md**
- Must include a **demo video**
- Must integrate at least **one Microsoft IQ layer**
- Must document **GitHub Copilot usage**
- No confidential information in the repo (see DISCLAIMER and SECURITY.md)
- Follow the Code of Conduct

---

## Key Links

| Resource | Link |
|----------|------|
| Hackathon registration | https://aka.ms/agentsleague/aisf |
| Discord | https://aka.ms/agentsleague/discord |
| Foundry IQ docs | https://learn.microsoft.com/azure/foundry/agents/concepts/what-is-foundry-iq |
| IQ Series learning | https://aka.ms/iq-series |
| Live battles (Creative Apps) | https://aka.ms/agentsleague/aisf/battles (June 9, 9 AM PT) |
| FAQ and rules | https://aka.ms/AgentsLeagueFAQ |

---

## Competitive Context

As of June 11, 2026, over 300 projects have been submitted. Most submissions in the Creative Apps track are chat interfaces, content generators, and single-agent tools.

Research Cartographer differentiates itself through:
- A live animated knowledge graph that updates as agents process each paper
- Multiple coordinated agents reasoning across documents rather than within a single prompt
- Deeply interactive features: contradiction drill-down, claim verification, thread tracing
- A tangible output: APA-formatted literature review downloadable as a Word document

---

## Policies

| Policy | Link |
|--------|------|
| Disclaimer | DISCLAIMER.md |
| Code of Conduct | CODE_OF_CONDUCT.md |
| Official Rules | OFFICIAL_RULES.md |
| Security | SECURITY.md |
