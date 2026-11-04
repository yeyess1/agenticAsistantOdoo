"""Document endpoints: upload, list, get, delete (I-01, I-06)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

import httpx
from common.schemas.documents import DocumentList, DocumentOut, DocumentStatus, IngestResult
from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile, status

from ingestion.parsers import ParseError, UnsupportedTypeError
from ingestion.pipeline import DocumentDeletedError, IngestionPipeline

router = APIRouter(prefix="/documents", tags=["documents"])


def _pipeline(request: Request) -> IngestionPipeline:
    pipeline: IngestionPipeline = request.app.state.pipeline
    return pipeline


def _error(code: int, kind: str, message: str) -> HTTPException:
    return HTTPException(code, detail={"error": {"code": kind, "message": message}})


@router.post(
    "",
    response_model=IngestResult,
    summary="Ingest a PDF, TXT or MD document",
    responses={409: {}, 413: {}, 415: {}, 422: {}, 502: {}},
)
async def upload_document(
    request: Request,
    file: Annotated[UploadFile, File(description=".pdf, .md or .txt")],
    source_url: Annotated[str | None, Form(description="Canonical URL of the document")] = None,
    force: Annotated[bool, Form(description="Reindex even if the content is unchanged")] = False,
) -> IngestResult:
    settings = request.app.state.settings
    limit = settings.max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise _error(413, "file_too_large", f"file exceeds {settings.max_upload_mb} MB")
    filename = file.filename or "upload"
    try:
        return await _pipeline(request).ingest(
            data, filename, source_url=source_url or None, force=force
        )
    except DocumentDeletedError as exc:
        raise _error(409, "document_deleted_during_ingestion", str(exc)) from exc
    except UnsupportedTypeError as exc:
        raise _error(415, "unsupported_type", str(exc)) from exc
    except (ParseError, ValueError) as exc:
        raise _error(422, "unprocessable_document", str(exc)) from exc
    except httpx.HTTPError as exc:
        raise _error(502, "embeddings_unavailable", f"embedding service failed: {exc}") from exc


@router.get("", response_model=DocumentList, summary="List indexed documents")
async def list_documents(
    request: Request,
    status_filter: Annotated[DocumentStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DocumentList:
    items, total = await request.app.state.repo.list(
        status=status_filter, limit=limit, offset=offset
    )
    return DocumentList(items=items, total=total)


@router.get("/{doc_id}", response_model=DocumentOut, summary="Get one document")
async def get_document(request: Request, doc_id: UUID) -> DocumentOut:
    doc: DocumentOut | None = await request.app.state.repo.get(doc_id)
    if doc is None:
        raise _error(404, "not_found", f"document {doc_id} not found")
    return doc


@router.delete(
    "/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document: its Qdrant points and its registry row",
)
async def delete_document(request: Request, doc_id: UUID) -> None:
    if not await _pipeline(request).delete_document(doc_id):
        raise _error(404, "not_found", f"document {doc_id} not found")
