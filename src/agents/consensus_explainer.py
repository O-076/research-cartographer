"""Consensus Explainer Agent.

Takes a claim, its connected claims, edge types, and Comparator reasoning,
and produces a 2-3 sentence qualitative consensus narrative.
"""

import logging
from typing import Any

from src.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a research analyst synthesizing scientific consensus.
Given a claim and the evidence from connected papers, write exactly 2-3 sentences:
1. State the overall level of consensus and what drives it.
2. Describe the most significant agreement or disagreement specifically
   (name the paper argument, not just the paper title if possible).
3. Characterize the nature of the debate: is it methodological, about scope,
   about replication, or about interpretation?
Output only the explanation text. No headers, no bullets, no preamble.
Be specific and grounded in the evidence provided. Do not fabricate details."""


class ConsensusExplainerAgent(BaseAgent):
    """Single-call agent that explains field consensus for a given claim."""

    SYSTEM_PROMPT = _SYSTEM_PROMPT

    async def explain(
        self,
        claim_text: str,
        paper_title: str,
        consensus_pct: int,
        semantic_edges: list[dict[str, Any]],
    ) -> str:
        """Generate a 2-3 sentence consensus explanation.

        Args:
            claim_text: The text of the focal claim.
            paper_title: The paper this claim comes from.
            consensus_pct: Pre-computed consensus percentage (0-100).
            semantic_edges: List of dicts with keys:
                edge_type, strength, reasoning, other_claim_text, other_paper_title, direction
                direction is "outgoing" or "incoming".

        Returns:
            Plain text explanation (2-3 sentences).
        """
        prompt = self._build_prompt(
            claim_text, paper_title, consensus_pct, semantic_edges
        )
        raw = await self.chat_completion(
            user_prompt=prompt,
            json_mode=False,
            max_tokens=256,
            temperature=0.3,
        )
        return raw.strip()

    @staticmethod
    def _build_prompt(
        claim_text: str,
        paper_title: str,
        consensus_pct: int,
        semantic_edges: list[dict[str, Any]],
    ) -> str:
        lines = [
            f'CLAIM: "{claim_text}"',
            f"SOURCE PAPER: {paper_title}",
            f"CONSENSUS SCORE: {consensus_pct}%",
            "",
        ]

        # Group edges by type
        supports, contradicts, extends = [], [], []
        for e in semantic_edges:
            t = (e.get("edge_type") or "").upper()
            entry = (
                f'  - "{e.get("other_claim_text", "")}" '
                f'({e.get("other_paper_title", "Unknown")}) '
                f'— strength {round((e.get("strength") or 0) * 100)}%'
            )
            if e.get("reasoning"):
                entry += f' — reasoning: "{e["reasoning"]}"'

            if t == "CONTRADICTS":
                contradicts.append(entry)
            elif t in ("SUPPORTS", "REPLICATES"):
                supports.append(entry)
            else:  # EXTENDS, REFINES
                extends.append(entry)

        if supports:
            lines.append("SUPPORTING CLAIMS:")
            lines.extend(supports)
            lines.append("")
        if contradicts:
            lines.append("CONTRADICTING CLAIMS:")
            lines.extend(contradicts)
            lines.append("")
        if extends:
            lines.append("EXTENDING/REFINING CLAIMS:")
            lines.extend(extends)
            lines.append("")

        if not (supports or contradicts or extends):
            lines.append("No connected semantic claims found.")

        return "\n".join(lines)
