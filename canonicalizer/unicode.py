import unicodedata

from models.document import Document


def normalize_unicode(document: Document) -> Document:
    """
    Convert Unicode characters into a canonical representation.
    """

    for page in document.pages:
        page.normalized_text = unicodedata.normalize(
            "NFKC",
            page.raw_text
        )

    return document