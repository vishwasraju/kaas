import re
import unicodedata
import logging

from models.document import Document

from canonicalizer.unicode import normalize_unicode
from canonicalizer.whitespace import normalize_whitespace
from canonicalizer.line_ending import normalize_line_endings
from canonicalizer.validator import validate

logger = logging.getLogger(__name__)

try:
    import ftfy
except ImportError:
    ftfy = None
    logger.warning("ftfy is not installed. Skipping ftfy text fixing.")



def _canonicalize_text(text: str) -> str:
    """
    Apply all canonicalization transforms to a single text string.
    Used for both page-level and paragraph-level normalization.
    """
    if not text:
        return text

    if ftfy:
        text = ftfy.fix_text(text)

    # Unicode normalization (NFKC)
    text = unicodedata.normalize("NFKC", text)

    # Strip control characters
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    # Whitespace normalization
    text = text.replace("\t", " ")
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
    text = re.sub(r" {2,}", " ", text)

    # Line ending normalization
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    return text


def canonicalize(document: Document) -> Document:
    """
    Runs the complete canonicalization pipeline.
    Normalizes both page-level text and individual paragraph texts
    to ensure consistent data throughout the pipeline.
    """

    # Normalize full page text
    document = normalize_unicode(document)

    document = normalize_whitespace(document)

    document = normalize_line_endings(document)

    validate(document)

    # Canonicalize paragraph texts so the generator gets clean content
    for page in document.pages:
        for paragraph in page.paragraphs:
            paragraph.text = _canonicalize_text(paragraph.text)

    if hasattr(document, 'chunks') and document.chunks:
        for chunk in document.chunks:
            chunk.content = _canonicalize_text(chunk.content)
            if chunk.heading:
                chunk.heading = _canonicalize_text(chunk.heading)

    document.normalized_text = "\n".join(
        page.normalized_text
        for page in document.pages
    )

    return document