import re

from models.document import Document


def normalize_whitespace(document: Document) -> Document:
    """
    Normalize whitespace while preserving document content.
    """

    for page in document.pages:

        text = page.normalized_text

        # Convert tabs to spaces
        text = text.replace("\t", " ")

        # Remove trailing spaces
        text = re.sub(
            r"[ \t]+$",
            "",
            text,
            flags=re.MULTILINE,
        )

        # Collapse multiple spaces
        text = re.sub(
            r" {2,}",
            " ",
            text,
        )

        page.normalized_text = text

    return document