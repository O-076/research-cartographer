"""Graph query endpoints and WebSocket delta stream."""

import logging

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect

from src.api.models import (
    GraphResponse, PaperStatusResponse, PIPELINE_PROGRESS,
    EdgeDetailResponse, ConsensusExplainResponse,
)

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
# REST — edge detail
# ---------------------------------------------------------------------------

@router.get("/edge/{edge_id}", response_model=EdgeDetailResponse)
async def get_edge_detail(
    edge_id: str,
    request: Request,
) -> EdgeDetailResponse:
    """Fetch full details for a relationship: both claims + their papers."""
    graph_manager = request.app.state.graph_manager
    result = await graph_manager.get_edge_with_claims(edge_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Edge {edge_id!r} not found")
    return EdgeDetailResponse(**result)


# ---------------------------------------------------------------------------
# REST — consensus explanation
# ---------------------------------------------------------------------------

@router.get(
    "/claim/{claim_id}/consensus/explain",
    response_model=ConsensusExplainResponse,
)
async def explain_claim_consensus(
    claim_id: str,
    request: Request,
) -> ConsensusExplainResponse:
    """Generate an AI explanation of field consensus for a given claim."""
    graph_manager = request.app.state.graph_manager
    explainer = request.app.state.consensus_explainer

    context = await graph_manager.get_claim_consensus_context(claim_id)
    if context is None:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id!r} not found")

    claim = context["claim"]
    semantic_edges = context["semantic_edges"]

    # Compute consensus_pct server-side (same formula as frontend)
    support_score = sum(
        (e.get("strength") or 0.5) * (0.5 if e["edge_type"] in ("EXTENDS", "REFINES") else 1.0)
        for e in semantic_edges if e["edge_type"] != "CONTRADICTS"
    )
    dispute_score = sum(
        (e.get("strength") or 0.5)
        for e in semantic_edges if e["edge_type"] == "CONTRADICTS"
    )
    total = support_score + dispute_score
    consensus_pct = round((support_score / total) * 100) if total > 0 else None

    explanation = await explainer.explain(
        claim_text=claim["text"],
        paper_title=claim["paper_title"],
        consensus_pct=consensus_pct or 0,
        semantic_edges=semantic_edges,
    )

    return ConsensusExplainResponse(
        claim_id=claim_id,
        explanation=explanation,
        consensus_pct=consensus_pct,
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
