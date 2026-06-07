"""FastAPI application entry point for Research Cartographer.

Start with::

    uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from src.api.limiter import limiter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Resolve project root (repo root) — src/api/main.py → go up 3 levels
_THIS_DIR = Path(__file__).resolve().parent
_SRC_DIR = _THIS_DIR.parent
_PROJECT_ROOT = _SRC_DIR.parent
_FRONTEND_DIR = _SRC_DIR / "frontend"

# ---------------------------------------------------------------------------
# Lifespan — startup & shutdown
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle.

    Startup:
        1. Load .env
        2. Create GraphManager and initialise Neo4j schema
        3. Create DeltaEmitter
        4. Create CartographerAgent
    Shutdown:
        - Close GraphManager (Neo4j driver)
        - Close CartographerAgent HTTP client
    """

    # ── 1. Load environment variables ──────────────────────────────────
    dotenv_path = _PROJECT_ROOT / ".env"
    load_dotenv(dotenv_path)
    logger.info("Loaded .env from %s", dotenv_path)

    # ── 2. GraphManager — Neo4j connection + schema init ───────────────
    from src.graph.graph_manager import GraphManager

    graph_manager = GraphManager.from_env()
    try:
        await graph_manager.initialize()
        logger.info("Neo4j schema initialised")
    except Exception:
        logger.exception(
            "Failed to initialise Neo4j schema — continuing with degraded mode"
        )

    app.state.graph_manager = graph_manager

    # ── 3. DeltaEmitter — WebSocket event fan-out ──────────────────────
    from src.graph.delta_emitter import DeltaEmitter

    emitter = DeltaEmitter()
    app.state.emitter = emitter

    # ── 4. CartographerAgent — orchestrator ────────────────────────────
    try:
        from src.agents.cartographer import CartographerAgent

        cartographer = CartographerAgent(
            graph_manager=graph_manager,
            delta_emitter=emitter,
        )
        logger.info("CartographerAgent created")
    except ImportError:
        logger.warning(
            "CartographerAgent not found — pipeline will not run. "
            "Create src/agents/cartographer.py to enable it."
        )
        cartographer = _StubCartographer()  # type: ignore[assignment]

    app.state.cartographer = cartographer

    # ── Ready ──────────────────────────────────────────────────────────
    logger.info("Research Cartographer API startup complete")

    yield  # ── Application runs here ──

    # ── Shutdown ───────────────────────────────────────────────────────
    logger.info("Shutting down Research Cartographer API")

    if hasattr(cartographer, "close"):
        try:
            await cartographer.close()
        except Exception:
            logger.exception("Error closing CartographerAgent")

    await graph_manager.close()
    logger.info("Neo4j driver closed")


# ---------------------------------------------------------------------------
# Stub cartographer (used when src/agents/cartographer.py is not yet built)
# ---------------------------------------------------------------------------

class _StubCartographer:
    """No-op placeholder so the API can start without the real agent."""

    async def process_paper(self, paper_id: str, pdf_bytes: bytes, **kwargs) -> None:
        logger.warning(
            "StubCartographer.process_paper called — no processing will occur. "
            "Implement src/agents/cartographer.py to enable the pipeline.",
            extra={"paper_id": paper_id},
        )

    async def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Research Cartographer",
    description=(
        "Multi-agent knowledge-graph engine for scientific literature. "
        "Upload PDFs, watch the graph grow in real-time via WebSocket."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS — fixed for security ────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Route modules ─────────────────────────────────────────────────────────
from src.api.routes.upload import router as upload_router  # noqa: E402
from src.api.routes.graph import router as graph_router  # noqa: E402

app.include_router(upload_router)
app.include_router(graph_router)

# ── Static files (frontend assets) ────────────────────────────────────────
# Mount only if the frontend directory has actual files to serve.
if _FRONTEND_DIR.is_dir():
    app.mount(
        "/static",
        StaticFiles(directory=str(_FRONTEND_DIR)),
        name="static",
    )


# ── Root route — serve index.html ─────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def root():
    """Serve the single-page frontend app."""
    index_path = _FRONTEND_DIR / "index.html"
    if index_path.is_file():
        return FileResponse(str(index_path), media_type="text/html")

    # Fallback when frontend is not yet built
    return HTMLResponse(
        content=(
            "<!doctype html><html><head><title>Research Cartographer</title></head>"
            "<body><h1>Research Cartographer</h1>"
            "<p>Frontend not found. Place <code>index.html</code>, "
            "<code>graph.js</code>, and <code>styles.css</code> in "
            "<code>src/frontend/</code>.</p>"
            '<p>API docs: <a href="/docs">/docs</a></p>'
            "</body></html>"
        ),
        status_code=200,
    )


# ---------------------------------------------------------------------------
# Logging configuration (basic — can be replaced with structlog later)
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
