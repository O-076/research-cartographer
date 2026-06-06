"""Agent 3 — Gap Finder.

Analyse the full claim graph and identify research questions that the
corpus does not yet answer.  For MVP, Web IQ is skipped and novelty
scores are mocked (random 0.3–0.9).

Output: ``AsyncGenerator[OpenQuestion, None]``
"""

import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from pydantic import BaseModel, Field

from src.agents.base_agent import BaseAgent, LLMResponseError
from src.graph.schema import Claim, OpenQuestion, QuestionStatus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Maximum number of claims to include in a single LLM prompt
_MAX_CLAIMS_PER_CALL: int = 30

# Minimum novelty score to emit a question (post-mock-scoring)
_MIN_NOVELTY_SCORE: float = 0.3

# ---------------------------------------------------------------------------
# Pydantic models for LLM output parsing
# ---------------------------------------------------------------------------

class IdentifiedGap(BaseModel):
    """Schema the LLM must produce for each open question."""

    question: str = Field(..., description="The research question in plain English")
    related_claim_ids: list[str] = Field(
        ..., description="IDs of claims that surface this gap"
    )
    reasoning: str = Field(
        ..., description="Why this question is unanswered by the current corpus"
    )


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a research gap identification agent.  You receive a set of
extracted claims from multiple scientific papers and must identify
open questions — i.e. important research questions that the current
corpus does NOT answer.

RULES:
- Focus on gaps between papers: contradictions without resolution,
  methods tested only on narrow datasets, assumptions not validated, etc.
- Each question must be concrete and falsifiable.
- Provide the IDs of the 2-5 claims most relevant to each gap.
- Do NOT restate existing findings as questions.
- Limit your output to at most 8 high-quality questions.

You MUST respond with valid JSON.
Return a JSON object with a single key "gaps" whose value is an array.
Each element must have: question, related_claim_ids, reasoning.

Example:
{
  "gaps": [
    {
      "question": "Does model X generalise beyond benchmark Y?",
      "related_claim_ids": ["id-1", "id-2"],
      "reasoning": "Claim id-1 reports high accuracy on Y, but no other benchmarks were tested."
    }
  ]
}
"""


class GapFinderAgent(BaseAgent):
    """Agent 3 — Discover open research questions from the claim graph."""

    SYSTEM_PROMPT = _SYSTEM_PROMPT

    async def run(
        self,
        all_claims: list[Claim],
        existing_questions: list[dict[str, Any]] | None = None,
    ) -> AsyncGenerator[OpenQuestion, None]:
        """Yield ``OpenQuestion`` objects for discovered gaps.

        Parameters
        ----------
        all_claims:
            Every claim currently in the graph.
        existing_questions:
            Previously emitted questions (to help avoid duplicates).
        """
        logger.info(
            "GapFinder started",
            extra={"claim_count": len(all_claims)},
        )

        if len(all_claims) < 2:
            logger.info("Too few claims to find gaps — skipping")
            return

        # Deduplicate existing question texts for the LLM context
        existing_q_texts: list[str] = []
        if existing_questions:
            existing_q_texts = [
                q.get("question", "") for q in existing_questions if q.get("question")
            ]

        # Process in batches if claim count is very high
        for batch_start in range(0, len(all_claims), _MAX_CLAIMS_PER_CALL):
            batch = all_claims[batch_start : batch_start + _MAX_CLAIMS_PER_CALL]
            prompt = self._build_prompt(batch, existing_q_texts)

            try:
                raw_response = await self.chat_completion(
                    user_prompt=prompt,
                    max_tokens=4096,
                )
            except Exception as exc:
                logger.error(
                    "LLM call failed during gap finding",
                    extra={"error": str(exc)},
                )
                continue

            try:
                gaps: list[IdentifiedGap] = self.parse_json_list(
                    raw_response, IdentifiedGap, list_key="gaps"
                )
            except LLMResponseError as exc:
                logger.error(
                    "Failed to parse gap-finder response",
                    extra={"error": str(exc)},
                )
                continue

            # Validate that related_claim_ids actually exist
            valid_ids = {c.id for c in all_claims}

            for gap in gaps:
                # Filter to only valid claim IDs
                related = [cid for cid in gap.related_claim_ids if cid in valid_ids]
                if not related:
                    logger.debug(
                        "Skipping gap with no valid related claims",
                        extra={"question": gap.question[:80]},
                    )
                    continue

                # MVP: mock novelty score (skip real Web IQ)
                novelty = self._mock_novelty_score(gap.question)
                web_evidence = (
                    "[MVP mock] Web IQ search skipped. "
                    f"Mock novelty score: {novelty:.2f}"
                )

                if novelty < _MIN_NOVELTY_SCORE:
                    continue

                question = OpenQuestion(
                    id=str(uuid.uuid4()),
                    question=gap.question,
                    novelty_score=novelty,
                    related_claim_ids=related,
                    web_evidence=web_evidence,
                    status=QuestionStatus.OPEN.value,
                )
                logger.debug(
                    "Gap found",
                    extra={
                        "question_id": question.id,
                        "novelty": question.novelty_score,
                    },
                )
                yield question

        logger.info("GapFinder finished")

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    @staticmethod
    def _build_prompt(
        claims: list[Claim],
        existing_questions: list[str],
    ) -> str:
        """Build the user prompt for a batch of claims."""
        claim_lines: list[str] = []
        for c in claims:
            claim_lines.append(
                f"- id={c.id} | paper={c.paper_id} | type={c.type} | "
                f"section={c.section} | confidence={c.confidence:.2f}\n"
                f"  \"{c.text}\""
            )

        body = "\n".join(claim_lines)
        prompt = (
            f"The knowledge graph currently contains {len(claims)} claims:\n\n"
            f"{body}\n\n"
        )

        if existing_questions:
            eq_text = "\n".join(f"  - {q}" for q in existing_questions[:10])
            prompt += (
                "Previously identified questions (do NOT repeat these):\n"
                f"{eq_text}\n\n"
            )

        prompt += "Identify open research questions that this corpus does NOT answer."
        return prompt

    # ------------------------------------------------------------------
    # Mock novelty scorer (MVP placeholder for Web IQ)
    # ------------------------------------------------------------------

    @staticmethod
    def _mock_novelty_score(question: str) -> float:
        """Return a deterministic placeholder novelty score between 0.3 and 0.9.

        In production this would be informed by Web IQ search results.
        """
        bucket = sum(ord(char) for char in question) % 61
        return round(0.3 + bucket / 100, 2)
