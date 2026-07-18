"""
Test suite for FastAPI routes.
Tests: RTE-01 through RTE-09
"""

import io
import os
import sys
import base64
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.repository import Repository
from models.okf_file import OKFFile


@pytest.fixture
def client():
    """Create a FastAPI TestClient."""
    from starlette.testclient import TestClient
    from app import app
    return TestClient(app)


def _make_mock_repo():
    """Create a mock repository for route tests."""
    return Repository(
        title="Test Knowledge Base",
        files=[OKFFile(
            path="chapters/test.md", title="Test Chapter", type="Chapter",
            description="A test chapter.", content="Test content here.",
            tags=["test"], relationships=[], citations=[],
        )],
    )


def _create_pdf_bytes():
    """Create minimal valid PDF bytes for upload testing."""
    try:
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Test content for extraction.", fontsize=11)
        buf = doc.tobytes()
        doc.close()
        return buf
    except ImportError:
        # Fallback: minimal PDF structure
        return b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n206\n%%EOF"


class TestHomeRoute:
    """Tests for GET /."""

    def test_rte_01_home_returns_200(self, client):
        """RTE-01: GET / returns 200 with HTML content."""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


class TestUploadRoute:
    """Tests for POST /upload."""

    @patch("routes.upload.process_pdf")
    def test_rte_02_valid_upload(self, mock_pipeline, client, tmp_path):
        """RTE-02: POST /upload with valid PDF returns JSON with success:true."""
        # Setup mock
        mock_repo = _make_mock_repo()
        zip_path = str(tmp_path / "output.zip")
        import zipfile
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("index.md", "# Test")
        mock_pipeline.return_value = (zip_path, mock_repo)

        pdf_bytes = _create_pdf_bytes()
        response = client.post(
            "/upload",
            files={"pdf": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_rte_03_non_pdf_rejected(self, client):
        """RTE-03: POST /upload with non-PDF file returns error."""
        response = client.post(
            "/upload",
            files={"pdf": ("test.txt", io.BytesIO(b"not a pdf"), "text/plain")},
        )
        assert response.status_code == 400

    def test_rte_04_no_file(self, client):
        """RTE-04: POST /upload with no file returns error."""
        response = client.post("/upload")
        assert response.status_code == 422  # FastAPI validation error

    @patch("routes.upload.process_pdf")
    def test_rte_06_file_cleanup(self, mock_pipeline, client, tmp_path):
        """RTE-06: Uploaded file cleaned up after processing."""
        mock_repo = _make_mock_repo()
        zip_path = str(tmp_path / "output.zip")
        import zipfile
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("index.md", "# Test")
        mock_pipeline.return_value = (zip_path, mock_repo)

        pdf_bytes = _create_pdf_bytes()
        response = client.post(
            "/upload",
            files={"pdf": ("cleanup_test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
        # The uploaded file should be cleaned up in the finally block
        upload_dir = os.path.join(os.getcwd(), "uploads")
        if os.path.exists(upload_dir):
            remaining = [f for f in os.listdir(upload_dir) if "cleanup_test" in f]
            assert len(remaining) == 0, "Uploaded file should be cleaned up"

    @patch("routes.upload.process_pdf")
    def test_rte_07_response_structure(self, mock_pipeline, client, tmp_path):
        """RTE-07: Response JSON includes repository_title and files[] metadata."""
        mock_repo = _make_mock_repo()
        zip_path = str(tmp_path / "output.zip")
        import zipfile
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("index.md", "# Test")
        mock_pipeline.return_value = (zip_path, mock_repo)

        pdf_bytes = _create_pdf_bytes()
        response = client.post(
            "/upload",
            files={"pdf": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
        data = response.json()
        assert "repository_title" in data
        assert data["repository_title"] == "Test Knowledge Base"
        assert "files" in data
        assert len(data["files"]) == 1
        assert data["files"][0]["title"] == "Test Chapter"


class TestHealthRoute:
    """Tests for GET /health."""

    def test_rte_08_health_check(self, client):
        """RTE-08: GET /health returns {"status": "healthy"}."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestStaticFiles:
    """Tests for static file serving."""

    def test_rte_09_static_css(self, client):
        """RTE-09: Static CSS served at /static/style.css."""
        response = client.get("/static/style.css")
        assert response.status_code == 200
