"""
Calls Gemini to analyze the document and
returns a repository plan in JSON format.
"""

import logging
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

from converter.dto import document_to_json
from converter.parser import parse_ai_response
from converter.prompt import SYSTEM_PROMPT
from models.document import Document

logger = logging.getLogger(__name__)

load_dotenv()

client = None


def _get_client():
    global client
    if client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GEMINI_API_KEY environment variable is not set. "
                "Please configure GEMINI_API_KEY in your Vercel Project Environment Variables."
            )
        client = genai.Client(api_key=api_key)
    return client

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
MAX_RETRIES = int(os.getenv("GEMINI_MAX_RETRIES", "3"))

# Errors that should NOT trigger a retry (bad data, not transient)
_NON_RETRYABLE = (ValueError, TypeError, KeyError)


def _slice_document(document: Document, start_idx: int, end_idx: int) -> Document:
    """Creates a lightweight sub-Document slice for a subset of pages [start_idx, end_idx)."""
    sliced_pages = document.pages[start_idx:end_idx]
    slice_doc = Document(
        filename=document.filename,
        filepath=document.filepath,
        page_count=len(sliced_pages),
        metadata=document.metadata,
    )
    slice_doc.pages = sliced_pages
    slice_doc.raw_text = "\n".join(p.raw_text for p in sliced_pages)
    return slice_doc


def _analyze_single_doc(document: Document) -> dict:
    """Sends a single Document (or Document slice) to Gemini with retry logic."""
    document_json = document_to_json(document)
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                f"Calling Gemini ({GEMINI_MODEL}), "
                f"attempt {attempt}/{MAX_RETRIES}"
            )

            response = _get_client().models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    SYSTEM_PROMPT,
                    document_json
                ],
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json",
                )
            )

            return parse_ai_response(response.text)

        except _NON_RETRYABLE as e:
            # Parse/schema errors — fail immediately, no retry
            logger.error(f"Non-retryable error: {e}")
            raise

        except Exception as e:
            last_error = e
            logger.warning(
                f"Gemini attempt {attempt}/{MAX_RETRIES} failed: {e}"
            )

            if attempt < MAX_RETRIES:
                wait = 2 ** attempt  # Exponential backoff: 2s, 4s
                logger.info(f"Retrying in {wait}s...")
                time.sleep(wait)

    raise RuntimeError(
        f"Gemini API failed after {MAX_RETRIES} attempts: {last_error}"
    ) from last_error


def _merge_chunk_analyses(chunk_analyses: list[dict]) -> dict:
    """
    Merges structural analyses from multiple chunk responses.
    Stitches continuous knowledge units across chunk boundaries if titles match.
    """
    if not chunk_analyses:
        return {"knowledge_units": []}

    first = chunk_analyses[0]
    merged = {
        "repository_title": first.get("repository_title", "Document Repository"),
        "document_type": first.get("document_type", "document"),
        "language": first.get("language", "en"),
        "knowledge_units": []
    }

    merged_units = []

    for analysis in chunk_analyses:
        units = analysis.get("knowledge_units", [])
        for unit in units:
            if not merged_units:
                merged_units.append(dict(unit))
                continue

            last_unit = merged_units[-1]
            # Check if this unit is a boundary continuation of the previous unit
            same_title = unit.get("title") and unit.get("title").strip().lower() == last_unit.get("title", "").strip().lower()

            if same_title:
                # Boundary Stitching: append segments and update end_page
                last_unit["segments"] = last_unit.get("segments", []) + unit.get("segments", [])
                if "end_page" in unit:
                    last_unit["end_page"] = max(last_unit.get("end_page", 0), unit["end_page"])
                # Merge relationships
                existing_rel_targets = {r.get("target") for r in last_unit.get("relationships", [])}
                for rel in unit.get("relationships", []):
                    if rel.get("target") not in existing_rel_targets:
                        last_unit.setdefault("relationships", []).append(rel)
                        existing_rel_targets.add(rel.get("target"))
            else:
                merged_units.append(dict(unit))

    merged["knowledge_units"] = merged_units
    return merged


def analyze_document(document: Document) -> dict:
    """
    Sends the document to Gemini with retry and page-chunking logic.

    If document page_count > GEMINI_BATCH_SIZE_PAGES, splits processing into
    page-window chunks with configurable delay to respect Free Tier API rate limits.
    """
    batch_size = int(os.getenv("GEMINI_BATCH_SIZE_PAGES", "15"))
    overlap = int(os.getenv("GEMINI_BATCH_OVERLAP_PAGES", "1"))
    delay = float(os.getenv("GEMINI_BATCH_DELAY_SEC", "1.0"))

    # Single-pass for documents within batch size
    if document.page_count <= batch_size:
        return _analyze_single_doc(document)

    logger.info(
        f"Document has {document.page_count} pages. "
        f"Enabling chunked processing (batch_size={batch_size}, overlap={overlap})."
    )

    chunks = []
    step = batch_size - overlap if batch_size > overlap else 1
    start_idx = 0

    while start_idx < document.page_count:
        end_idx = min(start_idx + batch_size, document.page_count)
        chunks.append((start_idx, end_idx))
        if end_idx == document.page_count:
            break
        start_idx += step

    logger.info(f"Split document into {len(chunks)} processing chunks: {chunks}")

    chunk_analyses = []
    for idx, (s, e) in enumerate(chunks, start=1):
        logger.info(f"Processing chunk {idx}/{len(chunks)} (pages {s+1} to {e})...")
        slice_doc = _slice_document(document, s, e)
        chunk_res = _analyze_single_doc(slice_doc)
        chunk_analyses.append(chunk_res)

        if idx < len(chunks) and delay > 0:
            logger.info(f"Waiting {delay:.1f}s between API calls for rate-limit protection...")
            time.sleep(delay)

    merged_analysis = _merge_chunk_analyses(chunk_analyses)
    logger.info(
        f"Successfully merged {len(chunk_analyses)} chunks into "
        f"{len(merged_analysis.get('knowledge_units', []))} knowledge units."
    )
    return merged_analysis