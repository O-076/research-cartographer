"""Literature Review Agent.

Gathers corpus data from Neo4j, formats APA citations in Python,
and generates a structured APA-format literature review via a single LLM call.
Returns a dict with keys: title, abstract, sections, references.
"""

import json
import logging
from typing import Any

from src.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are an academic writer producing a formal scientific literature review.

CRITICAL RULES — every violation makes the output unusable:
1. Write in formal academic prose. No conversational or AI-assistant language.
2. BANNED phrases (do not use): "It is important to note", "Overall, the literature suggests",
   "In conclusion, this review has demonstrated", "It is worth noting", "It is evident that",
   "This comprehensive review", "Notably,", "Importantly,", starting sentences with "Furthermore," or "Moreover,".
3. Every factual claim MUST have an APA in-text citation. Use ONLY the citations provided — never invent them.
4. Do NOT summarize papers individually. Synthesize thematically: compare, contrast, connect across papers.
5. Contradictions must be named explicitly: "Author (Year) directly challenge Author (Year) by arguing..."
6. Each thematic section must integrate claims from at least 2 different papers per paragraph.
7. Research gaps must reference the specific questions provided, not generic "more research is needed."
8. The abstract has NO citations.
9. References section must list every paper cited in the body.

OUTPUT: Return ONLY valid JSON — no preamble, no markdown backticks:
{
  "title": "Literature Review: [specific, descriptive title — not generic]",
  "abstract": "150-200 word summary of the corpus scope, key findings, and tensions. No citations.",
  "sections": [
    {"heading": "Introduction", "content": "200-250 words. Establish the research domain, scope of this review, why it matters. Cite the papers that define the field."},
    {"heading": "[Theme derived from concept cluster 1]", "content": "250-350 words with in-text citations. Synthesize across papers."},
    {"heading": "[Theme derived from concept cluster 2]", "content": "250-350 words with in-text citations."},
    [add 1-2 more thematic sections if concept data warrants it],
    {"heading": "Synthesis and Ongoing Debates", "content": "200-250 words. Explicitly name contradictions. Who argues what against whom, and why the debate matters."},
    {"heading": "Research Gaps and Future Directions", "content": "150-200 words. Reference specific open questions from the provided list."},
    {"heading": "Conclusion", "content": "100-150 words. Summarize key contributions and tensions. No new citations."}
  ],
  "references": [
    "APA-formatted reference string for every paper cited in the body."
  ]
}
"""


class LiteratureReviewAgent(BaseAgent):
    """Generates a full APA-format literature review from corpus graph data."""

    SYSTEM_PROMPT = _SYSTEM_PROMPT

    async def generate(self, review_data: dict[str, Any]) -> dict[str, Any]:
        """Generate the literature review.

        Args:
            review_data: Dict from graph_manager.get_review_data() with keys:
                papers, concepts, contradictions, questions.

        Returns:
            Dict with keys: title, abstract, sections (list of {heading, content}),
            references (list of str).
        """
        prompt = self._build_prompt(review_data)
        raw = await self.chat_completion(
            user_prompt=prompt,
            json_mode=True,
            max_tokens=4096,
            temperature=0.2,
        )
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.error("LiteratureReviewAgent: JSON parse failed", extra={"error": str(exc)})
            raise

        return parsed

    def _build_prompt(self, data: dict[str, Any]) -> str:
        papers = data.get("papers") or []
        concepts = data.get("concepts") or []
        contradictions = data.get("contradictions") or []
        questions = data.get("questions") or []

        # ── Papers with APA in-text and reference format ────────────
        paper_lines = []
        for p in papers:
            intext = self.apa_intext(p.get("authors"), p.get("year"))
            abstract_snippet = str(p.get("abstract") or "")[:300]
            paper_lines.append(
                f"- {intext}: \"{p.get('title', 'Untitled')}\""
                + (f" | Abstract: {abstract_snippet}" if abstract_snippet else "")
            )

        # ── Concept clusters ─────────────────────────────────────────
        concept_lines = []
        for c in concepts:
            claims_summary = " | ".join(
                f"{claim.get('text', '')[:100]} {self.apa_intext(claim.get('authors'), claim.get('paper_year'))}"
                for claim in (c.get("claims") or [])[:5]
            )
            concept_lines.append(
                f"CONCEPT [{c['concept']}] ({c['claim_count']} claims): {claims_summary}"
            )

        # ── Contradictions ───────────────────────────────────────────
        contra_lines = []
        for c in contradictions:
            cite1 = self.apa_intext(c.get("paper1_authors"), c.get("paper1_year"))
            cite2 = self.apa_intext(c.get("paper2_authors"), c.get("paper2_year"))
            contra_lines.append(
                f"- {cite1}: \"{str(c.get('claim1_text',''))[:150]}\"\n"
                f"  CONTRADICTS {cite2}: \"{str(c.get('claim2_text',''))[:150]}\"\n"
                f"  Comparator reasoning: \"{str(c.get('reasoning',''))[:200]}\""
            )

        # ── Open questions ───────────────────────────────────────────
        question_lines = [
            f"- (novelty {round((q.get('novelty_score') or 0) * 100)}%): {q.get('question', '')}"
            for q in questions
        ]

        lines = [
            "PAPERS IN CORPUS (use these exact APA citations):",
            *paper_lines,
            "",
            "CONCEPT CLUSTERS (derive thematic section headings from these):",
            *(concept_lines or ["None detected."]),
            "",
            "CONTRADICTIONS (must be discussed explicitly in Synthesis section):",
            *(contra_lines or ["None detected yet."]),
            "",
            "OPEN RESEARCH QUESTIONS (use in Research Gaps section):",
            *(question_lines or ["None detected yet."]),
            "",
            "Write the literature review following the system prompt instructions.",
        ]
        return "\n".join(lines)

    @staticmethod
    def apa_intext(authors: list[str] | None, year: int | None) -> str:
        """Format APA in-text citation: (Last, Year), (Last & Last, Year), or (Last et al., Year)."""
        authors = authors or []
        year_str = str(year) if year else "n.d."
        last_names = [a.strip().split()[-1] for a in authors if a.strip()]
        if not last_names:
            return f"(Anonymous, {year_str})"
        if len(last_names) == 1:
            return f"({last_names[0]}, {year_str})"
        if len(last_names) == 2:
            return f"({last_names[0]} & {last_names[1]}, {year_str})"
        return f"({last_names[0]} et al., {year_str})"
