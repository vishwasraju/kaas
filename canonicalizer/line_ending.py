from models.document import Document


def normalize_line_endings(document: Document) -> Document:
    """
    Normalize all line endings to Unix style.
    """

    for page in document.pages:

        text = page.normalized_text

        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")

        page.normalized_text = text

    return document