"""Agent 2 — Claim Comparator.

After a new paper is ingested, compare its claims against every existing
claim in the graph.  Uses cosine-similarity pre-filtering to avoid
unnecessary LLM calls, then asks the LLM to classify and score the
relationship.

Output: ``AsyncGenerator[Edge, None]``
"""

import logging
import random
import uuid
from collections.abc import AsyncGenerator
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.agents.base_agent import BaseAgent, LLMResponseError
from src.graph.graph_manager import GraphManager
from src.graph.schema import Claim, Edge, EdgeType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Minimum cosine similarity to consider a claim pair worth evaluating
SIMILARITY_THRESHOLD: float = 0.60

# Maximum claim pairs sent in a single LLM call
_MAX_PAIRS_PER_CALL: int = 10

# Maximum total LLM comparison calls per comparator run
_MAX_LLM_CALLS: int = 500

# Minimum LLM-reported strength to persist an edge
_MIN_EDGE_STRENGTH: float = 0.15

# ---------------------------------------------------------------------------
# Pydantic models for LLM output parsing
# ---------------------------------------------------------------------------

class ComparedEdge(BaseModel):
    """Schema the LLM must produce for each evaluated claim pair."""

    source_claim_id: str = Field(..., description="ID of the first claim")
    target_claim_id: str = Field(..., description="ID of the second claim")
    relationship: Literal[
        "supports", "contradicts", "extends", "replicates", "refines", "none"
    ] = Field(..., description="Relationship type or 'none' if unrelated")
    strength: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in the relationship"
    )
    reasoning: str = Field(..., description="Brief justification")


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a scientific claim comparison agent.  Given pairs of claims from
different research papers, determine the semantic relationship between them.

RELATIONSHIP TYPES (choose exactly one per pair):
  supports    — Claim B provides evidence that reinforces Claim A.
  contradicts — Claim B presents evidence or conclusions opposing Claim A.
  extends     — Claim B builds on or generalises Claim A.
  replicates  — Claim B independently reproduces the same result as Claim A.
  refines     — Claim B narrows, qualifies, or adds nuance to Claim A.
  none        — The claims are unrelated or the relationship is too weak.

RULES:
- Evaluate each pair independently.
- Assign a strength score (0.0–1.0) reflecting how strong the relationship is.
- Provide a one-sentence reasoning.
- If you are uncertain, prefer "none" over a weak guess.

You MUST respond with valid JSON.
Return a JSON object with a single key "edges" whose value is an array.
Each element must have: source_claim_id, target_claim_id, relationship,
strength, reasoning.

Example:
{
  "edges": [
    {
      "source_claim_id": "abc-123",
      "target_claim_id": "def-456",
      "relationship": "contradicts",
      "strength": 0.82,
      "reasoning": "Claim B reports opposite effect size under the same conditions."
    }
  ]
}
"""


class ComparatorAgent(BaseAgent):
    """Agent 2 — Detect typed edges between claims from different papers."""

    SYSTEM_PROMPT = _SYSTEM_PROMPT

    async def run_for_paper(
        self,
        paper_id: str,
        graph_manager: GraphManager,
    ) -> AsyncGenerator[Edge, None]:
        """Fetch claims for a new paper and compare them to existing claims."""
        new_records = await graph_manager.get_claims_for_paper(paper_id)
        existing_records = await graph_manager.get_claims_excluding_paper(paper_id)
        new_claims = [_claim_from_record(record) for record in new_records]
        existing_claims = [_claim_from_record(record) for record in existing_records]

        async for edge in self.run(new_claims, existing_claims):
            yield edge

    async def run(
        self,
        new_claims: list[Claim],
        existing_claims: list[Claim],
    ) -> AsyncGenerator[Edge, None]:
        """Yield ``Edge`` objects for relationships found.

        Parameters
        ----------
        new_claims:
            Claims just extracted from the newly ingested paper.
        existing_claims:
            All claims already in the graph from other papers.
        """
        logger.info(
            "Comparator started",
            extra={
                "new_claims": len(new_claims),
                "existing_claims": len(existing_claims),
            },
        )

        if not new_claims or not existing_claims:
            logger.info("Nothing to compare — skipping")
            return

        # 1. Pre-filter: cosine similarity
        candidate_pairs = self._prefilter(new_claims, existing_claims)

        if not candidate_pairs:
            logger.info("No candidate pairs above similarity threshold")
            return

        max_pairs = _MAX_LLM_CALLS * _MAX_PAIRS_PER_CALL
        if len(candidate_pairs) > max_pairs:
            logger.warning(
                "Candidate pair count exceeded comparator cap; sampling pairs",
                extra={"pair_count": len(candidate_pairs), "max_pairs": max_pairs},
            )
            candidate_pairs = random.sample(candidate_pairs, max_pairs)
            candidate_pairs.sort(key=lambda pair: pair[2], reverse=True)

        logger.info(
            "Candidate pairs after pre-filter",
            extra={"pair_count": len(candidate_pairs)},
        )

        # 2. Batch pairs and send to LLM
        for batch_start in range(0, len(candidate_pairs), _MAX_PAIRS_PER_CALL):
            batch = candidate_pairs[batch_start : batch_start + _MAX_PAIRS_PER_CALL]
            prompt = self._build_prompt(batch)

            try:
                raw_response = await self.chat_completion(
                    user_prompt=prompt,
                    max_tokens=4096,
                )
            except Exception as exc:
                logger.error(
                    "LLM call failed during comparison",
                    extra={"error": str(exc)},
                )
                continue

            try:
                edges: list[ComparedEdge] = self.parse_json_list(
                    raw_response, ComparedEdge, list_key="edges"
                )
            except LLMResponseError as exc:
                logger.error(
                    "Failed to parse comparator response",
                    extra={"error": str(exc)},
                )
                continue

            # 3. Convert to schema Edge objects
            for item in edges:
                if item.relationship == "none":
                    continue
                if item.strength < _MIN_EDGE_STRENGTH:
                    continue

                edge = Edge(
                    id=str(uuid.uuid4()),
                    source_claim_id=item.source_claim_id,
                    target_claim_id=item.target_claim_id,
                    type=item.relationship,
                    strength=item.strength,
                    reasoning=item.reasoning,
                )
                logger.debug(
                    "Edge detected",
                    extra={
                        "edge_id": edge.id,
                        "type": edge.type,
                        "strength": edge.strength,
                    },
                )
                yield edge

        logger.info("Comparator finished")

    # ------------------------------------------------------------------
    # Pre-filter
    # ------------------------------------------------------------------

    def _prefilter(
        self,
        new_claims: list[Claim],
        existing_claims: list[Claim],
    ) -> list[tuple[Claim, Claim, float]]:
        """Return (new, existing, similarity) triples above threshold."""
        pairs: list[tuple[Claim, Claim, float]] = []
        for nc in new_claims:
            if not nc.embedding:
                continue
            for ec in existing_claims:
                if not ec.embedding:
                    continue
                sim = self.cosine_similarity(nc.embedding, ec.embedding)
                if sim > SIMILARITY_THRESHOLD:
                    pairs.append((nc, ec, sim))

        # Sort by similarity descending so the LLM sees the strongest first
        pairs.sort(key=lambda t: t[2], reverse=True)
        return pairs

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    @staticmethod
    def _build_prompt(pairs: list[tuple[Claim, Claim, float]]) -> str:
        """Build the user prompt for a batch of claim pairs."""
        sections: list[str] = []
        for i, (new_c, existing_c, sim) in enumerate(pairs, 1):
            sections.append(
                f"--- PAIR {i} ---\n"
                f"Claim A (id={new_c.id}, paper={new_c.paper_id}, "
                f"type={new_c.type}, section={new_c.section}):\n"
                f"  \"{new_c.text}\"\n\n"
                f"Claim B (id={existing_c.id}, paper={existing_c.paper_id}, "
                f"type={existing_c.type}, section={existing_c.section}):\n"
                f"  \"{existing_c.text}\"\n\n"
                f"Cosine similarity: {sim:.3f}"
            )
        body = "\n\n".join(sections)
        return (
            f"Evaluate the following {len(pairs)} claim pair(s) and determine "
            f"their relationship.\n\n{body}\n\n"
            "Return the edges JSON array."
        )


def _claim_from_record(record: dict[str, Any]) -> Claim:
    """Build a Claim dataclass from a Neo4j property dict."""
    return Claim(
        id=record["id"],
        paper_id=record.get("paper_id", ""),
        text=record.get("text", ""),
        type=record.get("type", "finding"),
        confidence=record.get("confidence", 0.0),
        section=record.get("section", "unknown"),
        embedding=record.get("embedding", []),
        source_chunk_text=record.get("source_chunk_text", ""),
    )
