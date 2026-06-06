# 🏆 CONTEXT.md — Hackathon Context & Constraints

> AI agents: this file gives you the full context of WHY this project exists and the external constraints it must satisfy. Every technical decision in this repo exists to win this hackathon.

---

## The Event

**Agents League Hackathon @ Microsoft AI Skills Fest 2026**
- Hosted by: Microsoft
- Dates: June 4–14, 2026
- Registration deadline: June 12, 2026, 12:00 PM PT
- Submission deadline: **June 14, 2026, 11:59 PM PT** ← hard deadline, no extensions
- Prize pool: **$55,000 USD**
- Open to: everyone, all skill levels

---

## Our Track: Reasoning Agents

Build intelligent agents using **Microsoft Foundry** that solve complex problems through multi-step reasoning.

**Key constraint:** All submissions must integrate at least one Microsoft IQ layer.
**Our integration:** Foundry IQ (primary) + Semantic Scholar API (secondary for web grounding) — we exceed the minimum.

---

## Microsoft IQ Layers (Required Integration)

| IQ Layer | What It Is | How We Use It |
|----------|-----------|---------------|
| **Foundry IQ** | Managed knowledge layer — connects enterprise data for agentic retrieval | Primary knowledge base for all paper content; agents query it for grounded answers |
| **Work IQ** | Microsoft 365 intelligence — emails, meetings, documents | Not used (enterprise focus, not relevant to our use case) |
| **Fabric IQ** | Semantic layer for structured business data | Not used (our data is unstructured PDFs) |
| **Semantic Scholar API** | Real-time web grounding | Gap Finder uses it to verify novelty of discovered research gaps |

---

## Judging Rubric

Projects are scored by Microsoft experts and product teams:

| Criterion | Weight | What Judges Look For |
|-----------|--------|---------------------|
| Accuracy & Relevance | 20% | Does it actually meet the challenge requirements? Does the IQ integration work correctly? |
| Reasoning & Multi-step Thinking | 20% | Is there clear, explainable multi-step reasoning? Can you trace how the agent reached its conclusion? |
| Creativity & Originality | 15% | Is this novel? Does it do something unexpected? |
| User Experience & Presentation | 15% | Is the demo polished, clear, and compelling? Is the README good? |
| Reliability & Safety | 20% | Does it handle errors gracefully? Are there obvious failure modes? Is the code solid? |
| Community Vote | 10% | Discord poll — share project in Discord for votes |

**Total: 100%**

Note: 90% is judge-decided, 10% is community vote. Both matter.

---

## Submission Requirements

From the official README:

1. ✅ Repository must be **public** on GitHub
2. ✅ Repository must include a **README.md**
3. ✅ Must include a **demo video**
4. ✅ Must integrate at least **one Microsoft IQ layer**
5. ✅ Read and comply with [DISCLAIMER](https://aka.ms/AgentsLeague_Disclaimer)
6. ✅ Follow [Code of Conduct](https://aka.ms/AgentsLeagueCodeofConduct)
7. ✅ No confidential information in the repo

---

## Live Coding Battles (Watch for Inspiration)

These are Microsoft Reactor livestreams showing how experts approach each track:

| Date | Track | Link |
|------|-------|------|
| Tue June 9, 9 AM PT | 🎨 Creative Apps | [Microsoft Reactor](https://aka.ms/agentsleague/aisf/battles) |
| Wed June 10, 9 AM PT | 🧠 Reasoning Agents ← **our track** | [Microsoft Reactor](https://aka.ms/agentsleague/aisf/battles) |
| Thu June 11, 9 AM PT | 💼 Enterprise Agents | [Microsoft Reactor](https://aka.ms/agentsleague/aisf/battles) |

**Watch the June 10 battle.** It may reveal patterns judges reward.

---

## Community & Support

- **Discord:** [Agents League Arena](https://aka.ms/agentsleague/discord) — ask questions, share progress, vote for others
- **Foundry Forum:** [Microsoft Foundry Developer Forum](https://aka.ms/foundry/forum) — for API/SDK errors
- **IQ Series Learning:** [aka.ms/iq-series](https://aka.ms/iq-series) — video episodes + notebooks

---

## Key Policies

| Policy | Link | What It Means For Us |
|--------|------|---------------------|
| Disclaimer | [DISCLAIMER.md](DISCLAIMER.md) | No secrets/PII/confidential info in the public repo |
| Code of Conduct | [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | Be professional in Discord and commit messages |
| Official Rules | [OFFICIAL_RULES.md](OFFICIAL_RULES.md) | Read before submitting |
| Security | [SECURITY.md](SECURITY.md) | How to report security issues in the submission |

---

## What We Know About the Competition

As of June 5, 2026:
- **135 projects** submitted so far
- Common patterns in similar hackathons: chat interfaces, document Q&A bots, single-agent task runners
- **Our differentiation:** multi-agent A2A coordination + live animated graph + contradiction/gap detection

---

## Important Links

- Hackathon registration: [aka.ms/agentsleague/aisf](https://aka.ms/agentsleague/aisf)
- Foundry IQ docs: [learn.microsoft.com/azure/foundry/agents/concepts/what-is-foundry-iq](https://learn.microsoft.com/azure/foundry/agents/concepts/what-is-foundry-iq)
- Web IQ docs: [learn.microsoft.com](https://learn.microsoft.com/azure/foundry) (Note: Not publicly available yet, swapped for Semantic Scholar)
- Agent Framework: [aka.ms/agentframework](https://aka.ms/agentframework)
- A2A Protocol: [aka.ms/a2a](https://aka.ms/a2a)
- IQ Series GitHub: [github.com/microsoft/iq-series](https://github.com/microsoft/iq-series)
- Build 2026 announcements: [github.com/microsoft/Build26-news](https://github.com/microsoft/Build26-news)
