"""
Converts internal Document models into text payloads
that can be sent to the AI for Markdown conversion.
"""

import json

from models.document import Document


def document_to_dict(document: Document) -> dict:
    """
    Convert a Document into a JSON-friendly dictionary.
    Sends chunk-level data for semantic mapping.
    """

    return {
        "filename": document.filename,
        "page_count": document.page_count,
        "metadata": document.metadata,
        "chunks": [
            {
                "chunk_id": chunk.chunk_id,
                "heading": chunk.heading,
                "chunk_type": chunk.chunk_type,
                "suggested_type": chunk.suggested_type,
                "content_preview": chunk.content[:500],
                "page_range": f"{chunk.page_start}-{chunk.page_end}",
            }
            for chunk in document.chunks
        ]
    }


def document_to_json(document: Document) -> str:
    """
    Convert the document into formatted JSON text.
    """

    return json.dumps(
        document_to_dict(document),
        indent=2,
        ensure_ascii=False
    )
