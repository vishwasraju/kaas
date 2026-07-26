from dataclasses import dataclass, field
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from models.paragraph import Paragraph


@dataclass
class DoclingChunk:
    """
    Represents a structural chunk extracted from a PDF by Docling.

    Each chunk corresponds to a logical document section (text block under
    a heading), a standalone table, or a figure. Chunks are the primary
    unit of organization passed to the AI for metadata enrichment.
    """

    # Sequential chunk identifier (1-indexed)
    chunk_id: int

    # Section heading text from Docling (empty for tables/figures without headings)
    heading: str

    # Full text content of the chunk (markdown for tables)
    content: str

    # Type of structural element: "text", "table", "figure"
    chunk_type: str = "text"

    # Rule-based pre-classification: "Chapter", "Section", "Reference", etc.
    suggested_type: str = "Section"

    # Page range this chunk spans
    page_start: int = 1
    page_end: int = 1

    # Original paragraph objects for integrity checking
    paragraph_indices: List[int] = field(default_factory=list)
