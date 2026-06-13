"""POST /upload - accept a PDF and launch the processing pipeline."""

import asyncio
import logging
import uuid

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from src.api.models import UploadResponse
from src.graph.schema import Paper, PipelineStatus

logger = logging.getLogger(__name__)

router = APIRouter(tags=["upload"])


from src.api.limiter import limiter

@router.post("/upload", response_model=UploadResponse)
@limiter.limit("5/minute")
async def upload_pdf(request: Request, file: UploadFile = File(...)) -> UploadResponse:
    """Accept a PDF upload, create a Paper node, and kick off the pipeline.

    The cartographer pipeline runs as a fire-and-forget ``asyncio.Task``
    so the client gets an immediate response with the ``paper_id``.
    """
    # Validate file type
    if file.content_type and file.content_type != "application/pdf":
        if not (file.filename and file.filename.lower().endswith(".pdf")):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are accepted.",
            )

    # Read bytes
    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Generate identifiers
    paper_id = str(uuid.uuid4())
    filename = file.filename or "untitled.pdf"

    logger.info(
        "PDF upload received",
        extra={"paper_id": paper_id, "original_filename": filename, "size": len(pdf_bytes)},
    )

    # Create Paper node in Neo4j
    graph_manager = request.app.state.graph_manager
    paper = Paper(
        id=paper_id,
        title=filename.removesuffix(".pdf"),
        authors=[],
        status=PipelineStatus.QUEUED.value,
    )
    await graph_manager.add_paper(paper)

    # Emit initial status via WebSocket
    emitter = request.app.state.emitter
    await emitter.emit_paper_status(paper_id, PipelineStatus.QUEUED.value)

    # Launch pipeline as background task
    cartographer = request.app.state.cartographer
    task = asyncio.create_task(
        _run_pipeline(
            cartographer,
            paper_id,
            pdf_bytes,
            filename.removesuffix(".pdf"),
            graph_manager,
            emitter,
        ),
        name=f"pipeline-{paper_id}",
    )

    # Store the task on app.state so it can be inspected / cancelled
    if not hasattr(request.app.state, "pipeline_tasks"):
        request.app.state.pipeline_tasks = {}
    request.app.state.pipeline_tasks[paper_id] = task

    return UploadResponse(paper_id=paper_id, status=PipelineStatus.QUEUED.value)


async def _run_pipeline(
    cartographer,
    paper_id: str,
    pdf_bytes: bytes,
    title: str,
    graph_manager,
    emitter,
) -> None:
    """Run the full cartographer pipeline, catching any top-level error.

    This function is intentionally broad in its exception handling because
    it runs as a detached task - an unhandled exception would be silently
    swallowed by the event loop.
    """
    try:
        await cartographer.process_paper(paper_id, pdf_bytes, title=title)
    except Exception:
        logger.exception(
            "Pipeline failed for paper %s", paper_id, extra={"paper_id": paper_id}
        )
        try:
            await graph_manager.update_paper_status(paper_id, PipelineStatus.ERROR.value)
            await emitter.emit_paper_status(paper_id, PipelineStatus.ERROR.value)
        except Exception:
            logger.exception("Failed to record error status for paper %s", paper_id)
