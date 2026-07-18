"""
Converts internal Document models into text payloads
that can be sent to the AI for Markdown conversion.
"""

import json

from models.document import Document


def document_to_dict(document: Document) -> dict:
    """
    Convert a Document into a JSON-friendly dictionary.
    Sends paragraph-level data for precise segment mapping.
    Includes supplementary table and link data per page.
    """

    return {
        "filename": document.filename,
        "page_count": document.page_count,
        "metadata": document.metadata,
        "pages": [
            {
                "page_number": page.page_number,
                "paragraphs": [
                    {"index": p.index, "text": p.text}
                    for p in page.paragraphs
                ],
                "tables": page.tables,
                "links": page.links,
                "has_images": page.has_images,
            }
            for page in document.pages
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
