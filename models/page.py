from dataclasses import dataclass, field
from typing import Dict, List

from models.paragraph import Paragraph


@dataclass
class Page:
    """
    Represents a single page in a document.
    """

    page_number: int
    raw_text: str

    # Text after canonicalization
    normalized_text: str = ""

    # Paragraphs extracted from the normalized text
    paragraphs: List[Paragraph] = field(default_factory=list)

    # Tables extracted from the page (list of dicts with 'headers' and 'rows')
    tables: List[Dict] = field(default_factory=list)

    # Hyperlinks found on the page (list of dicts with 'text' and 'url')
    links: List[Dict] = field(default_factory=list)

    # Whether the page contains images
    has_images: bool = False