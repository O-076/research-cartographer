"""Shared base class for all Research Cartographer agents.

Every agent inherits from ``BaseAgent`` which provides:
- Azure OpenAI client (chat + embeddings)
- Foundry IQ query wrapper with retry / exponential backoff
- Structured JSON output parsing with Pydantic validation
- Correlation-aware logging
"""

import asyncio
import json
import logging
import os
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

DEFAULT_TIMEOUT_SECONDS = 60.0
MAX_RETRIES = 3
BACKOFF_MIN_SECONDS = 1
BACKOFF_MAX_SECONDS = 16


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class ExtractionError(Exception):
    """Raised when claim extraction fails."""


class FoundryQueryError(Exception):
    """Raised when a Foundry IQ query fails."""


class LLMResponseError(Exception):
    """Raised when the LLM returns unparseable output."""


# ---------------------------------------------------------------------------
# Base agent
# ---------------------------------------------------------------------------

class BaseAgent:
    """Abstract base for all Research Cartographer agents.

    Sub-classes must define ``SYSTEM_PROMPT`` as a class attribute.
    """

    SYSTEM_PROMPT: str = ""

    def __init__(
        self,
        azure_openai_endpoint: str | None = None,
        azure_openai_key: str | None = None,
        azure_openai_deployment: str | None = None,
        azure_openai_embedding_deployment: str | None = None,
        foundry_iq_endpoint: str | None = None,
        foundry_iq_key: str | None = None,
        foundry_iq_kb_id: str | None = None,
    ) -> None:
        self._openai_endpoint = (
            azure_openai_endpoint or _required_env("AZURE_OPENAI_ENDPOINT")
        ).rstrip("/")
        self._openai_key = azure_openai_key or _required_env("AZURE_OPENAI_KEY")
        self._openai_deployment = (
            azure_openai_deployment or _required_env("AZURE_OPENAI_DEPLOYMENT")
        )
        self._embedding_deployment = (
            azure_openai_embedding_deployment
            or _required_env("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
        )
        self._foundry_endpoint = (
            foundry_iq_endpoint or _required_env("AZURE_FOUNDRY_IQ_ENDPOINT")
        ).rstrip("/")
        self._foundry_key = foundry_iq_key or _required_env("AZURE_FOUNDRY_IQ_KEY")
        self._foundry_kb_id = foundry_iq_kb_id or _required_env("AZURE_FOUNDRY_IQ_KB_ID")

        self._http_client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazily create a shared async HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS)
        return self._http_client

    async def close(self) -> None:
        """Release the underlying HTTP client."""
        if self._http_client is not None and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None

    # ------------------------------------------------------------------
    # Azure OpenAI — Chat Completion
    # ------------------------------------------------------------------

    @retry(
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(
            multiplier=1, min=BACKOFF_MIN_SECONDS, max=BACKOFF_MAX_SECONDS
        ),
        reraise=True,
    )
    async def chat_completion(
        self,
        user_prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        json_mode: bool = True,
    ) -> str:
        """Send a chat completion request to Azure OpenAI.

        Returns the raw text content of the first choice.
        """
        system = system_prompt or self.SYSTEM_PROMPT
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ]

        body: dict[str, Any] = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}

        url = (
            f"{self._openai_endpoint}/openai/deployments/"
            f"{self._openai_deployment}/chat/completions"
            "?api-version=2024-06-01"
        )
        headers = {
            "api-key": self._openai_key,
            "Content-Type": "application/json",
        }

        client = await self._get_client()
        response = await client.post(url, json=body, headers=headers)
        response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        logger.debug("LLM raw response", extra={"response_length": len(content)})
        return content

    # ------------------------------------------------------------------
    # Azure OpenAI — Embeddings
    # ------------------------------------------------------------------

    @retry(
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(
            multiplier=1, min=BACKOFF_MIN_SECONDS, max=BACKOFF_MAX_SECONDS
        ),
        reraise=True,
    )
    async def get_embedding(self, text: str) -> list[float]:
        """Generate a single embedding via Azure OpenAI text-embedding-3-large."""
        url = (
            f"{self._openai_endpoint}/openai/deployments/"
            f"{self._embedding_deployment}/embeddings"
            "?api-version=2024-06-01"
        )
        headers = {
            "api-key": self._openai_key,
            "Content-Type": "application/json",
        }
        body = {"input": text}

        client = await self._get_client()
        response = await client.post(url, json=body, headers=headers)
        response.raise_for_status()

        data = response.json()
        embedding: list[float] = data["data"][0]["embedding"]
        return embedding

    async def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts in parallel."""
        tasks = [self.get_embedding(text) for text in texts]
        return await asyncio.gather(*tasks)

    # ------------------------------------------------------------------
    # Foundry IQ — Knowledge Base Query
    # ------------------------------------------------------------------

    @retry(
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(
            multiplier=1, min=BACKOFF_MIN_SECONDS, max=BACKOFF_MAX_SECONDS
        ),
        reraise=True,
    )
    async def query_foundry_iq(
        self,
        query: str,
        paper_id: str | None = None,
        section: str | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Query the Foundry IQ knowledge base.

        Optionally filter by paper_id and/or section.
        """
        url = (
            f"{self._foundry_endpoint}"
            f"/knowledge-base/{self._foundry_kb_id}/query"
        )
        headers = {
            "api-key": self._foundry_key,
            "Content-Type": "application/json",
        }

        body: dict[str, Any] = {"query": query, "top": top_k}

        filters: dict[str, str] = {}
        if paper_id:
            filters["paper_id"] = paper_id
        if section:
            filters["section"] = section
        if filters:
            body["filter"] = filters

        client = await self._get_client()
        response = await client.post(url, json=body, headers=headers)
        response.raise_for_status()

        data = response.json()
        results: list[dict[str, Any]] = data.get("results", data.get("value", []))
        logger.info(
            "Foundry IQ query returned results",
            extra={
                "query_length": len(query),
                "paper_id": paper_id,
                "result_count": len(results),
            },
        )
        return results

    # ------------------------------------------------------------------
    # Structured JSON parsing
    # ------------------------------------------------------------------

    def parse_json_response(
        self, raw: str, model_class: type[T]
    ) -> T:
        """Parse raw LLM text into a validated Pydantic model.

        Strips markdown fences and attempts JSON parsing.
        """
        cleaned = _strip_markdown_fences(raw).strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise LLMResponseError(
                f"LLM output is not valid JSON: {cleaned[:200]}"
            ) from exc

        try:
            return model_class.model_validate(parsed)
        except ValidationError as exc:
            raise LLMResponseError(
                f"LLM JSON does not match schema {model_class.__name__}: {exc}"
            ) from exc

    def parse_json_list(
        self, raw: str, item_model: type[T], list_key: str | None = None
    ) -> list[T]:
        """Parse raw LLM text into a list of validated Pydantic models.

        If ``list_key`` is provided, extracts the list from that key in the
        JSON object; otherwise the top-level value must be a list.
        """
        cleaned = _strip_markdown_fences(raw).strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise LLMResponseError(
                f"LLM output is not valid JSON: {cleaned[:200]}"
            ) from exc

        if list_key and isinstance(parsed, dict):
            parsed = parsed.get(list_key, [])

        if not isinstance(parsed, list):
            raise LLMResponseError(
                f"Expected a JSON array, got {type(parsed).__name__}"
            )

        items: list[T] = []
        for i, entry in enumerate(parsed):
            try:
                items.append(item_model.model_validate(entry))
            except ValidationError as exc:
                logger.warning(
                    "Skipping invalid item in LLM list",
                    extra={"index": i, "error": str(exc)},
                )
        return items

    # ------------------------------------------------------------------
    # Cosine similarity (numpy-free for lightweight usage)
    # ------------------------------------------------------------------

    @staticmethod
    def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(vec_a) != len(vec_b) or not vec_a:
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = sum(a * a for a in vec_a) ** 0.5
        norm_b = sum(b * b for b in vec_b) ** 0.5
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _required_env(name: str) -> str:
    """Read a required environment variable or raise."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` fences from LLM responses."""
    stripped = text.strip()
    if stripped.startswith("```"):
        first_newline = stripped.index("\n")
        stripped = stripped[first_newline + 1 :]
    if stripped.endswith("```"):
        stripped = stripped[:-3]
    return stripped.strip()
