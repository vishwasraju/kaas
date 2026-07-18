import re
import unicodedata

from models.document import Document

from canonicalizer.unicode import normalize_unicode
from canonicalizer.whitespace import normalize_whitespace
from canonicalizer.line_ending import normalize_line_endings
from canonicalizer.validator import validate


def _canonicalize_text(text: str) -> str:
    """
    Apply all canonicalization transforms to a single text string.
    Used for both page-level and paragraph-level normalization.
    """

    # Unicode normalization (NFKC)
    text = unicodedata.normalize("NFKC", text)

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

    document.normalized_text = "\n".join(
        page.normalized_text
        for page in document.pages
    )

    return document