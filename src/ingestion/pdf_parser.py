"""Parse scientific PDFs into structured paper chunks."""

import asyncio
import io
import logging
import re
from dataclasses import dataclass

import fitz
import pdfplumber

logger = logging.getLogger(__name__)

DEFAULT_MAX_CHUNK_TOKENS = 500
DEFAULT_CHUNK_OVERLAP_TOKENS = 50
MIN_EXTRACTED_TEXT_CHARS = 100
UNKNOWN_SECTION = "unknown"

SECTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("abstract", re.compile(r"^(?:\d+(?:\.\d+)*\.?\s+)?abstract[.:]?$", re.I)),
    (
        "intro",
        re.compile(
            r"^(?:\d+(?:\.\d+)*\.?\s+)?(?:introduction|background)[.:]?$",
            re.I,
        ),
    ),
    (
        "methods",
        re.compile(
            r"^(?:\d+(?:\.\d+)*\.?\s+)?"
            r"(?:methods?|materials\s+(?:and|&)\s+methods|methodology|experimental\s+setup)"
            r"[.:]?$",
            re.I,
        ),
    ),
    (
        "results",
        re.compile(r"^(?:\d+(?:\.\d+)*\.?\s+)?(?:results?|findings)[.:]?$", re.I),
    ),
    (
        "discussion",
        re.compile(
            r"^(?:\d+(?:\.\d+)*\.?\s+)?(?:discussion|conclusions?|limitations?)[.:]?$",
            re.I,
        ),
    ),
)


class PDFParsingError(Exception):
    """Raised when a PDF cannot be parsed into text chunks."""


@dataclass(frozen=True, slots=True)
class PaperChunk:
    """A chunk of paper text with section and page metadata."""

    paper_id: str
    chunk_index: int
    text: str
    section: str
    token_count: int
    page_numbers: list[int]


@dataclass(frozen=True, slots=True)
class _PageText:
    page_number: int
    text: str


@dataclass(slots=True)
class _SectionTokens:
    section: str
    tokens: list[str]
    page_numbers: list[int]

    def add_line(self, line: str, page_number: int) -> None:
        """Add a line of text to this section."""
        tokens = _tokenize(line)
        self.tokens.extend(tokens)
        self.page_numbers.extend([page_number] * len(tokens))


async def parse_pdf(
    pdf_bytes: bytes,
    paper_id: str,
    max_tokens: int = DEFAULT_MAX_CHUNK_TOKENS,
    overlap_tokens: int = DEFAULT_CHUNK_OVERLAP_TOKENS,
) -> list[PaperChunk]:
    """Parse PDF bytes without blocking the event loop."""
    return await asyncio.to_thread(
        parse_pdf_bytes,
        pdf_bytes,
        paper_id,
        max_tokens,
        overlap_tokens,
    )


def parse_pdf_bytes(
    pdf_bytes: bytes,
    paper_id: str,
    max_tokens: int = DEFAULT_MAX_CHUNK_TOKENS,
    overlap_tokens: int = DEFAULT_CHUNK_OVERLAP_TOKENS,
) -> list[PaperChunk]:
    """Parse PDF bytes into section-aware chunks."""
    if not pdf_bytes:
        raise PDFParsingError("PDF bytes are empty.")

    try:
        pages = _extract_pages_with_fitz(pdf_bytes)
    except (RuntimeError, ValueError, fitz.FileDataError) as exc:
        logger.warning(
            "PyMuPDF parsing failed; falling back to pdfplumber",
            extra={"paper_id": paper_id, "error": str(exc)},
        )
        pages = _extract_pages_with_pdfplumber(pdf_bytes)

    if _text_length(pages) < MIN_EXTRACTED_TEXT_CHARS:
        logger.warning(
            "PyMuPDF extracted little text; falling back to pdfplumber",
            extra={"paper_id": paper_id},
        )
        pages = _extract_pages_with_pdfplumber(pdf_bytes)

    if _text_length(pages) < MIN_EXTRACTED_TEXT_CHARS:
        logger.warning(
            "PDF appears scanned or empty; no chunks generated",
            extra={"paper_id": paper_id},
        )
        return []

    sections = _collect_sections(pages)
    return _build_chunks(paper_id, sections, max_tokens, overlap_tokens)


def _extract_pages_with_fitz(pdf_bytes: bytes) -> list[_PageText]:
    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        return [
            _PageText(page_number=index + 1, text=page.get_text("text") or "")
            for index, page in enumerate(document)
        ]
    finally:
        document.close()


def _extract_pages_with_pdfplumber(pdf_bytes: bytes) -> list[_PageText]:
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            return [
                _PageText(page_number=index + 1, text=page.extract_text() or "")
                for index, page in enumerate(pdf.pages)
            ]
    except (RuntimeError, ValueError, OSError) as exc:
        raise PDFParsingError("PDF fallback parsing failed.") from exc


def _collect_sections(pages: list[_PageText]) -> list[_SectionTokens]:
    current = _SectionTokens(section=UNKNOWN_SECTION, tokens=[], page_numbers=[])
    sections: list[_SectionTokens] = [current]

    for page in pages:
        for raw_line in page.text.splitlines():
            line = _normalize_line(raw_line)
            if not line:
                continue

            section = _classify_section_header(line)
            if section is not None:
                current = _SectionTokens(section=section, tokens=[], page_numbers=[])
                sections.append(current)
                continue

            current.add_line(line, page.page_number)

    return [section for section in sections if section.tokens]


def _build_chunks(
    paper_id: str,
    sections: list[_SectionTokens],
    max_tokens: int,
    overlap_tokens: int,
) -> list[PaperChunk]:
    if max_tokens <= 0:
        raise ValueError("max_tokens must be greater than zero.")
    if overlap_tokens < 0 or overlap_tokens >= max_tokens:
        raise ValueError(
            "overlap_tokens must be non-negative and smaller than max_tokens."
        )

    chunks: list[PaperChunk] = []
    stride = max_tokens - overlap_tokens

    for section in sections:
        start = 0
        while start < len(section.tokens):
            end = min(start + max_tokens, len(section.tokens))
            chunk_tokens = section.tokens[start:end]
            page_numbers = sorted(set(section.page_numbers[start:end]))
            chunks.append(
                PaperChunk(
                    paper_id=paper_id,
                    chunk_index=len(chunks),
                    text=" ".join(chunk_tokens),
                    section=section.section,
                    token_count=len(chunk_tokens),
                    page_numbers=page_numbers,
                )
            )

            if end == len(section.tokens):
                break
            start += stride

    return chunks


def _classify_section_header(line: str) -> str | None:
    if len(line) > 96:
        return None

    for section, pattern in SECTION_PATTERNS:
        if pattern.match(line):
            return section
    return None


def _normalize_line(line: str) -> str:
    return " ".join(line.strip().split())


def _tokenize(text: str) -> list[str]:
    return text.split()


def _text_length(pages: list[_PageText]) -> int:
    return sum(len(page.text.strip()) for page in pages)
