"""Agent 3 — Gap Finder.

Analyse the full claim graph and identify research questions that the
corpus does not yet answer. Novelty scores are evaluated using the free
Semantic Scholar API for real web grounding.

Output: ``AsyncGenerator[OpenQuestion, None]``
"""

import logging
import uuid
import urllib.parse
from collections.abc import AsyncGenerator
from typing import Any

import httpx
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

                # Web Grounding: Semantic Scholar API for novelty score
                novelty, web_evidence = await self._compute_novelty_score(gap.question)

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
    # Semantic Scholar novelty scorer (Web Grounding)
    # ------------------------------------------------------------------

    async def _compute_novelty_score(self, question: str) -> tuple[float, str]:
        """Query Semantic Scholar to determine novelty of the research question.
        
        Returns a tuple of (novelty_score, web_evidence).
        """
        query = urllib.parse.quote_plus(question)
        url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={query}&limit=5"
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    total_papers = data.get("total", 0)
                    
                    # More papers = lower novelty. 0 papers = max novelty.
                    if total_papers == 0:
                        novelty = 0.95
                    elif total_papers < 10:
                        novelty = 0.85 - (total_papers * 0.02)
                    elif total_papers < 100:
                        novelty = 0.65
                    else:
                        novelty = max(0.1, 0.5 - (total_papers / 1000.0))
                        
                    evidence = f"Semantic Scholar found {total_papers} related papers. Calculated novelty: {novelty:.2f}."
                    return round(novelty, 2), evidence
                else:
                    logger.warning(f"Semantic Scholar API returned {response.status_code}")
        except Exception as exc:
            logger.error("Failed to query Semantic Scholar", extra={"error": str(exc)})
            
        # Fallback if API fails
        bucket = sum(ord(char) for char in question) % 61
        novelty = round(0.3 + bucket / 100, 2)
        evidence = f"Web search failed. Deterministic fallback score: {novelty:.2f}."
        return novelty, evidence
