# Next Agent Prompt

You are continuing Research Cartographer in `C:\Users\OMAR\Desktop\Microsoft Student Ambassador\Hackathon\research-cartographer`.

Before editing, read these in order: `AGENTS.md`, `ARCHITECTURE.md`, `CHALLENGES.md`, `CONVENTIONS.md`, `SECURITY.md`, `PLAN.md`, `TODO.md`, and this file.

## Current State

- Latest committed work:
  - `686af3b feat(ingestion): add pdf parsing foundation`
  - `8ba31cf feat(agents): add extractor and comparator agents`
- Existing committed foundation includes graph schema/manager, delta emitter, base agent, ingestion, extractor, and comparator.
- Current working tree still contains uncommitted WIP files:
  - `src/agents/cartographer.py`
  - `src/agents/gap_finder.py`
  - `src/api/main.py`
  - `src/api/models.py`
  - `src/api/routes/upload.py`
  - `src/api/routes/graph.py`
  - `src/frontend/index.html`
  - `src/frontend/graph.js`
  - `src/frontend/styles.css`
- `TODO.md` has been updated to reflect this accurately: Day 4 and Day 8 are in progress where A2A/Web IQ are incomplete; Day 5 and Day 6 code scaffolds exist but still need runtime/browser verification.

## Important Caveats

- Do not mark live tests complete unless you actually run them.
- Do not stage `.env` or any secrets.
- Do not change pinned versions in `requirements.txt`.
- The current `CartographerAgent` is an async orchestrator, but true Microsoft Agent Framework A2A setup is still missing.
- The current `GapFinderAgent` uses deterministic placeholder novelty scoring; Web IQ is not implemented.
- `src/frontend/graph.js` must keep live delta restarts at `simulation.alpha(0.3).restart()`.
- Comparator threshold must stay `>0.60` with 10-pair batches and a 500-call cap.

## Recommended Next Work

1. Inspect the uncommitted Day 4-6 WIP files.
2. Run `python -m compileall .\src`.
3. Fix any runtime issues in Cartographer/API/frontend without broad refactors.
4. Decide on A2A:
   - Implement Microsoft Agent Framework A2A if feasible.
   - If not feasible quickly, document the temporary async fallback clearly in `README.md` and `TODO.md`, per `CHALLENGES.md`.
5. Commit in coherent slices:
   - `feat(orchestrator): add cartographer pipeline orchestration`
   - `feat(api): add graph streaming backend`
   - `feat(frontend): add live d3 graph interface`
6. Leave Gap Finder as in-progress until Web IQ novelty scoring is real or the placeholder is explicitly accepted for the demo.

## Verification Checklist Before Any Commit

- `python -m compileall .\src` passes.
- Search for forbidden blocking calls: `rg -n "time\.sleep|requests|threading" .\src`
- Search for obvious secrets in changed source.
- Run `git diff --cached` before committing.
- Update only the specific `TODO.md` lines that the commit truly completes.

## Suggested Immediate Command Sequence

```powershell
git status --short
python -m compileall .\src
rg -n "time\.sleep|requests|threading" .\src
```
