"""Upload parsed paper chunks to Azure AI Foundry IQ."""

import asyncio
import logging
import os
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import httpx

from src.ingestion.pdf_parser import PaperChunk

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_INDEXING_BACKOFF_SECONDS = (2.0, 4.0, 8.0, 16.0, 32.0)
DOCUMENTS_PATH_TEMPLATE = "/knowledge-base/{knowledge_base_id}/documents"
STATUS_PATH_TEMPLATE = "/knowledge-base/{knowledge_base_id}/status"
READY_STATUSES = {"ready", "succeeded", "indexed"}
FAILED_STATUSES = {"failed", "error"}


class FoundryUploadError(Exception):
    """Raised when chunks cannot be uploaded to Foundry IQ."""


class FoundryIndexingTimeoutError(Exception):
    """Raised when Foundry IQ indexing does not finish in time."""


@dataclass(frozen=True, slots=True)
class FoundryUploadResult:
    """Result returned after chunks are uploaded and indexed."""

    paper_id: str
    chunk_count: int
    document_ids: list[str]
    status: str


class FoundryIQUploader:
    """Async client for uploading paper chunks to Foundry IQ."""

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        knowledge_base_id: str,
        client: httpx.AsyncClient | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.knowledge_base_id = knowledge_base_id
        self.client = client
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_env(cls) -> "FoundryIQUploader":
        """Create an uploader from environment variables."""
        endpoint = _required_env("AZURE_FOUNDRY_IQ_ENDPOINT")
        api_key = _required_env("AZURE_FOUNDRY_IQ_KEY")
        knowledge_base_id = _required_env("AZURE_FOUNDRY_IQ_KB_ID")
        return cls(
            endpoint=endpoint,
            api_key=api_key,
            knowledge_base_id=knowledge_base_id,
        )

    async def upload_chunks(
        self,
        chunks: Sequence[PaperChunk],
        wait_for_indexing: bool = True,
    ) -> FoundryUploadResult:
        """Upload chunks and optionally wait until the knowledge base is ready."""
        if not chunks:
            return FoundryUploadResult(
                paper_id="",
                chunk_count=0,
                document_ids=[],
                status="no_chunks",
            )

        paper_id = _validate_single_paper(chunks)
        payload = {"documents": [self._chunk_to_document(chunk) for chunk in chunks]}

        async with self._client_context() as client:
            document_ids = await self._post_documents(client, payload, paper_id)
            status = "uploaded"
            if wait_for_indexing:
                status = await self.wait_until_ready(client, paper_id)

        logger.info(
            "Uploaded chunks to Foundry IQ",
            extra={
                "paper_id": paper_id,
                "chunk_count": len(chunks),
                "status": status,
            },
        )
        return FoundryUploadResult(
            paper_id=paper_id,
            chunk_count=len(chunks),
            document_ids=document_ids,
            status=status,
        )

    async def wait_until_ready(
        self,
        client: httpx.AsyncClient | None = None,
        paper_id: str | None = None,
        backoff_seconds: Sequence[float] = DEFAULT_INDEXING_BACKOFF_SECONDS,
    ) -> str:
        """Poll Foundry IQ until indexing is ready or fails."""
        async with self._client_context(client) as active_client:
            for delay_seconds in backoff_seconds:
                status = await self._get_status(active_client)
                normalized_status = status.lower()

                if normalized_status in READY_STATUSES:
                    return status
                if normalized_status in FAILED_STATUSES:
                    raise FoundryUploadError(f"Foundry IQ indexing failed: {status}")

                logger.info(
                    "Waiting for Foundry IQ indexing",
                    extra={"paper_id": paper_id, "status": status},
                )
                await asyncio.sleep(delay_seconds)

        raise FoundryIndexingTimeoutError("Foundry IQ indexing did not finish in time.")

    async def _post_documents(
        self,
        client: httpx.AsyncClient,
        payload: dict[str, Any],
        paper_id: str,
    ) -> list[str]:
        try:
            response = await client.post(
                self._url(DOCUMENTS_PATH_TEMPLATE),
                json=payload,
                headers=self._headers(),
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise FoundryUploadError(
                f"Foundry IQ upload failed with status {exc.response.status_code}."
            ) from exc
        except httpx.RequestError as exc:
            raise FoundryUploadError("Foundry IQ upload request failed.") from exc

        response_data = response.json()
        document_ids = _extract_document_ids(response_data, payload)
        logger.info(
            "Foundry IQ accepted chunk documents",
            extra={"paper_id": paper_id, "document_count": len(document_ids)},
        )
        return document_ids

    async def _get_status(self, client: httpx.AsyncClient) -> str:
        try:
            response = await client.get(
                self._url(STATUS_PATH_TEMPLATE),
                headers=self._headers(),
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise FoundryUploadError(
                f"Foundry IQ status check failed with status {exc.response.status_code}."
            ) from exc
        except httpx.RequestError as exc:
            raise FoundryUploadError("Foundry IQ status request failed.") from exc

        response_data = response.json()
        return str(response_data.get("status", "unknown"))

    def _chunk_to_document(self, chunk: PaperChunk) -> dict[str, Any]:
        document_id = f"{chunk.paper_id}:{chunk.chunk_index}"
        return {
            "id": document_id,
            "content": chunk.text,
            "metadata": {
                "paper_id": chunk.paper_id,
                "chunk_index": chunk.chunk_index,
                "section": chunk.section,
                "token_count": chunk.token_count,
                "page_numbers": chunk.page_numbers,
            },
        }

    def _url(self, path_template: str) -> str:
        path = path_template.format(knowledge_base_id=self.knowledge_base_id)
        return f"{self.endpoint}{path}"

    def _headers(self) -> dict[str, str]:
        return {
            "api-key": self.api_key,
            "Content-Type": "application/json",
        }

    @asynccontextmanager
    async def _client_context(
        self,
        override_client: httpx.AsyncClient | None = None,
    ) -> AsyncIterator[httpx.AsyncClient]:
        if override_client is not None:
            yield override_client
            return
        if self.client is not None:
            yield self.client
            return

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            yield client


def _validate_single_paper(chunks: Sequence[PaperChunk]) -> str:
    paper_ids = {chunk.paper_id for chunk in chunks}
    if len(paper_ids) != 1:
        raise ValueError("All chunks in one upload must belong to the same paper.")
    return next(iter(paper_ids))


def _extract_document_ids(
    response_data: dict[str, Any],
    payload: dict[str, Any],
) -> list[str]:
    documents = response_data.get("documents")
    if isinstance(documents, list):
        document_ids = [
            str(document["id"])
            for document in documents
            if isinstance(document, dict) and "id" in document
        ]
        if document_ids:
            return document_ids

    return [str(document["id"]) for document in payload["documents"]]


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise FoundryUploadError(f"Missing required environment variable: {name}")
    return value
