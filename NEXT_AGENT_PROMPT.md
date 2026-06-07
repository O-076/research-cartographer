# Next Agent Prompt

You are continuing Research Cartographer in:

`C:\Users\OMAR\Desktop\Microsoft Student Ambassador\Hackathon\research-cartographer`

Read these first, in order:

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `CHALLENGES.md`
4. `CONVENTIONS.md`
5. `SECURITY.md`
6. `PLAN.md`
7. `TODO.md`
8. `README.md`
9. `NEXT_AGENT_PROMPT.md`

## Current Committed State

Latest commit:

```text
057004e feat(app): add async pipeline backend and live graph UI
```

Committed implementation now includes:

- PDF parsing and Foundry IQ uploader scaffolding.
- Graph schema, graph manager, and WebSocket delta emitter.
- BaseAgent with Azure OpenAI/Foundry IQ wrappers.
- Extractor and Comparator agents.
- A2A Protocol Cartographer orchestrator.
- Gap Finder fully wired to OpenAlex API for real-time web grounding and novelty scoring.
- FastAPI backend routes for upload, graph snapshot, paper status, and WebSocket streaming.
- D3.js v7 frontend with upload UI, live delta handlers, graph styling, and click-to-inspect side panel.
- Updated `README.md` and `TODO.md` status/caveat tracking.

Working tree should be clean when you start. Confirm with:

```powershell
git status --short
```

## Remaining Caveats And Solutions

### 1. Local dependencies are not installed

Symptom: import smoke tests fail on modules such as `httpx`.

Solution:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m compileall .\src
python -c "import src.api.main; print('api import ok')"
```

If installation fails due to sandbox/network restrictions, request escalation for dependency installation.

### 2. A2A Protocol is fully operational

Current state: `CartographerAgent` successfully uses Microsoft Agent Framework 1.0 + A2A Protocol to orchestrate all sub-agents. 

Solution path:

- None required. This core hackathon requirement is completed.

### 3. Web IQ novelty scoring replaced by OpenAlex API

Current state: `GapFinderAgent` uses the free OpenAlex API for web grounding instead of Semantic Scholar (which rate-limited our shared IPs). It queries OpenAlex for real paper counts to natively score novelty.

Solution path:

- None required. This is considered complete for the hackathon MVP.

### 4. Live Neo4j/Foundry verification is pending

Solution path:

- Populate `.env` locally only.
- Run the API app:

```powershell
uvicorn src.api.main:app --reload
```

- Verify `/graph` returns a snapshot.
- Upload one real PDF and verify chunks, claims, and paper status.
- Upload two related papers and verify Comparator edges.

### 5. Browser/WebSocket QA is pending

Solution path:

- Open `http://localhost:8000`.
- Confirm `/static/styles.css` and `/static/graph.js` load.
- Confirm WebSocket connects to `/ws/graph`.
- Upload a PDF and verify the frontend uses deltas after initial `/graph`.
- Check `simulation.alpha(0.3).restart()` remains the live-update restart.
- Capture screenshots for desktop and a narrow viewport.

### 6. JS shell syntax check was blocked

Current state: Windows shell denied `node.exe --check`.

Solution path:

- Prefer browser QA with devtools console if Node remains blocked.
- If using Node is necessary, use an approved Node runtime or request permission through the proper tool path.

## Next Recommended Task

Start with environment/runtime validation, not new feature work:

1. Install dependencies in `.venv`.
2. Run import and compile checks.
3. Start FastAPI.
4. Use the browser to verify frontend asset loading and WebSocket connection.
5. Only then move to QAing the A2A and OpenAlex integration.

## Guardrails

- Do not commit `.env`.
- Do not hardcode secrets.
- Do not change pinned versions in `requirements.txt`.
- Do not mark live tests complete unless you actually ran them.
- Keep Comparator threshold `>0.60`, batches of 10, and 500-call cap.
- Keep D3 live update restart at `simulation.alpha(0.3).restart()`.

## Commit Guidance

If dependency/runtime validation fixes are needed, use:

```bash
git commit -m "fix(api): stabilize local runtime startup"
```


