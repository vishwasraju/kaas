from models.document import Document


def validate(document: Document) -> None:
    """
    Validation after canonicalization.
    Ensures every page was properly normalized.
    """

    for page in document.pages:

        if page.normalized_text is None or page.normalized_text == "":
            # Allow truly empty pages (e.g. blank separator pages)
            # but warn if a page with paragraphs has no normalized text
            if page.paragraphs:
                raise ValueError(
                    f"Page {page.page_number} has {len(page.paragraphs)} "
                    f"paragraphs but normalized_text is empty."
                )