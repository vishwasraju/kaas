"""
Test suite for the pipeline module.
Tests: PIP-01 through PIP-07
"""

import os
import sys
import logging
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.repository import Repository
from models.okf_file import OKFFile


# We need to mock all pipeline dependencies since they have side effects
PIPELINE_PATCHES = {
    "pipeline.read_pdf": "read_pdf",
    "pipeline.canonicalize": "canonicalize",
    "pipeline.analyze_document": "analyze_document",
    "pipeline.deduplicate_analysis": "deduplicate_analysis",
    "pipeline.generate_repository": "generate_repository",
    "pipeline.validate": "validate",
    "pipeline.check_repository": "check_repository",
    "pipeline.write_zip": "write_zip",
}


def _make_mock_repo():
    """Create a minimal Repository for pipeline tests."""
    return Repository(
        title="Test Repo",
        files=[OKFFile(
            path="chapters/test.md", title="Test", type="Chapter",
            description="Test", content="Test content.",
        )],
    )


class TestPipeline:
    """Tests for pipeline.py."""

    @patch("pipeline.write_zip", return_value="/tmp/output.zip")
    @patch("pipeline.check_repository", return_value={"missing": 0, "duplicates": 0, "original": 4, "generated": 4})
    @patch("pipeline.validate", return_value=True)
    @patch("pipeline.generate_repository")
    @patch("pipeline.deduplicate_analysis", side_effect=lambda x: x)
    @patch("pipeline.analyze_document", return_value={"knowledge_units": []})
    @patch("pipeline.canonicalize", side_effect=lambda x: x)
    @patch("pipeline.read_pdf")
    def test_pip_01_full_pipeline_success(
        self, mock_read, mock_canon, mock_analyze, mock_dedup,
        mock_generate, mock_validate, mock_check, mock_write,
        sample_document,
    ):
        """PIP-01: Full pipeline process_pdf() succeeds end-to-end."""
        mock_read.return_value = sample_document
        mock_repo = _make_mock_repo()
        mock_generate.return_value = mock_repo

        from pipeline import process_pdf
        result = process_pdf("/tmp/test.pdf")

        assert isinstance(result, tuple)
        assert len(result) == 2
        zip_path, repository = result
        assert zip_path == "/tmp/output.zip"
        assert repository.title == "Test Repo"

    @patch("pipeline.read_pdf", side_effect=FileNotFoundError("PDF not found"))
    def test_pip_02_extraction_failure(self, mock_read):
        """PIP-02: PipelineError raised with correct step on extraction failure."""
        from pipeline import process_pdf, PipelineError
        with pytest.raises(PipelineError) as exc_info:
            process_pdf("/nonexistent.pdf")
        assert "Step 1" in str(exc_info.value) or "Reading PDF" in str(exc_info.value)

    @patch("pipeline.canonicalize", side_effect=lambda x: x)
    @patch("pipeline.read_pdf")
    @patch("pipeline.analyze_document", side_effect=RuntimeError("Gemini API error"))
    def test_pip_03_gemini_failure(self, mock_analyze, mock_read, mock_canon, sample_document):
        """PIP-03: PipelineError raised on Gemini API failure."""
        mock_read.return_value = sample_document

        from pipeline import process_pdf, PipelineError
        with pytest.raises(PipelineError) as exc_info:
            process_pdf("/tmp/test.pdf")
        assert "Gemini" in str(exc_info.value) or "Step 3" in str(exc_info.value)

    @patch("pipeline.write_zip", return_value="/tmp/output.zip")
    @patch("pipeline.check_repository", return_value={"missing": 0, "duplicates": 0, "original": 4, "generated": 4})
    @patch("pipeline.validate", side_effect=Exception("Validation failed"))
    @patch("pipeline.generate_repository")
    @patch("pipeline.deduplicate_analysis", side_effect=lambda x: x)
    @patch("pipeline.analyze_document", return_value={"knowledge_units": []})
    @patch("pipeline.canonicalize", side_effect=lambda x: x)
    @patch("pipeline.read_pdf")
    def test_pip_04_validation_failure(
        self, mock_read, mock_canon, mock_analyze, mock_dedup,
        mock_generate, mock_validate, mock_check, mock_write,
        sample_document,
    ):
        """PIP-04: PipelineError raised on validation failure."""
        mock_read.return_value = sample_document
        mock_generate.return_value = _make_mock_repo()

        from pipeline import process_pdf, PipelineError
        with pytest.raises(PipelineError) as exc_info:
            process_pdf("/tmp/test.pdf")
        assert "Step 5" in str(exc_info.value) or "Validat" in str(exc_info.value)

    def test_pip_05_timed_logs(self, caplog):
        """PIP-05: _timed() logs correct timing information."""
        from pipeline import _timed
        with caplog.at_level(logging.INFO):
            result = _timed("Test Step", lambda: 42)
        assert result == 42
        assert any("Test Step" in r.message for r in caplog.records)
        assert any("completed" in r.message.lower() for r in caplog.records)

    @patch("pipeline.write_zip", return_value="/tmp/output.zip")
    @patch("pipeline.check_repository", return_value={"missing": 3, "duplicates": 1, "original": 10, "generated": 8})
    @patch("pipeline.validate", return_value=True)
    @patch("pipeline.generate_repository")
    @patch("pipeline.deduplicate_analysis", side_effect=lambda x: x)
    @patch("pipeline.analyze_document", return_value={"knowledge_units": []})
    @patch("pipeline.canonicalize", side_effect=lambda x: x)
    @patch("pipeline.read_pdf")
    def test_pip_06_integrity_warnings_continue(
        self, mock_read, mock_canon, mock_analyze, mock_dedup,
        mock_generate, mock_validate, mock_check, mock_write,
        sample_document, caplog,
    ):
        """PIP-06: Integrity warnings logged but don't stop pipeline."""
        mock_read.return_value = sample_document
        mock_generate.return_value = _make_mock_repo()

        from pipeline import process_pdf
        with caplog.at_level(logging.WARNING):
            result = process_pdf("/tmp/test.pdf")

        # Pipeline should complete despite integrity issues
        assert result is not None
        zip_path, repo = result
        assert zip_path == "/tmp/output.zip"
        # Warning should be logged
        assert any("missing" in r.message.lower() or "Integrity" in r.message for r in caplog.records)

    @patch("pipeline.write_zip", return_value="/tmp/output.zip")
    @patch("pipeline.check_repository", return_value={"missing": 0, "duplicates": 0, "original": 4, "generated": 4})
    @patch("pipeline.validate", return_value=True)
    @patch("pipeline.generate_repository")
    @patch("pipeline.deduplicate_analysis", side_effect=lambda x: x)
    @patch("pipeline.analyze_document", return_value={"knowledge_units": []})
    @patch("pipeline.canonicalize", side_effect=lambda x: x)
    @patch("pipeline.read_pdf")
    def test_pip_07_return_types(
        self, mock_read, mock_canon, mock_analyze, mock_dedup,
        mock_generate, mock_validate, mock_check, mock_write,
        sample_document,
    ):
        """PIP-07: Pipeline returns (zip_path, repository) tuple."""
        mock_read.return_value = sample_document
        mock_repo = _make_mock_repo()
        mock_generate.return_value = mock_repo

        from pipeline import process_pdf
        result = process_pdf("/tmp/test.pdf")

        assert isinstance(result, tuple)
        zip_path, repository = result
        assert isinstance(zip_path, str)
        assert isinstance(repository, Repository)
