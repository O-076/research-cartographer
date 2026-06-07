"""Agent 4 — Cartographer (A2A Orchestrator).

Coordinates the full ingestion pipeline:

    parse PDF → upload to Foundry IQ → Extract claims → Compare → Gap Find

Emits delta events at each stage so the frontend receives live updates.
Tracks per-paper pipeline state:

    QUEUED → EXTRACTING → CLAIMS_READY → COMPARING → EDGES_READY → GAP_FINDING → COMPLETE
                                                                                     ↕
                                                                                  ERROR
"""

import asyncio
import logging
from typing import Any

from src.agents.base_agent import BaseAgent
from src.agents.comparator import ComparatorAgent
from src.agents.extractor import ExtractorAgent
from src.agents.gap_finder import GapFinderAgent
from src.graph.delta_emitter import DeltaEmitter
from src.graph.graph_manager import GraphManager
from src.graph.schema import (
    Claim,
    Paper,
    PipelineStatus,
    claim_to_props,
    edge_to_props,
    paper_to_props,
    question_to_props,
)
from src.ingestion.foundry_uploader import FoundryIQUploader
from src.ingestion.pdf_parser import parse_pdf

logger = logging.getLogger(__name__)


class CartographerAgent(BaseAgent):
    """A2A orchestrator that drives the full paper-processing pipeline.

    Usage::

        carto = CartographerAgent(graph_manager=gm, delta_emitter=de)
        await carto.process_paper(paper_id, pdf_bytes, title="My Paper")
    """

    SYSTEM_PROMPT = ""  # Not used directly — sub-agents have their own prompts

    def __init__(
        self,
        graph_manager: GraphManager,
        delta_emitter: DeltaEmitter,
        foundry_uploader: FoundryIQUploader | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._graph = graph_manager
        self._delta = delta_emitter
        self._uploader = foundry_uploader

        # Per-paper state tracking
        self._paper_states: dict[str, PipelineStatus] = {}

        # Pipeline work queue
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        # Sub-agents (lazily initialised to share credentials)
        self._extractor: ExtractorAgent | None = None
        self._comparator: ComparatorAgent | None = None
        self._gap_finder: GapFinderAgent | None = None

    # ------------------------------------------------------------------
    # Sub-agent initialisation (shares Azure credentials)
    # ------------------------------------------------------------------

    def _get_extractor(self) -> ExtractorAgent:
        if self._extractor is None:
            self._extractor = ExtractorAgent(
                azure_openai_endpoint=self._openai_endpoint,
                azure_openai_key=self._openai_key,
                azure_openai_deployment=self._openai_deployment,
                azure_openai_embedding_deployment=self._embedding_deployment,
                foundry_iq_endpoint=self._foundry_endpoint,
                foundry_iq_key=self._foundry_key,
                foundry_iq_kb_id=self._foundry_kb_id,
            )
        return self._extractor

    def _get_comparator(self) -> ComparatorAgent:
        if self._comparator is None:
            self._comparator = ComparatorAgent(
                azure_openai_endpoint=self._openai_endpoint,
                azure_openai_key=self._openai_key,
                azure_openai_deployment=self._openai_deployment,
                azure_openai_embedding_deployment=self._embedding_deployment,
                foundry_iq_endpoint=self._foundry_endpoint,
                foundry_iq_key=self._foundry_key,
                foundry_iq_kb_id=self._foundry_kb_id,
            )
        return self._comparator

    def _get_gap_finder(self) -> GapFinderAgent:
        if self._gap_finder is None:
            self._gap_finder = GapFinderAgent(
                azure_openai_endpoint=self._openai_endpoint,
                azure_openai_key=self._openai_key,
                azure_openai_deployment=self._openai_deployment,
                azure_openai_embedding_deployment=self._embedding_deployment,
                foundry_iq_endpoint=self._foundry_endpoint,
                foundry_iq_key=self._foundry_key,
                foundry_iq_kb_id=self._foundry_kb_id,
            )
        return self._gap_finder

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def enqueue_paper(
        self,
        paper_id: str,
        pdf_bytes: bytes,
        title: str = "Untitled",
        authors: list[str] | None = None,
    ) -> None:
        """Add a paper to the processing queue."""
        await self._queue.put({
            "paper_id": paper_id,
            "pdf_bytes": pdf_bytes,
            "title": title,
            "authors": authors or [],
        })
        self._paper_states[paper_id] = PipelineStatus.QUEUED
        logger.info("Paper enqueued", extra={"paper_id": paper_id, "title": title})

    async def run_queue(self) -> None:
        """Process all items currently in the queue.

        Designed to be called after uploads, or run as a background task.
        """
        while not self._queue.empty():
            item = await self._queue.get()
            try:
                await self.process_paper(
                    paper_id=item["paper_id"],
                    pdf_bytes=item["pdf_bytes"],
                    title=item["title"],
                    authors=item.get("authors", []),
                )
            except Exception as exc:
                logger.error(
                    "Pipeline failed for paper",
                    extra={"paper_id": item["paper_id"], "error": str(exc)},
                )
            finally:
                self._queue.task_done()

    async def process_paper(
        self,
        paper_id: str,
        pdf_bytes: bytes,
        title: str = "Untitled",
        authors: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run the full pipeline for a single paper.

        Returns a summary dict with counts of claims, edges, and questions.
        """
        summary: dict[str, Any] = {
            "paper_id": paper_id,
            "claims": 0,
            "edges": 0,
            "questions": 0,
            "status": PipelineStatus.QUEUED.value,
        }

        try:
            # ── 0. Create Paper node ──────────────────────────────
            paper = Paper(
                id=paper_id,
                title=title,
                authors=authors or [],
                status=PipelineStatus.QUEUED.value,
            )
            await self._graph.add_paper(paper)
            await self._delta.emit_node_added(
                {"label": "Paper", **paper_to_props(paper)}
            )
            await self._set_status(paper_id, PipelineStatus.EXTRACTING)

            # ── 1. Parse PDF ──────────────────────────────────────
            logger.info("Parsing PDF", extra={"paper_id": paper_id})
            chunks = await parse_pdf(pdf_bytes, paper_id)
            logger.info(
                "PDF parsed",
                extra={"paper_id": paper_id, "chunk_count": len(chunks)},
            )

            # ── 2. Upload to Foundry IQ ───────────────────────────
            if self._uploader and chunks:
                try:
                    upload_result = await self._uploader.upload_chunks(chunks)
                    logger.info(
                        "Chunks uploaded to Foundry IQ",
                        extra={
                            "paper_id": paper_id,
                            "status": upload_result.status,
                        },
                    )
                except Exception as exc:
                    logger.warning(
                        "Foundry IQ upload failed — continuing with local chunks",
                        extra={"paper_id": paper_id, "error": str(exc)},
                    )

            # ── 3. Extract claims ─────────────────────────────────
            new_claims: list[Claim] = []
            extractor = self._get_extractor()

            # Convert parsed chunks to dict format the extractor expects
            chunk_dicts = [
                {
                    "content": c.text,
                    "metadata": {
                        "section": c.section,
                        "chunk_index": c.chunk_index,
                        "page_numbers": c.page_numbers,
                    },
                }
                for c in chunks
            ]

            from src.graph.schema import concept_to_props
            
            async for claim, concepts in extractor.run(paper_id, chunks=chunk_dicts):
                await self._graph.add_claim(claim)
                await self._delta.emit_node_added(claim_to_props(claim))
                
                # Emit the CONTAINS edge so the frontend links them
                await self._delta.emit_edge_added({
                    "id": f"{paper_id}:CONTAINS:{claim.id}",
                    "source": paper_id,
                    "target": claim.id,
                    "rel_type": "CONTAINS",
                    "type": "contains"
                })
                
                # Link Concepts
                for concept in concepts:
                    await self._graph.add_concept(concept)
                    await self._delta.emit_node_added({"label": "Concept", **concept_to_props(concept)})
                    
                    await self._graph.link_claim_to_concept(claim.id, concept.id)
                    await self._delta.emit_edge_added({
                        "id": f"{claim.id}:RELATES_TO:{concept.id}",
                        "source": claim.id,
                        "target": concept.id,
                        "rel_type": "RELATES_TO",
                        "type": "relates_to"
                    })
                
                new_claims.append(claim)

            summary["claims"] = len(new_claims)
            logger.info(
                "Claims extracted",
                extra={"paper_id": paper_id, "count": len(new_claims)},
            )

            await self._set_status(paper_id, PipelineStatus.CLAIMS_READY)

            if not new_claims:
                logger.warning(
                    "No claims extracted — skipping comparison and gap-finding",
                    extra={"paper_id": paper_id},
                )
                await self._set_status(paper_id, PipelineStatus.COMPLETE)
                summary["status"] = PipelineStatus.COMPLETE.value
                return summary

            # ── 4. Compare claims ─────────────────────────────────
            await self._set_status(paper_id, PipelineStatus.COMPARING)

            existing_claim_dicts = await self._graph.get_claims_excluding_paper(paper_id)
            existing_claims = [
                Claim(
                    id=d["id"],
                    paper_id=d.get("paper_id", ""),
                    text=d.get("text", ""),
                    type=d.get("type", "finding"),
                    confidence=d.get("confidence", 0.0),
                    section=d.get("section", "unknown"),
                    embedding=d.get("embedding", []),
                )
                for d in existing_claim_dicts
            ]

            comparator = self._get_comparator()
            edge_count = 0
            async for edge in comparator.run(new_claims, existing_claims):
                is_new = await self._graph.add_edge(edge)
                if is_new:
                    await self._delta.emit_edge_added(edge_to_props(edge))
                else:
                    await self._graph.update_edge(edge)
                    await self._delta.emit_edge_updated(edge_to_props(edge))
                edge_count += 1

            summary["edges"] = edge_count
            logger.info(
                "Edges created/updated",
                extra={"paper_id": paper_id, "count": edge_count},
            )

            await self._set_status(paper_id, PipelineStatus.EDGES_READY)

            # ── 5. Find gaps ──────────────────────────────────────
            await self._set_status(paper_id, PipelineStatus.GAP_FINDING)

            all_claim_dicts = await self._graph.get_all_claims()
            all_claims_for_gaps = [
                Claim(
                    id=d["id"],
                    paper_id=d.get("paper_id", ""),
                    text=d.get("text", ""),
                    type=d.get("type", "finding"),
                    confidence=d.get("confidence", 0.0),
                    section=d.get("section", "unknown"),
                    embedding=d.get("embedding", []),
                )
                for d in all_claim_dicts
            ]

            existing_questions = await self._graph.get_open_questions()

            gap_finder = self._get_gap_finder()
            question_count = 0
            async for question in gap_finder.run(all_claims_for_gaps, existing_questions):
                await self._graph.upsert_question(question)
                await self._delta.emit_question_added(question_to_props(question))
                
                for claim_id in question.related_claim_ids:
                    await self._delta.emit_edge_added({
                        "id": f"{question.id}:GAPS:{claim_id}",
                        "source": question.id,
                        "target": claim_id,
                        "rel_type": "GAPS",
                        "type": "gaps"
                    })
                
                question_count += 1

            summary["questions"] = question_count
            logger.info(
                "Open questions found",
                extra={"paper_id": paper_id, "count": question_count},
            )

            # ── 6. Done ───────────────────────────────────────────
            await self._set_status(paper_id, PipelineStatus.COMPLETE)
            summary["status"] = PipelineStatus.COMPLETE.value

        except Exception as exc:
            logger.error(
                "Pipeline error",
                extra={"paper_id": paper_id, "error": str(exc)},
                exc_info=True,
            )
            await self._set_status(paper_id, PipelineStatus.ERROR)
            summary["status"] = PipelineStatus.ERROR.value

        return summary

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------

    def get_paper_status(self, paper_id: str) -> str:
        """Return the current pipeline status for a paper."""
        status = self._paper_states.get(paper_id)
        return status.value if status else "unknown"

    async def _set_status(self, paper_id: str, status: PipelineStatus) -> None:
        """Update pipeline state in memory, Neo4j, and via WebSocket."""
        self._paper_states[paper_id] = status
        try:
            await self._graph.update_paper_status(paper_id, status.value)
        except Exception as exc:
            logger.warning(
                "Failed to update paper status in Neo4j",
                extra={"paper_id": paper_id, "error": str(exc)},
            )
        await self._delta.emit_paper_status(paper_id, status.value)
        logger.info(
            "Pipeline status changed",
            extra={"paper_id": paper_id, "status": status.value},
        )

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Release resources for all sub-agents."""
        for agent in (self._extractor, self._comparator, self._gap_finder):
            if agent is not None:
                await agent.close()
        await super().close()
