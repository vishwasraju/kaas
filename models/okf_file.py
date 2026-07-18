from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class OKFFile:
    """
    Represents one OKF concept document (§4).
    """

    # Bundle-relative path, e.g. "chapters/neural-networks.md"
    path: str

    title: str

    # Descriptive type, e.g. "Textbook Chapter", "Reference" (§4.1 REQUIRED)
    type: str

    # One-line summary (§4.1 recommended)
    description: str

    # Main body content (markdown)
    content: str

    # Cross-cutting categorization tags (§4.1 recommended)
    tags: List[str] = field(default_factory=list)

    # ISO 8601 datetime of last meaningful change (§4.1 recommended)
    timestamp: Optional[str] = None

    # Producer-defined extension fields (§4.1 extensions)
    metadata: Dict = field(default_factory=dict)

    # Relationships to other concepts (for generating cross-links §5)
    relationships: List[Dict] = field(default_factory=list)

    # External sources backing claims in the body (§8)
    citations: List[Dict] = field(default_factory=list)