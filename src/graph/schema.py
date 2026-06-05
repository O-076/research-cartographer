"""Graph node and edge type definitions for Neo4j.

All node labels, relationship types, and constraint DDL live here.
Import from this module — never redefine schema types elsewhere.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ClaimType(str, Enum):
    """Claim classification types."""

    FINDING = "finding"
    METHOD = "method"
    ASSUMPTION = "assumption"
    LIMITATION = "limitation"


class SectionType(str, Enum):
    """Paper section types used for chunk classification."""

    ABSTRACT = "abstract"
    INTRO = "intro"
    METHODS = "methods"
    RESULTS = "results"
    DISCUSSION = "discussion"
    OTHER = "other"
    UNKNOWN = "unknown"


class EdgeType(str, Enum):
    """Relationship types between claims."""

    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    EXTENDS = "extends"
    REPLICATES = "replicates"
    REFINES = "refines"


class QuestionStatus(str, Enum):
    """Status lifecycle of an open question."""

    OPEN = "open"
    PARTIALLY_ANSWERED = "partially_answered"
    RESOLVED = "resolved"


class PipelineStatus(str, Enum):
    """Per-paper pipeline state machine."""

    QUEUED = "queued"
    EXTRACTING = "extracting"
    CLAIMS_READY = "claims_ready"
    COMPARING = "comparing"
    EDGES_READY = "edges_ready"
    GAP_FINDING = "gap_finding"
    COMPLETE = "complete"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Node dataclasses
# ---------------------------------------------------------------------------

def _new_id() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class Paper:
    """A scientific paper uploaded to the system."""

    id: str
    title: str
    authors: list[str]
    year: int | None = None
    abstract: str = ""
    status: str = PipelineStatus.QUEUED.value
    created_at: datetime = field(default_factory=_utcnow)


@dataclass(frozen=True, slots=True)
class Claim:
    """An extracted factual claim from a paper."""

    id: str = field(default_factory=_new_id)
    paper_id: str = ""
    text: str = ""
    type: str = ClaimType.FINDING.value
    confidence: float = 0.0
    section: str = SectionType.UNKNOWN.value
    embedding: list[float] = field(default_factory=list)
    source_chunk_text: str = ""
    created_at: datetime = field(default_factory=_utcnow)


@dataclass(frozen=True, slots=True)
class Edge:
    """A typed relationship between two claims."""

    id: str = field(default_factory=_new_id)
    source_claim_id: str = ""
    target_claim_id: str = ""
    type: str = EdgeType.SUPPORTS.value
    strength: float = 0.0
    reasoning: str = ""
    created_at: datetime = field(default_factory=_utcnow)


@dataclass(frozen=True, slots=True)
class Concept:
    """An auto-extracted domain concept shared across claims."""

    id: str = field(default_factory=_new_id)
    name: str = ""
    embedding: list[float] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class OpenQuestion:
    """A research gap identified by the Gap Finder agent."""

    id: str = field(default_factory=_new_id)
    question: str = ""
    novelty_score: float = 0.0
    related_claim_ids: list[str] = field(default_factory=list)
    web_evidence: str = ""
    status: str = QuestionStatus.OPEN.value
    created_at: datetime = field(default_factory=_utcnow)


# ---------------------------------------------------------------------------
# Neo4j Cypher DDL — run once on database setup
# ---------------------------------------------------------------------------

NEO4J_CONSTRAINTS: tuple[str, ...] = (
    "CREATE CONSTRAINT paper_id_unique IF NOT EXISTS FOR (p:Paper) REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT claim_id_unique IF NOT EXISTS FOR (c:Claim) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT concept_id_unique IF NOT EXISTS FOR (c:Concept) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT open_question_id_unique IF NOT EXISTS FOR (q:OpenQuestion) REQUIRE q.id IS UNIQUE",
)

NEO4J_INDEXES: tuple[str, ...] = (
    "CREATE INDEX claim_paper_id IF NOT EXISTS FOR (c:Claim) ON (c.paper_id)",
    "CREATE INDEX concept_name IF NOT EXISTS FOR (c:Concept) ON (c.name)",
    "CREATE INDEX question_status IF NOT EXISTS FOR (q:OpenQuestion) ON (q.status)",
)

ALL_NEO4J_DDL: tuple[str, ...] = NEO4J_CONSTRAINTS + NEO4J_INDEXES


# ---------------------------------------------------------------------------
# Serialization helpers (dataclass → Neo4j property dict)
# ---------------------------------------------------------------------------

def paper_to_props(paper: Paper) -> dict:
    """Convert a Paper to a Neo4j property map."""
    return {
        "id": paper.id,
        "title": paper.title,
        "authors": paper.authors,
        "year": paper.year,
        "abstract": paper.abstract,
        "status": paper.status,
        "created_at": paper.created_at.isoformat(),
    }


def claim_to_props(claim: Claim) -> dict:
    """Convert a Claim to a Neo4j property map (embedding stored separately)."""
    return {
        "id": claim.id,
        "paper_id": claim.paper_id,
        "text": claim.text,
        "type": claim.type,
        "confidence": claim.confidence,
        "section": claim.section,
        "embedding": claim.embedding,
        "source_chunk_text": claim.source_chunk_text,
        "created_at": claim.created_at.isoformat(),
    }


def edge_to_props(edge: Edge) -> dict:
    """Convert an Edge to a Neo4j relationship property map."""
    return {
        "id": edge.id,
        "strength": edge.strength,
        "reasoning": edge.reasoning,
        "created_at": edge.created_at.isoformat(),
    }


def concept_to_props(concept: Concept) -> dict:
    """Convert a Concept to a Neo4j property map."""
    return {
        "id": concept.id,
        "name": concept.name,
        "embedding": concept.embedding,
    }


def question_to_props(question: OpenQuestion) -> dict:
    """Convert an OpenQuestion to a Neo4j property map."""
    return {
        "id": question.id,
        "question": question.question,
        "novelty_score": question.novelty_score,
        "related_claim_ids": question.related_claim_ids,
        "web_evidence": question.web_evidence,
        "status": question.status,
        "created_at": question.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Neo4j relationship type mapping
# ---------------------------------------------------------------------------

EDGE_TYPE_TO_NEO4J: dict[str, str] = {
    EdgeType.SUPPORTS.value: "SUPPORTS",
    EdgeType.CONTRADICTS.value: "CONTRADICTS",
    EdgeType.EXTENDS.value: "EXTENDS",
    EdgeType.REPLICATES.value: "REPLICATES",
    EdgeType.REFINES.value: "REFINES",
}
