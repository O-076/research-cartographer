"""Thread Tracer Agent.

Given a structured path from the knowledge graph (nodes + edges),
generates a flowing narrative explaining the reasoning chain.
"""

import logging
from typing import Any

from src.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a scientific reasoning analyst. Given a chain of research concepts and claims
connected through a literature knowledge graph, write a concise narrative (3-5 sentences)
explaining how the start node connects to the end node through the research.

Rules:
- Be specific about each intermediate step in the chain.
- Use relationship types (SUPPORTS, CONTRADICTS, EXTENDS, etc.) to characterize each connection.
- Reference papers when reasoning text is available.
- Write in flowing academic prose — no bullet points, no headers.
- If the path passes through a CONTRADICTS edge, explicitly note the tension.

Output ONLY the narrative text. No preamble, no conclusion label."""


class ThreadTracerAgent(BaseAgent):
    """Single-call agent that narrates the reasoning chain between two graph nodes."""

    SYSTEM_PROMPT = _SYSTEM_PROMPT

    async def trace(
        self,
        path_nodes: list[dict[str, Any]],
        path_edges: list[dict[str, Any]],
    ) -> str:
        """Generate a narrative for the given path.

        Args:
            path_nodes: Ordered list of node dicts with keys:
                id, label, text, paper_id, type
            path_edges: Ordered list of edge dicts (length = len(nodes) - 1) with keys:
                id, edge_type, strength, reasoning

        Returns:
            Plain text narrative (3-5 sentences).
        """
        if len(path_nodes) < 2:
            return "These nodes are directly connected."

        prompt = self._build_prompt(path_nodes, path_edges)
        raw = await self.chat_completion(
            user_prompt=prompt,
            json_mode=False,
            max_tokens=512,
            temperature=0.3,
        )
        return raw.strip()

    @staticmethod
    def _build_prompt(
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> str:
        start = (nodes[0].get("text") or nodes[0].get("id", ""))[:100]
        end = (nodes[-1].get("text") or nodes[-1].get("id", ""))[:100]

        steps = []
        for i, node in enumerate(nodes):
            label = node.get("label", "Node")
            text = (node.get("text") or node.get("id", ""))[:200]
            steps.append(f"[{label}] {text}")
            if i < len(edges):
                edge = edges[i]
                rel = edge.get("edge_type", "UNKNOWN")
                reasoning = (edge.get("reasoning") or "")[:150]
                if reasoning:
                    steps.append(f'  → {rel}: "{reasoning}"')
                else:
                    steps.append(f"  → {rel}")

        return (
            f'TRACE FROM: "{start}"\n'
            f'TRACE TO: "{end}"\n\n'
            "CHAIN:\n" + "\n".join(steps) +
            "\n\nWrite the narrative."
        )
