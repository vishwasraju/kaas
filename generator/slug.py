import re
import unicodedata


def slugify(text: str) -> str:
    """
    Convert a title into a filesystem-safe slug.

    Accented characters are decomposed and stripped of combining marks
    so that 'Café Résumé' becomes 'cafe-resume' (not 'cafe-re-sume').
    """

    # Decompose unicode (é → e + combining accent)
    text = unicodedata.normalize("NFKD", text)

    # Strip combining marks (accents, diacritics)
    text = "".join(
        ch for ch in text
        if unicodedata.category(ch) != "Mn"
    )

    # Lowercase
    text = text.lower()

    # Replace non-alphanumeric characters with hyphens
    text = re.sub(r"[^a-z0-9]+", "-", text)

    # Remove duplicate hyphens
    text = re.sub(r"-+", "-", text)

    # Trim hyphens
    return text.strip("-")