import logging
from collections import Counter
from typing import Dict, List

from models.document import Document
from models.repository import Repository

logger = logging.getLogger(__name__)


def check_repository(document: Document, repository: Repository) -> Dict:
    """
    Verify that the generated repository preserves the original PDF.
    """

    logger.info("=" * 60)
    logger.info("PDF → OKF Integrity Report")
    logger.info("=" * 60)

    # Original PDF paragraphs
    original_paragraphs: List[str] = []
    for page in document.pages:
        for paragraph in page.paragraphs:
            text = paragraph.text.strip()
            if text:
                original_paragraphs.append(text)

    # Generated OKF paragraphs
    generated_paragraphs: List[str] = []
    for okf in repository.files:
        parts = [
            p.strip()
            for p in okf.content.split("\n\n")
            if p.strip()
        ]
        generated_paragraphs.extend(parts)

    # Counts
    logger.info(f"Original paragraphs : {len(original_paragraphs)}")
    logger.info(f"Generated paragraphs: {len(generated_paragraphs)}")

    # Frequency counters
    original_counter = Counter(original_paragraphs)
    generated_counter = Counter(generated_paragraphs)

    # Missing paragraphs: present in original more times than in generated
    missing = []
    for text, count in original_counter.items():
        gen_count = generated_counter.get(text, 0)
        if gen_count < count:
            missing.extend([text] * (count - gen_count))

    # Duplicate paragraphs: present in generated more times than in original
    duplicates = []
    for text, count in generated_counter.items():
        orig_count = original_counter.get(text, 0)
        if count > orig_count:
            duplicates.extend([text] * (count - orig_count))

    # Character counts
    original_chars = sum(len(p) for p in original_paragraphs)
    generated_chars = sum(len(p) for p in generated_paragraphs)

    logger.info(f"Original characters : {original_chars}")
    logger.info(f"Generated characters: {generated_chars}")
    logger.info(f"Missing paragraphs : {len(missing)}")
    logger.info(f"Duplicate paragraphs: {len(duplicates)}")

    if missing:
        logger.warning("=" * 60)
        logger.warning("Missing Paragraphs")
        logger.warning("=" * 60)
        for p in missing[:10]:
            logger.warning(p[:250])

    if duplicates:
        logger.warning("=" * 60)
        logger.warning("Duplicate Paragraphs")
        logger.warning("=" * 60)
        for p in duplicates[:10]:
            logger.warning(p[:250])

    if len(missing) == 0 and len(duplicates) == 0:
        logger.info("✅ Repository Integrity PASSED")
    else:
        logger.warning("❌ Repository Integrity FAILED")

    logger.info("=" * 60)

    return {
        "original": len(original_paragraphs),
        "generated": len(generated_paragraphs),
        "missing": len(missing),
        "duplicates": len(duplicates),
    }