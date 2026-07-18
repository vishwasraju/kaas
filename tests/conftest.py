"""
Shared pytest fixtures for the PDF-to-OKF test suite.

Provides reusable fixtures for Document, Page, Paragraph, Repository,
OKFFile models, mock Gemini responses, sample PDFs, and the FastAPI
test client.
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
def sample_document(sample_page):
    """A Document with one page containing four paragraphs."""
    return Document(
        filename="test_document.pdf",
        filepath="/tmp/test_document.pdf",
        page_count=1,
        metadata={"title": "Test Document"},
        pages=[sample_page],
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
        content="Software testing is the process of evaluating a system.\nIt involves executing components to find defects.",
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
        content="Unit testing validates individual functions in isolation.\nIntegration testing checks module interactions.",
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
# PDF fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_pdf_path(tmp_path):
    """Create a minimal valid PDF using PyMuPDF and return its path."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        pytest.skip("PyMuPDF (fitz) not installed")

    pdf_path = tmp_path / "test_document.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        (
            "Software testing is the process of evaluating a system.\n"
            "It involves executing components to find defects.\n"
            "Unit testing validates individual functions in isolation.\n"
            "Integration testing checks module interactions."
        ),
        fontsize=11,
    )
    doc.save(str(pdf_path))
    doc.close()
    return str(pdf_path)


@pytest.fixture
def empty_pdf_path(tmp_path):
    """Create a PDF with no text content (blank page)."""
    try:
        import fitz
    except ImportError:
        pytest.skip("PyMuPDF (fitz) not installed")

    pdf_path = tmp_path / "empty.pdf"
    doc = fitz.open()
    doc.new_page()  # blank page, no text
    doc.save(str(pdf_path))
    doc.close()
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
