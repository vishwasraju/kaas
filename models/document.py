from dataclasses import dataclass, field
from typing import Dict, List

from models.page import Page


@dataclass
class Document:
    """
    Represents the uploaded PDF throughout the pipeline.
    """

    filename: str
    filepath: str
    page_count: int

    metadata: Dict = field(default_factory=dict)

    pages: List[Page] = field(default_factory=list)

    raw_text: str = ""

    normalized_text: str = ""