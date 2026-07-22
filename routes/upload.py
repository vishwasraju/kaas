import os
import re
import shutil
import uuid
import logging

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel

from pipeline import process_pdf
from writer.writer import cleanup_temp_dir
from rag.rag_pipeline import _sessions

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

ALLOWED_EXTENSIONS = {".pdf"}

class RAGQuery(BaseModel):
    session_id: str
    question: str

def _sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal."""
    # Extract just the basename (strip any directory components)
    basename = os.path.basename(filename)
    # Remove unsafe characters
    safe = re.sub(r'[^a-zA-Z0-9._-]', '_', basename)
    # Prepend UUID to prevent collisions
    return f"{uuid.uuid4().hex[:8]}_{safe}"


def _validate_file(pdf: UploadFile) -> None:
    """Validate uploaded file type and size."""
    # Check extension
    filename = pdf.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{ext}'. Only PDF files are accepted."
        )

    # Check content type
    if pdf.content_type and "pdf" not in pdf.content_type.lower():
        raise HTTPException(
            status_code=400,
            detail="Invalid content type. Only PDF files are accepted."
        )


@router.post("/upload")
def upload_pdf(pdf: UploadFile = File(...), mode: str = Form("okf")):
    """
    Upload a PDF and process based on mode.
    """

    # Validate file type
    _validate_file(pdf)

    # Save uploaded file with sanitized name in system temp directory (for serverless environments)
    import tempfile
    temp_dir = tempfile.gettempdir()
    safe_name = _sanitize_filename(pdf.filename or "upload.pdf")
    file_path = os.path.join(temp_dir, safe_name)

    # Write with size limit check
    bytes_written = 0
    with open(file_path, "wb") as buffer:
        while chunk := pdf.file.read(8192):
            bytes_written += len(chunk)
            if bytes_written > MAX_UPLOAD_SIZE_BYTES:
                buffer.close()
                os.remove(file_path)
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE_MB}MB."
                )
            buffer.write(chunk)

    zip_path = None
    try:
        # Run extraction pipeline
        logger.info("Processing PDF: %s with mode: %s", safe_name, mode)
        result = process_pdf(file_path, mode=mode)
        
        if mode == "rag":
            _, document, session_id = result
            return {
                "success": True,
                "mode": "rag",
                "session_id": session_id,
                "document_title": document.filename,
                "chunk_count": _sessions[session_id].vector_store.collection.count() if _sessions.get(session_id) and _sessions[session_id].vector_store.collection else 0
            }
            
        if mode == "rag-okf":
            zip_path, repository, session_id = result
        else:
            zip_path, repository = result
            session_id = None

        import base64
        with open(zip_path, "rb") as f:
            zip_bytes = f.read()
        zip_base64 = base64.b64encode(zip_bytes).decode("utf-8")

        files_data = []
        for okf in repository.files:
            files_data.append({
                "path": okf.path,
                "title": okf.title,
                "type": okf.type,
                "description": okf.description,
                "content": okf.content,
                "tags": okf.tags,
                "relationships": okf.relationships,
                "citations": okf.citations,
            })

        response = {
            "success": True,
            "repository_title": repository.title,
            "zip_base64": zip_base64,
            "files": files_data
        }
        
        if mode == "rag-okf":
            response["mode"] = "rag-okf"
            response["session_id"] = session_id
            response["chunk_count"] = _sessions[session_id].vector_store.collection.count() if _sessions.get(session_id) and _sessions[session_id].vector_store.collection else 0
            
        return response

    except HTTPException:
        raise

    except Exception as e:
        logger.error("Extraction failed for %s: %s", safe_name, e)
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

    finally:
        # Clean up uploaded file
        if os.path.exists(file_path):
            os.remove(file_path)
        # Clean up temp directory from write_zip
        if zip_path:
            cleanup_temp_dir(zip_path)

@router.post("/api/rag/query")
def rag_query(query: RAGQuery):
    """Query a RAG session."""
    session_id = query.session_id
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    try:
        pipeline = _sessions[session_id]
        return pipeline.query(query.question)
    except Exception as e:
        logger.error(f"RAG query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
@router.delete("/api/rag/session/{session_id}")
def delete_rag_session(session_id: str):
    """Clean up a RAG session."""
    if session_id in _sessions:
        del _sessions[session_id]
        return {"success": True, "message": "Session deleted"}
    raise HTTPException(status_code=404, detail="Session not found")