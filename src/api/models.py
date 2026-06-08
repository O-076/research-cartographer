"""Pydantic request/response models for the Research Cartographer API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# REST response models
# ---------------------------------------------------------------------------

class UploadResponse(BaseModel):
    """Returned by POST /upload after a PDF is accepted."""

    paper_id: str
    status: str = "queued"


class PaperStatusResponse(BaseModel):
    """Returned by GET /paper/{paper_id}/status."""

    paper_id: str
    status: str
    progress_pct: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Estimated pipeline progress percentage.",
    )


class GraphResponse(BaseModel):
    """Returned by GET /graph — the full snapshot of the knowledge graph."""

    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    questions: list[dict[str, Any]] = Field(default_factory=list)


class EdgeDetailResponse(BaseModel):
    """Returned by GET /edge/{edge_id}."""

    edge: dict[str, Any]
    source_claim: dict[str, Any]
    target_claim: dict[str, Any]
    source_paper: dict[str, Any]
    target_paper: dict[str, Any]


# ---------------------------------------------------------------------------
# WebSocket delta event models
# ---------------------------------------------------------------------------

class NodeData(BaseModel):
    """Payload for node_added WebSocket events."""

    id: str
    label: str  # "Paper", "Claim", "Concept", "OpenQuestion"
    paper_id: str | None = None
    text: str | None = None
    type: str | None = None
    confidence: float | None = None
    section: str | None = None
    title: str | None = None
    authors: list[str] | None = None
    year: int | None = None
    abstract: str | None = None
    status: str | None = None


class EdgeData(BaseModel):
    """Payload for edge_added / edge_updated WebSocket events."""

    id: str
    source: str
    target: str
    rel_type: str
    strength: float = 0.0
    reasoning: str = ""


class QuestionData(BaseModel):
    """Payload for question_added WebSocket events."""

    id: str
    question: str
    novelty_score: float = 0.0
    related_claim_ids: list[str] = Field(default_factory=list)
    web_evidence: str = ""
    status: str = "open"


class DeltaEvent(BaseModel):
    """Generic wrapper for any WebSocket delta event."""

    type: str
    data: dict[str, Any]
    timestamp: str


# ---------------------------------------------------------------------------
# Pipeline status → progress mapping
# ---------------------------------------------------------------------------

PIPELINE_PROGRESS: dict[str, float] = {
    "queued": 0.0,
    "extracting": 15.0,
    "claims_ready": 35.0,
    "comparing": 50.0,
    "edges_ready": 70.0,
    "gap_finding": 85.0,
    "complete": 100.0,
    "error": 0.0,
}
