"""Neo4j CRUD and query interface for the knowledge graph.

This is the *only* file that contains Cypher queries.
All graph reads and writes go through ``GraphManager``.
"""

import logging
import uuid
import os
from typing import Any

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession

from src.graph.schema import (
    ALL_NEO4J_DDL,
    EDGE_TYPE_TO_NEO4J,
    Claim,
    Concept,
    Edge,
    OpenQuestion,
    Paper,
    claim_to_props,
    concept_to_props,
    edge_to_props,
    paper_to_props,
    question_to_props,
)

logger = logging.getLogger(__name__)


class GraphWriteError(Exception):
    """Raised when a graph write operation fails."""


class GraphManager:
    """Async interface to the Neo4j knowledge graph.

    Usage::

        gm = GraphManager.from_env()
        await gm.initialize()    # create constraints / indexes
        await gm.add_paper(paper)
        ...
        await gm.close()
    """

    def __init__(self, uri: str, username: str, password: str) -> None:
        self._driver: AsyncDriver = AsyncGraphDatabase.driver(
            uri, auth=(username, password)
        )

    @classmethod
    def from_env(cls) -> "GraphManager":
        """Create a GraphManager from environment variables."""
        uri = _required_env("NEO4J_URI")
        username = _required_env("NEO4J_USERNAME")
        password = _required_env("NEO4J_PASSWORD")
        return cls(uri=uri, username=username, password=password)

    async def close(self) -> None:
        """Close the Neo4j driver."""
        await self._driver.close()

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Run all constraint and index DDL statements."""
        async with self._driver.session() as session:
            for ddl in ALL_NEO4J_DDL:
                await session.run(ddl)
        logger.info("Neo4j schema initialized", extra={"ddl_count": len(ALL_NEO4J_DDL)})

    # ------------------------------------------------------------------
    # Paper CRUD
    # ------------------------------------------------------------------

    async def add_paper(self, paper: Paper) -> None:
        """Create or merge a Paper node."""
        query = """
        MERGE (p:Paper {id: $id})
        SET p += $props
        """
        props = paper_to_props(paper)
        await self._write(query, {"id": paper.id, "props": props}, "add_paper")

    async def update_paper_status(self, paper_id: str, status: str) -> None:
        """Update the pipeline status on a Paper node."""
        query = """
        MATCH (p:Paper {id: $id})
        SET p.status = $status
        """
        await self._write(query, {"id": paper_id, "status": status}, "update_paper_status")

    async def get_paper(self, paper_id: str) -> dict[str, Any] | None:
        """Fetch a single Paper node by id."""
        query = "MATCH (p:Paper {id: $id}) RETURN p"
        async with self._driver.session() as session:
            result = await session.run(query, {"id": paper_id})
            record = await result.single()
            return dict(record["p"]) if record else None

    # ------------------------------------------------------------------
    # Claim CRUD
    # ------------------------------------------------------------------

    async def add_claim(self, claim: Claim) -> None:
        """Create a Claim node and link it to its Paper."""
        query = """
        MERGE (c:Claim {id: $id})
        SET c += $props
        WITH c
        MATCH (p:Paper {id: $paper_id})
        MERGE (p)-[r:CONTAINS]->(c)
        ON CREATE SET r.id = $edge_id
        """
        props = claim_to_props(claim)
        await self._write(
            query,
            {
                "id": claim.id,
                "props": props,
                "paper_id": claim.paper_id,
                "edge_id": str(uuid.uuid4()),
            },
            "add_claim",
        )

    async def get_claims_for_paper(self, paper_id: str) -> list[dict[str, Any]]:
        """Return all claims belonging to a paper."""
        query = """
        MATCH (p:Paper {id: $paper_id})-[:CONTAINS]->(c:Claim)
        RETURN c
        ORDER BY c.created_at
        """
        return await self._read_nodes(query, {"paper_id": paper_id}, "c")

    async def get_all_claims(self) -> list[dict[str, Any]]:
        """Return every Claim node in the graph."""
        query = "MATCH (c:Claim) RETURN c ORDER BY c.created_at"
        return await self._read_nodes(query, {}, "c")

    async def get_claims_excluding_paper(self, paper_id: str) -> list[dict[str, Any]]:
        """Return all claims that do NOT belong to the given paper."""
        query = """
        MATCH (c:Claim) WHERE c.paper_id <> $paper_id
        RETURN c ORDER BY c.created_at
        """
        return await self._read_nodes(query, {"paper_id": paper_id}, "c")

    # ------------------------------------------------------------------
    # Edge (Relationship) CRUD
    # ------------------------------------------------------------------

    async def add_edge(self, edge: Edge) -> bool:
        """Create a typed relationship between two claims.

        Returns True if the edge was newly created, False if it already existed.
        """
        rel_type = EDGE_TYPE_TO_NEO4J.get(edge.type)
        if not rel_type:
            raise GraphWriteError(f"Unknown edge type: {edge.type}")

        query = f"""
        MATCH (src:Claim {{id: $src_id}})
        MATCH (tgt:Claim {{id: $tgt_id}})
        MERGE (src)-[r:{rel_type} {{id: $edge_id}}]->(tgt)
        ON CREATE SET r += $props, r._created = true
        ON MATCH SET
            r.source_claim_id = $src_id,
            r.target_claim_id = $tgt_id,
            r.type = $edge_type,
            r.strength = $strength,
            r.reasoning = $reasoning,
            r._created = false
        RETURN r._created AS created
        """
        props = edge_to_props(edge)
        async with self._driver.session() as session:
            result = await session.run(
                query,
                {
                    "src_id": edge.source_claim_id,
                    "tgt_id": edge.target_claim_id,
                    "edge_id": edge.id,
                    "props": props,
                    "edge_type": edge.type,
                    "strength": edge.strength,
                    "reasoning": edge.reasoning,
                },
            )
            record = await result.single()
            created = bool(record["created"]) if record else True

        logger.info(
            "Edge written",
            extra={
                "edge_id": edge.id,
                "type": edge.type,
                "is_new": created,
            },
        )
        return created

    async def get_edge_with_claims(
        self, edge_id: str
    ) -> dict[str, Any] | None:
        """Fetch a relationship and both connected claims with their papers.

        Returns a dict with keys: edge, source_claim, target_claim,
        source_paper, target_paper. Returns None if the edge is not found.
        """
        query = """
        MATCH (src:Claim)-[r {id: $edge_id}]->(tgt:Claim)
        MATCH (p1:Paper)-[:CONTAINS]->(src)
        MATCH (p2:Paper)-[:CONTAINS]->(tgt)
        RETURN
            r.id           AS edge_id,
            r.type         AS edge_type,
            r.strength     AS edge_strength,
            r.reasoning    AS edge_reasoning,
            r.created_at   AS edge_created_at,
            src.id         AS src_id,
            src.text       AS src_text,
            src.type       AS src_type,
            src.confidence AS src_confidence,
            src.section    AS src_section,
            src.source_chunk_text AS src_chunk,
            src.paper_id   AS src_paper_id,
            tgt.id         AS tgt_id,
            tgt.text       AS tgt_text,
            tgt.type       AS tgt_type,
            tgt.confidence AS tgt_confidence,
            tgt.section    AS tgt_section,
            tgt.source_chunk_text AS tgt_chunk,
            tgt.paper_id   AS tgt_paper_id,
            p1.id          AS src_paper_id_full,
            p1.title       AS src_paper_title,
            p1.authors     AS src_paper_authors,
            p1.year        AS src_paper_year,
            p2.id          AS tgt_paper_id_full,
            p2.title       AS tgt_paper_title,
            p2.authors     AS tgt_paper_authors,
            p2.year        AS tgt_paper_year
        """
        async with self._driver.session() as session:
            result = await session.run(query, {"edge_id": edge_id})
            record = await result.single()
            if not record:
                return None

            data = dict(record)
            return {
                "edge": {
                    "id": data["edge_id"],
                    "type": data["edge_type"],
                    "strength": data["edge_strength"] or 0.0,
                    "reasoning": data["edge_reasoning"] or "",
                    "created_at": data["edge_created_at"],
                },
                "source_claim": {
                    "id": data["src_id"],
                    "text": data["src_text"],
                    "type": data["src_type"],
                    "confidence": data["src_confidence"] or 0.0,
                    "section": data["src_section"],
                    "source_chunk_text": data["src_chunk"] or "",
                    "paper_id": data["src_paper_id"],
                },
                "target_claim": {
                    "id": data["tgt_id"],
                    "text": data["tgt_text"],
                    "type": data["tgt_type"],
                    "confidence": data["tgt_confidence"] or 0.0,
                    "section": data["tgt_section"],
                    "source_chunk_text": data["tgt_chunk"] or "",
                    "paper_id": data["tgt_paper_id"],
                },
                "source_paper": {
                    "id": data["src_paper_id_full"],
                    "title": data["src_paper_title"],
                    "authors": data["src_paper_authors"] or [],
                    "year": data["src_paper_year"],
                },
                "target_paper": {
                    "id": data["tgt_paper_id_full"],
                    "title": data["tgt_paper_title"],
                    "authors": data["tgt_paper_authors"] or [],
                    "year": data["tgt_paper_year"],
                },
            }

    async def get_claim_consensus_context(
        self, claim_id: str
    ) -> dict[str, Any] | None:
        """Fetch a claim, its paper, and all semantic edges with connected claims.

        Used by ConsensusExplainerAgent to build its prompt.
        Returns None if the claim is not found.
        """
        # Query 1: get the claim and its paper
        claim_query = """
        MATCH (c:Claim {id: $claim_id})
        OPTIONAL MATCH (p:Paper)-[:CONTAINS]->(c)
        RETURN c.id AS id, c.text AS text, c.type AS type,
               c.confidence AS confidence, c.section AS section,
               p.title AS paper_title
        """
        # Query 2: get all semantic edges in both directions with connected claims/papers
        edges_query = """
        MATCH (c:Claim {id: $claim_id})-[r]->(other:Claim)
        WHERE type(r) IN ['SUPPORTS','CONTRADICTS','EXTENDS','REPLICATES','REFINES']
        OPTIONAL MATCH (op:Paper)-[:CONTAINS]->(other)
        RETURN type(r) AS edge_type, r.strength AS strength,
               r.reasoning AS reasoning, other.text AS other_claim_text,
               coalesce(op.title, 'Unknown paper') AS other_paper_title,
               'outgoing' AS direction
        UNION ALL
        MATCH (other:Claim)-[r]->(c:Claim {id: $claim_id})
        WHERE type(r) IN ['SUPPORTS','CONTRADICTS','EXTENDS','REPLICATES','REFINES']
        OPTIONAL MATCH (op:Paper)-[:CONTAINS]->(other)
        RETURN type(r) AS edge_type, r.strength AS strength,
               r.reasoning AS reasoning, other.text AS other_claim_text,
               coalesce(op.title, 'Unknown paper') AS other_paper_title,
               'incoming' AS direction
        """
        async with self._driver.session() as session:
            claim_result = await session.run(claim_query, {"claim_id": claim_id})
            claim_record = await claim_result.single()
            if not claim_record:
                return None

            edges_result = await session.run(edges_query, {"claim_id": claim_id})
            edge_records = [dict(r) async for r in edges_result]

        return {
            "claim": {
                "id": claim_record["id"],
                "text": claim_record["text"],
                "type": claim_record["type"],
                "confidence": claim_record["confidence"],
                "section": claim_record["section"],
                "paper_title": claim_record["paper_title"] or "Unknown paper",
            },
            "semantic_edges": edge_records,
        }

    async def update_edge(self, edge: Edge) -> None:
        """Update an existing edge's properties (re-scoring)."""
        rel_type = EDGE_TYPE_TO_NEO4J.get(edge.type)
        if not rel_type:
            raise GraphWriteError(f"Unknown edge type: {edge.type}")

        query = f"""
        MATCH (src:Claim {{id: $src_id}})-[r:{rel_type} {{id: $edge_id}}]->(tgt:Claim {{id: $tgt_id}})
        SET
            r.source_claim_id = $src_id,
            r.target_claim_id = $tgt_id,
            r.type = $edge_type,
            r.strength = $strength,
            r.reasoning = $reasoning
        """
        await self._write(
            query,
            {
                "src_id": edge.source_claim_id,
                "tgt_id": edge.target_claim_id,
                "edge_id": edge.id,
                "edge_type": edge.type,
                "strength": edge.strength,
                "reasoning": edge.reasoning,
            },
            "update_edge",
        )

    async def get_edges_for_claim(self, claim_id: str) -> list[dict[str, Any]]:
        """Return all edges where the given claim is source or target."""
        query = """
        MATCH (c:Claim {id: $claim_id})-[r]->(other:Claim)
        RETURN r, type(r) AS rel_type, c.id AS source_id, other.id AS target_id
        UNION
        MATCH (other:Claim)-[r]->(c:Claim {id: $claim_id})
        RETURN r, type(r) AS rel_type, other.id AS source_id, c.id AS target_id
        """
        async with self._driver.session() as session:
            result = await session.run(query, {"claim_id": claim_id})
            records = [record async for record in result]

        return [
            {
                **dict(record["r"]),
                "rel_type": record["rel_type"],
                "source_claim_id": record["source_id"],
                "target_claim_id": record["target_id"],
            }
            for record in records
        ]

    # ------------------------------------------------------------------
    # Concept CRUD
    # ------------------------------------------------------------------

    async def add_concept(self, concept: Concept) -> None:
        """Create or merge a Concept node."""
        query = """
        MERGE (c:Concept {id: $id})
        SET c += $props
        """
        props = concept_to_props(concept)
        await self._write(query, {"id": concept.id, "props": props}, "add_concept")

    async def link_claim_to_concept(self, claim_id: str, concept_id: str) -> None:
        """Create a RELATES_TO edge from Claim to Concept."""
        query = """
        MATCH (cl:Claim {id: $claim_id})
        MATCH (co:Concept {id: $concept_id})
        MERGE (cl)-[r:RELATES_TO]->(co)
        ON CREATE SET r.id = $edge_id
        """
        await self._write(
            query,
            {
                "claim_id": claim_id,
                "concept_id": concept_id,
                "edge_id": str(uuid.uuid4()),
            },
            "link_claim_concept",
        )

    # ------------------------------------------------------------------
    # OpenQuestion CRUD
    # ------------------------------------------------------------------

    async def upsert_question(self, question: OpenQuestion) -> None:
        """Create or update an OpenQuestion node and link to related claims."""
        query = """
        MERGE (q:OpenQuestion {id: $id})
        SET q += $props
        """
        props = question_to_props(question)
        await self._write(query, {"id": question.id, "props": props}, "upsert_question")

        for claim_id in question.related_claim_ids:
            link_query = """
            MATCH (q:OpenQuestion {id: $question_id})
            MATCH (c:Claim {id: $claim_id})
            MERGE (q)-[r:GAPS]->(c)
            ON CREATE SET r.id = $edge_id
            """
            await self._write(
                link_query,
                {
                    "question_id": question.id,
                    "claim_id": claim_id,
                    "edge_id": str(uuid.uuid4()),
                },
                "link_question_to_claim",
            )

    async def resolve_question(self, question_id: str) -> None:
        """Mark an OpenQuestion as resolved."""
        query = """
        MATCH (q:OpenQuestion {id: $id})
        SET q.status = 'resolved'
        """
        await self._write(query, {"id": question_id}, "resolve_question")

    async def get_open_questions(self) -> list[dict[str, Any]]:
        """Return all OpenQuestion nodes that are not resolved."""
        query = """
        MATCH (q:OpenQuestion)
        WHERE q.status <> 'resolved'
        RETURN q ORDER BY q.novelty_score DESC
        """
        return await self._read_nodes(query, {}, "q")

    # ------------------------------------------------------------------
    # Full graph snapshot (for initial frontend load)
    # ------------------------------------------------------------------

    async def get_full_graph(self) -> dict[str, Any]:
        """Return the entire graph as nodes + edges for GET /graph."""
        nodes_query = """
        MATCH (n)
        RETURN n, labels(n)[0] AS label
        """
        edges_query = """
        MATCH (a)-[r]->(b)
        RETURN a.id AS source, b.id AS target, type(r) AS rel_type,
               properties(r) AS props
        """
        async with self._driver.session() as session:
            nodes_result = await session.run(nodes_query)
            node_records = [record async for record in nodes_result]

            edges_result = await session.run(edges_query)
            edge_records = [record async for record in edges_result]

        nodes = [
            {"label": record["label"], **dict(record["n"])}
            for record in node_records
        ]
        edges: list[dict[str, Any]] = []
        for record in edge_records:
            props = dict(record["props"])
            rel_type = record["rel_type"]
            source = record["source"]
            target = record["target"]
            edge_id = props.get("id") or f"{source}:{rel_type}:{target}"
            edges.append(
                {
                    "id": edge_id,
                    "source": source,
                    "target": target,
                    "rel_type": rel_type,
                    "type": props.get("type", rel_type.lower()),
                    **props,
                }
            )

        return {"nodes": nodes, "edges": edges}

    # ------------------------------------------------------------------
    # Contradiction clusters (for D3.js tension highlights)
    # ------------------------------------------------------------------

    async def get_contradiction_clusters(self) -> list[dict[str, Any]]:
        """Return claims with the most contradiction edges."""
        query = """
        MATCH (c1:Claim)-[r:CONTRADICTS]-(c2:Claim)
        RETURN c1.id AS claim_id, count(r) AS tension_score
        ORDER BY tension_score DESC
        LIMIT 20
        """
        async with self._driver.session() as session:
            result = await session.run(query)
            return [dict(record) async for record in result]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _write(
        self, query: str, params: dict[str, Any], operation: str
    ) -> None:
        """Execute a write query with error handling."""
        try:
            async with self._driver.session() as session:
                await session.run(query, params)
        except Exception as exc:
            logger.error(
                f"Graph write failed: {operation}",
                extra={"operation": operation, "error": str(exc)},
            )
            raise GraphWriteError(f"{operation} failed: {exc}") from exc

    async def _read_nodes(
        self, query: str, params: dict[str, Any], node_var: str
    ) -> list[dict[str, Any]]:
        """Execute a read query and return a list of node property dicts."""
        async with self._driver.session() as session:
            result = await session.run(query, params)
            records = [record async for record in result]
        return [dict(record[node_var]) for record in records]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _required_env(name: str) -> str:
    """Read a required environment variable or raise."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value
