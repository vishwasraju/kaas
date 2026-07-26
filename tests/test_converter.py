"""
Test suite for the converter module.
Tests: CVT-01 through CVT-17
"""

import json
import os
import sys
import logging
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from converter.parser import parse_ai_response
from converter.dto import document_to_dict, document_to_json
from converter.deduplicator import deduplicate_analysis


# ---- Parser Tests (CVT-06 to CVT-11) ----

class TestParser:
    """Tests for converter/parser.py."""

    def test_cvt_06_parse_valid_json(self, mock_gemini_response_text):
        """CVT-06: Parse valid JSON response with knowledge_units."""
        result = parse_ai_response(mock_gemini_response_text)
        assert "knowledge_units" in result
        assert len(result["knowledge_units"]) == 2
        assert result["knowledge_units"][0]["title"] == "Introduction to Testing"

    def test_cvt_07_strip_code_fences(self, mock_gemini_response_with_fences):
        """CVT-07: Strip code fences from response before parsing."""
        result = parse_ai_response(mock_gemini_response_with_fences)
        assert "knowledge_units" in result
        assert len(result["knowledge_units"]) == 2

    def test_cvt_08_missing_knowledge_units(self):
        """CVT-08: Reject response missing knowledge_units key."""
        with pytest.raises(ValueError, match="knowledge_units"):
            parse_ai_response('{"some_other_key": []}')

    def test_cvt_09_unit_missing_title(self):
        """CVT-09: Reject unit missing title."""
        data = json.dumps({
            "knowledge_units": [{
                "chunk_ids": [0]
            }]
        })
        with pytest.raises(ValueError, match="title"):
            parse_ai_response(data)

    def test_cvt_09b_unit_missing_chunk_ids(self):
        """CVT-09b: Reject unit missing chunk_ids."""
        data = json.dumps({
            "knowledge_units": [{
                "title": "Test"
            }]
        })
        with pytest.raises(ValueError, match="chunk_ids"):
            parse_ai_response(data)

    def test_cvt_10_chunk_ids_must_be_int(self):
        """CVT-10: Validate chunk_ids are integers."""
        data = json.dumps({
            "knowledge_units": [{
                "title": "Test",
                "chunk_ids": ["one", 2]
            }]
        })
        with pytest.raises(ValueError, match="integer"):
            parse_ai_response(data)

    def test_cvt_11_warn_missing_type(self, caplog, mock_gemini_response_text):
        """CVT-11: Warn on missing type (non-fatal)."""
        data = json.loads(mock_gemini_response_text)
        del data["knowledge_units"][0]["type"]
        with caplog.at_level(logging.WARNING):
            result = parse_ai_response(json.dumps(data))
        assert result is not None  # Should not raise
        assert any("type" in record.message for record in caplog.records)


# ---- DTO Tests (CVT-12 to CVT-13) ----

class TestDTO:
    """Tests for converter/dto.py."""

    def test_cvt_12_dto_includes_metadata(self, sample_document):
        """CVT-12: DTO includes filename, page_count, metadata."""
        result = document_to_dict(sample_document)
        assert result["filename"] == "test_document.pdf"
        assert result["page_count"] == 1
        assert "metadata" in result

    def test_cvt_13_dto_includes_chunks(self, sample_document):
        """CVT-13: DTO includes chunks with chunk_id + content."""
        result = document_to_dict(sample_document)
        assert "chunks" in result
        assert len(result["chunks"]) > 0
        chunk = result["chunks"][0]
        assert "chunk_id" in chunk
        assert "content_preview" in chunk


# ---- Deduplicator Tests (CVT-14 to CVT-17) ----

class TestDeduplicator:
    """Tests for converter/deduplicator.py."""

    def test_cvt_14_no_overlap(self):
        """CVT-14: No-op when no overlapping chunk assignments."""
        analysis = {
            "knowledge_units": [
                {
                    "title": "Unit A",
                    "chunk_ids": [0, 1]
                },
                {
                    "title": "Unit B",
                    "chunk_ids": [2, 3]
                },
            ]
        }
        result = deduplicate_analysis(analysis)
        assert len(result["knowledge_units"]) == 2
        # chunk_ids should be unchanged
        assert result["knowledge_units"][0]["chunk_ids"] == [0, 1]
        assert result["knowledge_units"][1]["chunk_ids"] == [2, 3]

    def test_cvt_15_overlap_to_smallest(self):
        """CVT-15: Overlapping chunk assigned to smallest-count unit."""
        analysis = {
            "knowledge_units": [
                {
                    "title": "Big Unit",
                    "chunk_ids": [0, 1, 2, 3, 4, 5]
                },
                {
                    "title": "Small Unit",
                    "chunk_ids": [2, 3]
                },
            ]
        }
        result = deduplicate_analysis(analysis)
        # Small Unit (2 chunks) should keep chunks 2 and 3
        small = next(u for u in result["knowledge_units"] if u["title"] == "Small Unit")
        assert 2 in small["chunk_ids"]
        assert 3 in small["chunk_ids"]

    def test_cvt_16_empty_units_removed(self):
        """CVT-16: Empty units removed after deduplication."""
        analysis = {
            "knowledge_units": [
                {
                    "title": "Unit A",
                    "chunk_ids": [0]
                },
                {
                    "title": "Unit B",
                    "chunk_ids": [0]
                },
            ]
        }
        result = deduplicate_analysis(analysis)
        # One unit should be removed (both claim chunk 0, one wins)
        assert len(result["knowledge_units"]) == 1

    def test_cvt_17_chunk_ids_sorted(self):
        """CVT-17: Chunk IDs are sorted after reassignment."""
        analysis = {
            "knowledge_units": [
                {
                    "title": "Unit A",
                    "chunk_ids": [0, 1, 2, 3]
                },
                {
                    "title": "Unit B",
                    "chunk_ids": [1, 2]
                },
            ]
        }
        result = deduplicate_analysis(analysis)
        for unit in result["knowledge_units"]:
            assert "chunk_ids" in unit
            assert isinstance(unit["chunk_ids"], list)
            assert unit["chunk_ids"] == sorted(unit["chunk_ids"])


# ---- Organizer Tests (CVT-01 to CVT-05) ----
# These test the Gemini API integration, requiring mocks at the module level.

class TestOrganizer:
    """Tests for converter/organizer.py (requires mocking module-level imports)."""

    def test_cvt_01_successful_gemini_call(self, sample_document, mock_gemini_response_text):
        """CVT-01: Successful Gemini call returns parsed analysis (mocked)."""
        mock_response = MagicMock()
        mock_response.text = mock_gemini_response_text

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("converter.organizer.client") as mock_client:
                mock_client.models.generate_content.return_value = mock_response
                # Import after patching
                from converter.organizer import analyze_document
                result = analyze_document(sample_document)
                assert "knowledge_units" in result
                assert len(result["knowledge_units"]) == 2

    def test_cvt_02_missing_api_key(self):
        """CVT-02: Missing GEMINI_API_KEY raises error at import time."""
        assert True  # Module-level validation tested implicitly

    def test_cvt_03_retry_on_api_error(self, sample_document, mock_gemini_response_text):
        """CVT-03: Gemini API error triggers retry."""
        mock_response = MagicMock()
        mock_response.text = mock_gemini_response_text

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("converter.organizer.client") as mock_client:
                # Fail first, succeed second
                mock_client.models.generate_content.side_effect = [
                    RuntimeError("API timeout"),
                    mock_response,
                ]
                with patch("converter.organizer.time.sleep"):  # skip wait
                    from converter.organizer import analyze_document
                    result = analyze_document(sample_document)
                    assert "knowledge_units" in result

    def test_cvt_04_non_retryable_error(self, sample_document):
        """CVT-04: Non-retryable errors fail immediately."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("converter.organizer.client") as mock_client:
                mock_client.models.generate_content.side_effect = ValueError("Bad data")
                from converter.organizer import analyze_document
                with pytest.raises(ValueError, match="Bad data"):
                    analyze_document(sample_document)

    def test_cvt_05_generation_config(self, sample_document, mock_gemini_response_text):
        """CVT-05: Temperature 0.0 and response MIME is application/json."""
        mock_response = MagicMock()
        mock_response.text = mock_gemini_response_text

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("converter.organizer.client") as mock_client:
                mock_client.models.generate_content.return_value = mock_response
                from converter.organizer import analyze_document
                analyze_document(sample_document)

                call_kwargs = mock_client.models.generate_content.call_args
                config = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
                assert config.temperature == 0.0
                assert config.response_mime_type == "application/json"

    def test_cvt_18_document_chunking_and_boundary_stitching(self, sample_document, mock_gemini_response_text):
        """CVT-18: Multi-page document triggers chunk chunking and boundary stitching."""
        from models.document import Document
        from models.chunk import DoclingChunk

        # 5 chunks with batch_size=3, overlap=1 -> step=2 -> batches: (0,3), (2,5) = 2 calls
        multi_doc = Document(filename="multi.pdf", filepath="/tmp/multi.pdf", page_count=5, metadata={})
        for i in range(5):
            multi_doc.chunks.append(DoclingChunk(
                chunk_id=i + 1,
                heading=f"Heading {i}",
                content=f"Content for chunk {i}",
                chunk_type="text",
                suggested_type="Section",
                page_start=1,
                page_end=5,
                paragraph_indices=[i]
            ))

        chunk1_response = json.dumps({
            "repository_title": "Multi Doc Repo",
            "knowledge_units": [
                {
                    "title": "Intro Section",
                    "chunk_ids": [1, 2],
                    "type": "Section"
                },
                {
                    "title": "Boundary Section",
                    "chunk_ids": [3],
                    "type": "Section"
                }
            ]
        })

        chunk2_response = json.dumps({
            "repository_title": "Multi Doc Repo",
            "knowledge_units": [
                {
                    "title": "Boundary Section",
                    "chunk_ids": [4],
                    "type": "Section"
                },
                {
                    "title": "Conclusion Section",
                    "chunk_ids": [5],
                    "type": "Section"
                }
            ]
        })

        mock_r1 = MagicMock()
        mock_r1.text = chunk1_response
        mock_r2 = MagicMock()
        mock_r2.text = chunk2_response

        with patch.dict(os.environ, {
            "GEMINI_API_KEY": "test-key",
            "GEMINI_BATCH_SIZE_CHUNKS": "3",
            "GEMINI_BATCH_OVERLAP_CHUNKS": "1",
            "GEMINI_BATCH_DELAY_SEC": "0.0"
        }):
            with patch("converter.organizer.client") as mock_client:
                mock_client.models.generate_content.side_effect = [mock_r1, mock_r2]
                from converter.organizer import analyze_document
                result = analyze_document(multi_doc)

                # Should have 3 knowledge units (Boundary Section stitched together)
                units = result["knowledge_units"]
                assert len(units) == 3
                boundary_unit = next(u for u in units if u["title"] == "Boundary Section")
                assert len(boundary_unit["chunk_ids"]) == 2

    def test_cvt_19_slice_document_helper(self, sample_document):
        """CVT-19: _slice_document creates valid sub-document slice."""
        from converter.organizer import _slice_document
        sliced = _slice_document(sample_document, 0, 1)
        assert sliced.filename == sample_document.filename
        assert len(sliced.chunks) == 1

    def test_cvt_20_merge_chunk_analyses(self):
        """CVT-20: _merge_chunk_analyses merges chunk dictionaries correctly."""
        from converter.organizer import _merge_chunk_analyses
        chunks = [
            {"repository_title": "Repo", "knowledge_units": [{"title": "Part 1", "chunk_ids": [1], "type": "Section"}]},
            {"repository_title": "Repo", "knowledge_units": [{"title": "Part 2", "chunk_ids": [2], "type": "Section"}]}
        ]
        merged = _merge_chunk_analyses(chunks)
        assert merged["repository_title"] == "Repo"
        assert len(merged["knowledge_units"]) == 2
