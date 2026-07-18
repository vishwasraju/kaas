"""
Test suite for the canonicalizer module.
Tests: CAN-01 through CAN-11
"""

import os
import sys
import copy

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.document import Document
from models.page import Page
from models.paragraph import Paragraph
from canonicalizer.pipeline import canonicalize, _canonicalize_text
from canonicalizer.unicode import normalize_unicode
from canonicalizer.whitespace import normalize_whitespace
from canonicalizer.line_ending import normalize_line_endings
from canonicalizer.validator import validate


def _make_document(raw_text, paragraphs=None):
    """Helper to create a Document with one page."""
    if paragraphs is None:
        paragraphs = [Paragraph(index=0, text=raw_text)]
    page = Page(
        page_number=1,
        raw_text=raw_text,
        paragraphs=paragraphs,
    )
    return Document(
        filename="test.pdf",
        filepath="/tmp/test.pdf",
        page_count=1,
        pages=[page],
        raw_text=raw_text,
    )


class TestCanonicalizationPipeline:
    """Tests for the full canonicalization pipeline."""

    def test_can_01_full_pipeline_runs(self, sample_document):
        """CAN-01: Full canonicalization pipeline runs without error."""
        result = canonicalize(sample_document)
        assert result is not None

    def test_can_02_normalized_text_populated(self, sample_document):
        """CAN-02: normalized_text populated on each page after pipeline."""
        result = canonicalize(sample_document)
        for page in result.pages:
            assert page.normalized_text is not None
            assert len(page.normalized_text) > 0

    def test_can_03_document_normalized_text_joined(self, sample_document):
        """CAN-03: document.normalized_text is the join of page normalized_texts."""
        result = canonicalize(sample_document)
        expected = "\n".join(page.normalized_text for page in result.pages)
        assert result.normalized_text == expected


class TestUnicodeNormalization:
    """Tests for unicode normalization."""

    def test_can_04_nfkc_normalization(self):
        """CAN-04: NFKC normalization applied (e.g., \ufb01 -> fi)."""
        doc = _make_document("The \ufb01rst line of text")
        result = normalize_unicode(doc)
        assert "\ufb01" not in result.pages[0].normalized_text
        assert "fi" in result.pages[0].normalized_text


class TestWhitespaceNormalization:
    """Tests for whitespace normalization."""

    def test_can_05_tabs_to_spaces(self):
        """CAN-05: Tabs converted to spaces."""
        doc = _make_document("Hello\tworld")
        # First apply unicode normalization (pipeline order)
        doc = normalize_unicode(doc)
        result = normalize_whitespace(doc)
        assert "\t" not in result.pages[0].normalized_text
        assert "Hello" in result.pages[0].normalized_text

    def test_can_06_trailing_spaces_removed(self):
        """CAN-06: Trailing spaces removed."""
        doc = _make_document("Hello world   \nSecond line  ")
        doc = normalize_unicode(doc)
        result = normalize_whitespace(doc)
        for line in result.pages[0].normalized_text.split("\n"):
            assert not line.endswith(" "), f"Line has trailing spaces: '{line}'"

    def test_can_07_multiple_spaces_collapsed(self):
        """CAN-07: Multiple consecutive spaces collapsed to single."""
        doc = _make_document("Hello    world     test")
        doc = normalize_unicode(doc)
        result = normalize_whitespace(doc)
        assert "  " not in result.pages[0].normalized_text


class TestLineEndingNormalization:
    """Tests for line ending normalization."""

    def test_can_08_crlf_to_lf(self):
        """CAN-08: \\r\\n normalized to \\n."""
        doc = _make_document("Hello\r\nworld\r\n")
        doc = normalize_unicode(doc)
        doc = normalize_whitespace(doc)
        result = normalize_line_endings(doc)
        assert "\r\n" not in result.pages[0].normalized_text
        assert "\n" in result.pages[0].normalized_text

    def test_can_09_cr_to_lf(self):
        """CAN-09: \\r normalized to \\n."""
        doc = _make_document("Hello\rworld\r")
        doc = normalize_unicode(doc)
        doc = normalize_whitespace(doc)
        result = normalize_line_endings(doc)
        assert "\r" not in result.pages[0].normalized_text


class TestCanonicalizerValidator:
    """Tests for post-canonicalization validation."""

    def test_can_10_raises_on_empty_normalized_text(self):
        """CAN-10: Raises ValueError if page has paragraphs but empty normalized_text."""
        page = Page(
            page_number=1,
            raw_text="Some text",
            normalized_text="",  # empty!
            paragraphs=[Paragraph(index=0, text="Some text")],
        )
        doc = Document(
            filename="test.pdf",
            filepath="/tmp/test.pdf",
            page_count=1,
            pages=[page],
        )
        with pytest.raises(ValueError, match="normalized_text is empty"):
            validate(doc)

    def test_can_11_passes_valid_page(self):
        """CAN-11: Passes when page has paragraphs and non-empty normalized_text."""
        page = Page(
            page_number=1,
            raw_text="Some text",
            normalized_text="Some text",
            paragraphs=[Paragraph(index=0, text="Some text")],
        )
        doc = Document(
            filename="test.pdf",
            filepath="/tmp/test.pdf",
            page_count=1,
            pages=[page],
        )
        # Should not raise
        validate(doc)
