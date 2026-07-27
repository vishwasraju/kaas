import logging
import os
import re
from typing import Dict, List

from models.document import Document
from models.page import Page
from models.paragraph import Paragraph
from models.chunk import DoclingChunk

logger = logging.getLogger(__name__)


def _classify_type(heading: str, chunk_type: str) -> str:
    """
    Rule-based type classification from heading text and chunk type.
    Handles ~80% of type assignments deterministically; Gemini can override.
    """
    if chunk_type == "table":
        return "Reference"
    if chunk_type == "figure":
        return "Figure"

    heading_lower = heading.lower().strip()
    if re.match(r'^(chapter|part)\s+\d', heading_lower):
        return "Chapter"
    if re.match(r'^appendix', heading_lower):
        return "Appendix"
    if re.match(r'^glossary', heading_lower):
        return "Glossary"
    if re.match(r'^(references|bibliography)', heading_lower):
        return "Reference"
    if re.match(r'^(exercise|problem|question)', heading_lower):
        return "Exercise"
    if re.match(r'^(example|case study)', heading_lower):
        return "Example"
    if re.match(r'^(theorem|lemma|corollary)', heading_lower):
        return "Theorem"
    if re.match(r'^definition', heading_lower):
        return "Definition"
    if re.match(r'^(summary|conclusion)', heading_lower):
        return "Summary"
    if re.match(r'^(introduction|preface|foreword)', heading_lower):
        return "Introduction"

    return "Section"


def read_pdf(pdf_path: str) -> Document:
    """
    Reads a PDF using Docling and creates a Document object.

    Performs two extraction passes:
    1. Flat paragraph extraction (per-page, for integrity checking)
    2. Structural chunking (section-level, for OKF generation)

    Extracts:
    - Raw page text (Markdown)
    - Paragraphs (indexed per page)
    - Tables (preserved as complete Markdown)
    - Image presence flags
    - Structural Chunks (DoclingChunk objects)
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    try:
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.datamodel.base_models import InputFormat
    except ImportError as e:
        raise RuntimeError("Docling package is not installed. Please install 'docling'.") from e

    try:
        enable_ocr = os.getenv("ENABLE_OCR", "true").lower() == "true"
        enable_table_structure = os.getenv("ENABLE_TABLE_STRUCTURE", "true").lower() == "true"

        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = enable_ocr
        pipeline_options.do_table_structure = enable_table_structure

        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        result = converter.convert(pdf_path)
        docling_doc = result.document
    except Exception as e:
        logger.warning(f"Docling conversion encountered issue ({e}). Using ultra-lightweight pypdfium fallback...")
        return _read_pdf_pypdfium(pdf_path)

    if not hasattr(docling_doc, 'pages') or len(docling_doc.pages) == 0:
         raise ValueError(f"PDF has no pages: {os.path.basename(pdf_path)}")

    num_pages = len(docling_doc.pages)

    # Initialize per-page collections (Pass 1: flat paragraphs)
    page_texts: Dict[int, List[str]] = {i: [] for i in range(1, num_pages + 1)}
    page_paragraphs: Dict[int, List[Paragraph]] = {i: [] for i in range(1, num_pages + 1)}
    page_tables: Dict[int, List[Dict]] = {i: [] for i in range(1, num_pages + 1)}
    page_images: Dict[int, bool] = {i: False for i in range(1, num_pages + 1)}

    paragraph_counters = {i: 1 for i in range(1, num_pages + 1)}

    # Pass 2: Structural chunking state
    chunks: List[DoclingChunk] = []
    chunk_id_counter = 1

    current_heading = ""
    current_text_parts: List[str] = []
    current_page_start = None
    current_page_end = None
    current_paragraph_indices: List[int] = []

    def _close_text_chunk():
        """Close the current accumulating text chunk and save it."""
        nonlocal chunk_id_counter, current_text_parts, current_page_start, current_page_end, current_paragraph_indices
        if current_text_parts:
            content = "\n\n".join(current_text_parts)
            chunk = DoclingChunk(
                chunk_id=chunk_id_counter,
                heading=current_heading,
                content=content,
                chunk_type="text",
                suggested_type=_classify_type(current_heading, "text"),
                page_start=current_page_start or 1,
                page_end=current_page_end or 1,
                paragraph_indices=current_paragraph_indices.copy()
            )
            chunks.append(chunk)
            chunk_id_counter += 1
            current_text_parts = []
            current_page_start = None
            current_page_end = None
            current_paragraph_indices = []

    # Iterate over document elements (both passes happen in single traversal)
    for item, level in docling_doc.iterate_items():
        if hasattr(item, 'prov') and item.prov:
            for prov in item.prov:
                page_no = prov.page_no
                if page_no not in page_texts:
                    continue  # Safety check for unexpected page numbers

                item_type = type(item).__name__

                # Detect section headers to create chunk boundaries
                is_header = (
                    item_type == "SectionHeaderItem"
                    or "Header" in item_type
                    or "Title" in item_type
                )

                if is_header:
                    _close_text_chunk()
                    current_heading = item.text if hasattr(item, 'text') and item.text else ""

                if item_type == "TableItem":
                    # Close any preceding text chunk before the standalone table
                    _close_text_chunk()

                    md_table = item.export_to_markdown() if hasattr(item, 'export_to_markdown') else ""
                    # Store as markdown representation for tables
                    page_tables[page_no].append({
                        "headers": [],
                        "rows": [],
                        "md": md_table
                    })
                    if md_table:
                        p_idx = paragraph_counters[page_no]
                        page_paragraphs[page_no].append(
                            Paragraph(index=p_idx, text=md_table, section_heading=current_heading)
                        )
                        paragraph_counters[page_no] += 1
                        page_texts[page_no].append(md_table)

                        # Table = standalone chunk (never split)
                        chunks.append(DoclingChunk(
                            chunk_id=chunk_id_counter,
                            heading=current_heading,
                            content=md_table,
                            chunk_type="table",
                            suggested_type=_classify_type(current_heading, "table"),
                            page_start=page_no,
                            page_end=page_no,
                            paragraph_indices=[p_idx]
                        ))
                        chunk_id_counter += 1

                elif item_type == "PictureItem":
                    page_images[page_no] = True
                    # Figure = standalone chunk
                    chunks.append(DoclingChunk(
                        chunk_id=chunk_id_counter,
                        heading=current_heading,
                        content="[Figure]",
                        chunk_type="figure",
                        suggested_type=_classify_type(current_heading, "figure"),
                        page_start=page_no,
                        page_end=page_no,
                        paragraph_indices=[]
                    ))
                    chunk_id_counter += 1

                elif hasattr(item, 'text'):
                    # Text item (Paragraph, Section header text, etc.)
                    text_val = item.text
                    if text_val:
                        p_idx = paragraph_counters[page_no]
                        page_texts[page_no].append(text_val)
                        page_paragraphs[page_no].append(
                            Paragraph(index=p_idx, text=text_val, section_heading=current_heading)
                        )
                        paragraph_counters[page_no] += 1

                        # Accumulate into current section chunk
                        current_text_parts.append(text_val)
                        current_paragraph_indices.append(p_idx)
                        if current_page_start is None or page_no < current_page_start:
                            current_page_start = page_no
                        if current_page_end is None or page_no > current_page_end:
                            current_page_end = page_no

    # Close the last text chunk
    _close_text_chunk()

    # FALLBACK: If zero chunks were created (PDF has no section headers),
    # create 1 chunk per page to avoid returning 1 giant chunk.
    if len(chunks) == 0:
        logger.info("No section headers found in PDF. Falling back to page-based chunking.")
        for p_num in range(1, num_pages + 1):
            page_text_content = "\n\n".join(page_texts.get(p_num, []))
            if page_text_content.strip():
                indices = [p.index for p in page_paragraphs.get(p_num, [])]
                chunks.append(DoclingChunk(
                    chunk_id=chunk_id_counter,
                    heading=f"Page {p_num}",
                    content=page_text_content,
                    chunk_type="text",
                    suggested_type="Section",
                    page_start=p_num,
                    page_end=p_num,
                    paragraph_indices=indices
                ))
                chunk_id_counter += 1

    # Build the Document object
    document = Document(
        filename=os.path.basename(pdf_path),
        filepath=os.path.abspath(pdf_path),
        page_count=num_pages,
        metadata={},
    )

    document.chunks = chunks

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


def _read_pdf_pypdfium(pdf_path: str) -> Document:
    """
    Bulletproof fallback PDF reader using pypdfium2 (uses < 10MB RAM).
    Extracts text, paragraphs, and page chunks instantly.
    """
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(pdf_path)
    num_pages = len(pdf)

    page_texts: Dict[int, List[str]] = {i: [] for i in range(1, num_pages + 1)}
    page_paragraphs: Dict[int, List[Paragraph]] = {i: [] for i in range(1, num_pages + 1)}
    chunks: List[DoclingChunk] = []
    chunk_id = 1

    for page_idx in range(num_pages):
        page_num = page_idx + 1
        page = pdf[page_idx]
        text_page = page.get_textpage()
        page_text = text_page.get_text_range().strip()

        paragraphs = []
        if page_text:
            lines = [line.strip() for line in page_text.splitlines() if line.strip()]
            for p_i, line in enumerate(lines, 1):
                paragraphs.append(Paragraph(index=p_i, text=line, section_heading=f"Page {page_num}"))

            chunks.append(DoclingChunk(
                chunk_id=chunk_id,
                heading=f"Page {page_num}",
                content=page_text,
                chunk_type="text",
                suggested_type="Section",
                page_start=page_num,
                page_end=page_num,
                paragraph_indices=[p.index for p in paragraphs]
            ))
            chunk_id += 1

            page_texts[page_num] = [page_text]
        page_paragraphs[page_num] = paragraphs

    document = Document(
        filename=os.path.basename(pdf_path),
        filepath=os.path.abspath(pdf_path),
        page_count=num_pages,
        metadata={},
    )
    document.chunks = chunks

    for p_num in range(1, num_pages + 1):
        raw_text = "\n".join(page_texts.get(p_num, []))
        page = Page(
            page_number=p_num,
            raw_text=raw_text,
            paragraphs=page_paragraphs.get(p_num, []),
            tables=[],
            links=[],
            has_images=False
        )
        document.pages.append(page)

    document.raw_text = "\n\n".join("\n".join(page_texts.get(i, [])) for i in range(1, num_pages + 1))
    return document