"""
Test suite for the tester/repository_checker module.
Tests: TST-01 through TST-04
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tester.repository_checker import check_repository
from models.document import Document
from models.page import Page
from models.paragraph import Paragraph
from models.repository import Repository
from models.okf_file import OKFFile


def _make_doc_and_repo(doc_texts, repo_contents):
    """Helper: create a Document and Repository from text lists."""
    paragraphs = [Paragraph(index=i, text=t) for i, t in enumerate(doc_texts)]
    page = Page(
        page_number=1,
        raw_text="\n".join(doc_texts),
        normalized_text="\n".join(doc_texts),
        paragraphs=paragraphs,
    )
    doc = Document(
        filename="test.pdf", filepath="/tmp/test.pdf",
        page_count=1, pages=[page],
    )
    files = []
    for i, content in enumerate(repo_contents):
        files.append(OKFFile(
            path=f"chapters/ch{i}.md", title=f"Ch {i}",
            type="Chapter", description="", content=content,
        ))
    repo = Repository(title="Test", files=files)
    return doc, repo


class TestRepositoryChecker:
    """Tests for tester/repository_checker.py."""

    def test_tst_01_full_coverage(self):
        """TST-01: No missing/duplicate paragraphs when repository fully covers document."""
        texts = ["Alpha paragraph.", "Beta paragraph."]
        # OKF content joins paragraphs with double newline
        doc, repo = _make_doc_and_repo(texts, ["Alpha paragraph.\n\nBeta paragraph."])
        result = check_repository(doc, repo)
        assert result["missing"] == 0
        assert result["duplicates"] == 0

    def test_tst_02_missing_paragraphs(self):
        """TST-02: Detects missing paragraphs when some are not in any OKF file."""
        texts = ["Alpha paragraph.", "Beta paragraph.", "Gamma paragraph."]
        # Only include first paragraph in repo
        doc, repo = _make_doc_and_repo(texts, ["Alpha paragraph."])
        result = check_repository(doc, repo)
        assert result["missing"] == 2  # Beta and Gamma missing

    def test_tst_03_duplicate_paragraphs(self):
        """TST-03: Detects duplicate paragraphs when same content appears multiple times."""
        texts = ["Alpha paragraph."]
        # Same paragraph appears in two OKF files
        doc, repo = _make_doc_and_repo(
            texts,
            ["Alpha paragraph.", "Alpha paragraph."]
        )
        result = check_repository(doc, repo)
        assert result["duplicates"] == 1

    def test_tst_04_correct_counts(self):
        """TST-04: Returns correct counts (original, generated, missing, duplicates)."""
        texts = ["One.", "Two.", "Three."]
        doc, repo = _make_doc_and_repo(texts, ["One.\n\nTwo."])
        result = check_repository(doc, repo)
        assert result["original"] == 3
        assert result["generated"] == 2
        assert result["missing"] == 1
        assert result["duplicates"] == 0
        assert set(result.keys()) == {"original", "generated", "missing", "duplicates"}
