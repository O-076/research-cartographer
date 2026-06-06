"""Graph query endpoints and WebSocket delta stream."""

import logging

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect

from src.api.models import GraphResponse, PaperStatusResponse, PIPELINE_PROGRESS

logger = logging.getLogger(__name__)

router = APIRouter(tags=["graph"])


# ---------------------------------------------------------------------------
# REST — full graph snapshot
# ---------------------------------------------------------------------------

@router.get("/graph", response_model=GraphResponse)
async def get_graph(request: Request) -> GraphResponse:
    """Return the full knowledge graph for the initial frontend load.

    After this initial fetch the frontend relies exclusively on
    WebSocket delta events — it should never re-fetch /graph.
    """
    graph_manager = request.app.state.graph_manager
    snapshot = await graph_manager.get_full_graph()

    # Separate OpenQuestion nodes from regular nodes
    questions: list[dict] = []
    nodes: list[dict] = []
    for node in snapshot.get("nodes", []):
        if node.get("label") == "OpenQuestion":
            questions.append(node)
        else:
            nodes.append(node)

    return GraphResponse(
        nodes=nodes,
        edges=snapshot.get("edges", []),
        questions=questions,
    )


# ---------------------------------------------------------------------------
# REST — per-paper pipeline status
# ---------------------------------------------------------------------------

@router.get("/paper/{paper_id}/status", response_model=PaperStatusResponse)
async def get_paper_status(request: Request, paper_id: str) -> PaperStatusResponse:
    """Return the current pipeline status for a given paper."""
    graph_manager = request.app.state.graph_manager
    paper = await graph_manager.get_paper(paper_id)

    if paper is None:
        raise HTTPException(status_code=404, detail=f"Paper {paper_id} not found.")

    status = paper.get("status", "unknown")
    progress = PIPELINE_PROGRESS.get(status, 0.0)

    return PaperStatusResponse(
        paper_id=paper_id,
        status=status,
        progress_pct=progress,
    )


# ---------------------------------------------------------------------------
# WebSocket — live graph delta stream
# ---------------------------------------------------------------------------

@router.websocket("/ws/graph")
async def ws_graph(websocket: WebSocket) -> None:
    """Subscribe a client to real-time graph delta events.

    The server sends deltas; the client does not send meaningful messages
    but we keep the receive loop alive to detect disconnects.
    """
    emitter = websocket.app.state.emitter

    await websocket.accept()
    await emitter.subscribe(websocket)
    logger.info(
        "WebSocket client connected",
        extra={"subscriber_count": emitter.subscriber_count},
    )

    try:
        # Keep the connection alive — wait for the client to close it
        while True:
            # recv keeps the task alive; we ignore incoming data
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected normally")
    except Exception:
        logger.exception("WebSocket error")
    finally:
        await emitter.unsubscribe(websocket)
        logger.info(
            "WebSocket client unsubscribed",
            extra={"subscriber_count": emitter.subscriber_count},
        )
