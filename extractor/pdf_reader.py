import fitz  # PyMuPDF
import logging
import os
from models.document import Document
from models.page import Page
from models.paragraph import Paragraph

logger = logging.getLogger(__name__)


def _is_inside_bbox(point, bbox) -> bool:
    """Helper to check if a 2D point (x, y) is inside a bounding box (x0, y0, x1, y1)."""
    x, y = point
    bx0, by0, bx1, by1 = bbox
    return bx0 <= x <= bx1 and by0 <= y <= by1


def _table_to_markdown(table_data) -> str:
    """
    Converts raw table cell data extracted from PyMuPDF into a clean Markdown table.
    Ensures empty rows are skipped, None values are replaced, and newlines are sanitized.
    """
    if not table_data or len(table_data) < 2:
        return ""

    # Clean cell values
    cleaned_rows = []
    max_cols = 0
    for row in table_data:
        if not row:
            continue
        cleaned_row = []
        for cell in row:
            val = str(cell) if cell is not None else ""
            # Sanitize cell value (newlines to spaces, strip, escape pipe)
            val = val.replace("\n", " ").strip()
            val = val.replace("|", "\\|")
            cleaned_row.append(val)
        cleaned_rows.append(cleaned_row)
        max_cols = max(max_cols, len(cleaned_row))

    if not cleaned_rows:
        return ""

    # Standardize row lengths to max_cols
    for row in cleaned_rows:
        while len(row) < max_cols:
            row.append("")

    header = cleaned_rows[0]
    data_rows = cleaned_rows[1:]

    # Generate Markdown table
    lines = []
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join([":---"] * max_cols) + " |")
    for row in data_rows:
        # Skip completely empty rows
        if not any(row):
            continue
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def read_pdf(pdf_path: str) -> Document:
    """
    Reads a PDF and creates a Document object.

    Extracts:
    - Document metadata
    - Raw page text
    - Paragraphs (using PyMuPDF text blocks, with table reconstruction)
    - Tables (using PyMuPDF table detection)
    - Hyperlinks (with text extracted from bounding rectangles)
    - Image presence
    """

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    # Use context manager for safe resource cleanup
    with fitz.open(pdf_path) as pdf:

        # Check for encrypted/password-protected PDFs
        if pdf.is_encrypted:
            raise ValueError(
                f"PDF is password-protected and cannot be read: "
                f"{os.path.basename(pdf_path)}"
            )

        if len(pdf) == 0:
            raise ValueError(
                f"PDF has no pages: {os.path.basename(pdf_path)}"
            )

        metadata = pdf.metadata or {}

        document = Document(
            filename=os.path.basename(pdf_path),
            filepath=os.path.abspath(pdf_path),
            page_count=len(pdf),
            metadata=metadata,
        )

        full_text = []

        for page_number, pdf_page in enumerate(pdf, start=1):

            # -------------------------
            # Full page text
            # -------------------------
            raw_text = pdf_page.get_text("text")

            page = Page(
                page_number=page_number,
                raw_text=raw_text,
            )

            # -------------------------
            # Table Detection
            # -------------------------
            tables_on_page = []
            try:
                # Try default line-based detection first
                tabs = pdf_page.find_tables()
                if tabs and hasattr(tabs, "tables") and tabs.tables:
                    tables_on_page = tabs.tables
                else:
                    # Fallback to text-alignment based strategy for borderless tables
                    tabs_text = pdf_page.find_tables(strategy="text")
                    if tabs_text and hasattr(tabs_text, "tables") and tabs_text.tables:
                        tables_on_page = tabs_text.tables
            except Exception as e:
                logger.debug("Table detection failed on page %d: %s", page_number, e)

            # Reconstruct table representations
            table_records = []
            for tab in tables_on_page:
                try:
                    table_data = tab.extract()
                    if table_data and len(table_data) >= 2:
                        md_table = _table_to_markdown(table_data)
                        if md_table:
                            table_records.append({
                                "bbox": tab.bbox,
                                "md": md_table,
                                "raw": table_data
                            })
                except Exception as e:
                    logger.debug("Reconstructing table failed: %s", e)

            # -------------------------
            # Extract paragraphs / Reconstruct tables
            # -------------------------
            blocks = pdf_page.get_text("blocks")
            paragraph_index = 1
            written_table_indices = set()

            for block in blocks:
                # block[6] == 0 means text block (not image)
                if block[6] != 0:
                    continue

                # Check if block falls inside any table bbox
                bx0, by0, bx1, by1 = block[0], block[1], block[2], block[3]
                block_center = ((bx0 + bx1) / 2, (by0 + by1) / 2)

                inside_table_idx = None
                for t_idx, tr in enumerate(table_records):
                    if _is_inside_bbox(block_center, tr["bbox"]):
                        inside_table_idx = t_idx
                        break

                if inside_table_idx is not None:
                    # Replace cell blocks with the single reconstructed markdown table block
                    if inside_table_idx not in written_table_indices:
                        written_table_indices.add(inside_table_idx)
                        page.paragraphs.append(
                            Paragraph(
                                index=paragraph_index,
                                text=table_records[inside_table_idx]["md"]
                            )
                        )
                        paragraph_index += 1
                    # Skip the fragmented text block itself
                    continue

                text = block[4].strip()
                if not text:
                    continue

                page.paragraphs.append(
                    Paragraph(
                        index=paragraph_index,
                        text=text
                    )
                )
                paragraph_index += 1

            # Store table metadata
            for tr in table_records:
                extracted = tr["raw"]
                headers = extracted[0] if extracted else []
                rows = extracted[1:] if len(extracted) > 1 else []
                page.tables.append({
                    "headers": headers,
                    "rows": rows
                })

            # -------------------------
            # Extract hyperlinks
            # -------------------------
            links = pdf_page.get_links()
            for link in links:
                if link.get("uri"):
                    # Extract the visible text under the link's bounding rect
                    link_text = ""
                    try:
                        link_rect = fitz.Rect(link["from"])
                        link_text = pdf_page.get_text(
                            "text", clip=link_rect
                        ).strip()
                    except Exception:
                        pass

                    page.links.append({
                        "url": link["uri"],
                        "text": link_text or link["uri"],
                    })

            # -------------------------
            # Check for images
            # -------------------------
            images = pdf_page.get_images(full=False)
            page.has_images = len(images) > 0

            document.pages.append(page)
            full_text.append(raw_text)

        document.raw_text = "\n".join(full_text)

    return document