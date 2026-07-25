import logging
import os
from typing import Dict, List

from models.document import Document
from models.page import Page
from models.paragraph import Paragraph

logger = logging.getLogger(__name__)

def read_pdf(pdf_path: str) -> Document:
    """
    Reads a PDF using Docling and creates a Document object.

    Extracts:
    - Raw page text (Markdown)
    - Paragraphs
    - Tables
    - Image presence
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    try:
        from docling.document_converter import DocumentConverter
    except ImportError as e:
        raise RuntimeError("Docling package is not installed. Please install 'docling'.") from e

    try:
        converter = DocumentConverter()
        result = converter.convert(pdf_path)
        docling_doc = result.document
    except Exception as e:
        raise ValueError(f"Failed to read PDF {os.path.basename(pdf_path)}. It may be encrypted or corrupted: {str(e)}")

    if not hasattr(docling_doc, 'pages') or len(docling_doc.pages) == 0:
         raise ValueError(f"PDF has no pages: {os.path.basename(pdf_path)}")

    num_pages = len(docling_doc.pages)

    # Initialize collections
    page_texts: Dict[int, List[str]] = {i: [] for i in range(1, num_pages + 1)}
    page_paragraphs: Dict[int, List[Paragraph]] = {i: [] for i in range(1, num_pages + 1)}
    page_tables: Dict[int, List[Dict]] = {i: [] for i in range(1, num_pages + 1)}
    page_images: Dict[int, bool] = {i: False for i in range(1, num_pages + 1)}

    paragraph_counters = {i: 1 for i in range(1, num_pages + 1)}

    # Iterate over document elements
    for item, level in docling_doc.iterate_items():
        if hasattr(item, 'prov') and item.prov:
            for prov in item.prov:
                page_no = prov.page_no
                if page_no not in page_texts:
                    continue  # Safety check for unexpected page numbers

                item_type = type(item).__name__

                if item_type == "TableItem":
                    md_table = item.export_to_markdown() if hasattr(item, 'export_to_markdown') else ""
                    # Store as markdown representation for tables
                    page_tables[page_no].append({
                        "headers": [],
                        "rows": [],
                        "md": md_table
                    })
                    if md_table:
                        page_paragraphs[page_no].append(
                            Paragraph(index=paragraph_counters[page_no], text=md_table)
                        )
                        paragraph_counters[page_no] += 1
                        page_texts[page_no].append(md_table)
                elif item_type == "PictureItem":
                    page_images[page_no] = True
                elif hasattr(item, 'text'):
                    # Text item (Paragraph, Title, Section header, etc.)
                    text_val = item.text
                    if text_val:
                        page_texts[page_no].append(text_val)
                        page_paragraphs[page_no].append(
                            Paragraph(index=paragraph_counters[page_no], text=text_val)
                        )
                        paragraph_counters[page_no] += 1

    document = Document(
        filename=os.path.basename(pdf_path),
        filepath=os.path.abspath(pdf_path),
        page_count=num_pages,
        metadata={},
    )

    for p_num in range(1, num_pages + 1):
        raw_text = "\n".join(page_texts.get(p_num, []))
        page = Page(
            page_number=p_num,
            raw_text=raw_text,
            paragraphs=page_paragraphs.get(p_num, []),
            tables=page_tables.get(p_num, []),
            links=[],  # Docling currently does not extract simple bounding-box links in this format
            has_images=page_images.get(p_num, False)
        )
        document.pages.append(page)

    # Export full document directly to markdown as the raw text
    document.raw_text = docling_doc.export_to_markdown()

    return document