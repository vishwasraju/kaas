"""
Shared pytest fixtures for the PDF-to-OKF test suite.

Provides reusable fixtures for Document, Page, Paragraph, DoclingChunk,
Repository, OKFFile models, mock Gemini responses, sample PDFs, and the
FastAPI test client.
"""

import json
import os
import sys
import tempfile

import pytest

# Ensure project root is on sys.path so we can import project modules
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from models.document import Document
from models.page import Page
from models.paragraph import Paragraph
from models.chunk import DoclingChunk
from models.okf_file import OKFFile
from models.repository import Repository


# ---------------------------------------------------------------------------
# Fixture paths
# ---------------------------------------------------------------------------

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture
def fixtures_dir():
    """Return the path to the fixtures directory."""
    return FIXTURES_DIR


# ---------------------------------------------------------------------------
# Model fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_paragraphs():
    """Four sample paragraphs for a single page."""
    return [
        Paragraph(index=0, text="Software testing is the process of evaluating a system."),
        Paragraph(index=1, text="It involves executing components to find defects."),
        Paragraph(index=2, text="Unit testing validates individual functions in isolation."),
        Paragraph(index=3, text="Integration testing checks module interactions."),
    ]


@pytest.fixture
def sample_chunks():
    """Two sample DoclingChunks corresponding to the sample analysis."""
    return [
        DoclingChunk(
            chunk_id=1,
            heading="Introduction to Testing",
            content="Software testing is the process of evaluating a system.\n\nIt involves executing components to find defects.",
            chunk_type="text",
            suggested_type="Introduction",
            page_start=1,
            page_end=1,
            paragraph_indices=[0, 1],
        ),
        DoclingChunk(
            chunk_id=2,
            heading="Unit Testing Basics",
            content="Unit testing validates individual functions in isolation.\n\nIntegration testing checks module interactions.",
            chunk_type="text",
            suggested_type="Section",
            page_start=1,
            page_end=1,
            paragraph_indices=[2, 3],
        ),
    ]


@pytest.fixture
def sample_page(sample_paragraphs):
    """A single Page with paragraphs, a table, and a link."""
    return Page(
        page_number=1,
        raw_text=(
            "Software testing is the process of evaluating a system.\n"
            "It involves executing components to find defects.\n"
            "Unit testing validates individual functions in isolation.\n"
            "Integration testing checks module interactions."
        ),
        normalized_text=(
            "Software testing is the process of evaluating a system.\n"
            "It involves executing components to find defects.\n"
            "Unit testing validates individual functions in isolation.\n"
            "Integration testing checks module interactions."
        ),
        paragraphs=sample_paragraphs,
        tables=[{
            "bbox": [0, 0, 100, 100],
            "markdown": "| Term | Definition |\n|------|------------|\n| Unit | Single function |"
        }],
        links=[{"uri": "https://example.com", "text": "Example"}],
        has_images=False,
    )


@pytest.fixture
def sample_document(sample_page, sample_chunks):
    """A Document with one page containing four paragraphs and two structural chunks."""
    return Document(
        filename="test_document.pdf",
        filepath="/tmp/test_document.pdf",
        page_count=1,
        metadata={"title": "Test Document"},
        pages=[sample_page],
        chunks=sample_chunks,
        raw_text=sample_page.raw_text,
        normalized_text=sample_page.normalized_text,
    )


@pytest.fixture
def sample_analysis():
    """Mock Gemini analysis result (parsed JSON)."""
    response_path = os.path.join(FIXTURES_DIR, "gemini_response.json")
    with open(response_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sample_okf_file():
    """A single valid OKFFile."""
    return OKFFile(
        path="chapters/introduction.md",
        title="Introduction to Testing",
        type="Chapter",
        description="An introduction to software testing concepts.",
        content="Software testing is the process of evaluating a system.\n\nIt involves executing components to find defects.",
        tags=["testing", "introduction"],
        timestamp="2026-07-18T00:00:00Z",
        metadata={},
        relationships=[{"type": "related", "target": "Unit Testing Basics"}],
        citations=[{"url": "https://example.com", "text": "Example"}],
    )


@pytest.fixture
def sample_okf_file_2():
    """A second valid OKFFile for multi-file tests."""
    return OKFFile(
        path="chapters/unit-testing.md",
        title="Unit Testing Basics",
        type="Chapter",
        description="Fundamentals of unit testing methodology.",
        content="Unit testing validates individual functions in isolation.\n\nIntegration testing checks module interactions.",
        tags=["testing", "unit-testing"],
        timestamp="2026-07-18T00:00:00Z",
        metadata={},
        relationships=[{"type": "prerequisite", "target": "Introduction to Testing"}],
        citations=[],
    )


@pytest.fixture
def sample_repository(sample_okf_file, sample_okf_file_2):
    """A Repository with two valid OKF files."""
    return Repository(
        title="Test Knowledge Base",
        files=[sample_okf_file, sample_okf_file_2],
    )


# ---------------------------------------------------------------------------
# PDF fixture (uses raw PDF commands for lightweight PDF creation)
# ---------------------------------------------------------------------------

def _create_simple_pdf(path, text=""):
    """Create a simple valid PDF file with optional text using raw PDF commands."""
    # Minimal valid PDF with text
    if text:
        # Encode text content into a simple PDF
        stream_content = f"BT /F1 11 Tf 72 720 Td ({text}) Tj ET"
        stream_bytes = stream_content.encode("latin-1")
        stream_length = len(stream_bytes)

        pdf_content = (
            b"%PDF-1.4\n"
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R"
            b"/Contents 4 0 R/Resources<</Font<</F1<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>>>>>>>endobj\n"
            + f"4 0 obj<</Length {stream_length}>>stream\n".encode("latin-1")
            + stream_bytes
            + b"\nendstream\nendobj\n"
            + b"xref\n0 5\n"
            + b"0000000000 65535 f \n"
            + b"0000000009 00000 n \n"
            + b"0000000058 00000 n \n"
            + b"0000000115 00000 n \n"
            + b"0000000306 00000 n \n"
            + b"trailer<</Size 5/Root 1 0 R>>\n"
            + b"startxref\n400\n%%EOF"
        )
    else:
        # Blank page PDF
        pdf_content = (
            b"%PDF-1.4\n"
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
            b"xref\n0 4\n"
            b"0000000000 65535 f \n"
            b"0000000009 00000 n \n"
            b"0000000058 00000 n \n"
            b"0000000115 00000 n \n"
            b"trailer<</Size 4/Root 1 0 R>>\n"
            b"startxref\n206\n%%EOF"
        )
    with open(path, "wb") as f:
        f.write(pdf_content)


@pytest.fixture
def sample_pdf_path(tmp_path):
    """Create a minimal valid PDF with text content and return its path."""
    pdf_path = tmp_path / "test_document.pdf"
    _create_simple_pdf(
        str(pdf_path),
        text="Software testing is the process of evaluating a system."
    )
    return str(pdf_path)


@pytest.fixture
def empty_pdf_path(tmp_path):
    """Create a PDF with no text content (blank page)."""
    pdf_path = tmp_path / "empty.pdf"
    _create_simple_pdf(str(pdf_path), text="")
    return str(pdf_path)


# ---------------------------------------------------------------------------
# Gemini mock fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_gemini_response_text(sample_analysis):
    """Raw text that the Gemini API would return (JSON string)."""
    return json.dumps(sample_analysis)


@pytest.fixture
def mock_gemini_response_with_fences(mock_gemini_response_text):
    """Gemini response wrapped in markdown code fences."""
    return f"```json\n{mock_gemini_response_text}\n```"


# ---------------------------------------------------------------------------
# FastAPI test client
# ---------------------------------------------------------------------------

@pytest.fixture
def app_client():
    """FastAPI TestClient for route testing."""
    from httpx import ASGITransport, AsyncClient
    from app import app

    # Use synchronous TestClient from httpx for simplicity
    from starlette.testclient import TestClient
    return TestClient(app)


# ---------------------------------------------------------------------------
# Temp directory fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_output_dir(tmp_path):
    """Temporary directory for file write tests."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return str(output_dir)
