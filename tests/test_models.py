"""
Test suite for data models.
Tests: MDL-01 through MDL-05
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.document import Document
from models.page import Page
from models.paragraph import Paragraph
from models.okf_file import OKFFile
from models.repository import Repository


class TestDocument:
    """MDL-01: Document dataclass initializes with required fields."""

    def test_mdl_01_document_init(self):
        """Document initializes with filename, filepath, page_count and defaults."""
        doc = Document(filename="test.pdf", filepath="/tmp/test.pdf", page_count=5)
        assert doc.filename == "test.pdf"
        assert doc.filepath == "/tmp/test.pdf"
        assert doc.page_count == 5
        assert doc.pages == []
        assert doc.raw_text == ""
        assert doc.normalized_text == ""
        assert doc.metadata == {}


class TestPage:
    """MDL-02: Page dataclass defaults."""

    def test_mdl_02_page_defaults(self):
        """Page has correct defaults: empty lists and has_images=False."""
        page = Page(page_number=1, raw_text="Hello world")
        assert page.page_number == 1
        assert page.raw_text == "Hello world"
        assert page.normalized_text == ""
        assert page.paragraphs == []
        assert page.tables == []
        assert page.links == []
        assert page.has_images is False


class TestParagraph:
    """MDL-03: Paragraph stores index and text."""

    def test_mdl_03_paragraph_fields(self):
        """Paragraph stores index and text correctly."""
        p = Paragraph(index=0, text="Test paragraph content")
        assert p.index == 0
        assert p.text == "Test paragraph content"


class TestOKFFile:
    """MDL-04: OKFFile stores all fields."""

    def test_mdl_04_okf_file_fields(self):
        """OKFFile stores path, title, type, content and optional fields."""
        f = OKFFile(
            path="chapters/intro.md",
            title="Introduction",
            type="Chapter",
            description="An intro chapter",
            content="Some content here.",
        )
        assert f.path == "chapters/intro.md"
        assert f.title == "Introduction"
        assert f.type == "Chapter"
        assert f.description == "An intro chapter"
        assert f.content == "Some content here."
        # Defaults
        assert f.tags == []
        assert f.timestamp is None
        assert f.metadata == {}
        assert f.relationships == []
        assert f.citations == []


class TestRepository:
    """MDL-05: Repository stores title and files."""

    def test_mdl_05_repository_fields(self):
        """Repository stores title and list of OKFFile."""
        f1 = OKFFile(path="a.md", title="A", type="T", description="D", content="C")
        repo = Repository(title="My Repo", files=[f1])
        assert repo.title == "My Repo"
        assert len(repo.files) == 1
        assert repo.files[0].title == "A"

    def test_mdl_05_repository_defaults(self):
        """Repository defaults to empty files list."""
        repo = Repository(title="Empty")
        assert repo.files == []
