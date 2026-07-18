"""
Test suite for the validator module.
Tests: VAL-01 through VAL-12
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from validator.validator import validate, ValidationError
from models.repository import Repository
from models.okf_file import OKFFile


def _make_valid_file(**overrides):
    """Create a valid OKFFile with optional overrides."""
    defaults = {
        "path": "chapters/test.md",
        "title": "Test Concept",
        "type": "Chapter",
        "description": "A test concept.",
        "content": "This is valid content for testing.",
        "tags": ["test"],
    }
    defaults.update(overrides)
    return OKFFile(**defaults)


class TestValidator:
    """Tests for validator/validator.py."""

    def test_val_01_valid_repository(self, sample_repository):
        """VAL-01: Valid repository passes validation."""
        result = validate(sample_repository)
        assert result is True

    def test_val_02_no_title(self):
        """VAL-02: Repository with no title raises ValidationError."""
        repo = Repository(title="", files=[_make_valid_file()])
        with pytest.raises(ValidationError, match="title"):
            validate(repo)

    def test_val_03_no_files(self):
        """VAL-03: Repository with no files raises ValidationError."""
        repo = Repository(title="Test Repo", files=[])
        with pytest.raises(ValidationError, match="empty"):
            validate(repo)

    def test_val_04_empty_path(self):
        """VAL-04: File with empty path raises error."""
        repo = Repository(title="Test", files=[_make_valid_file(path="")])
        with pytest.raises(ValidationError, match="no path"):
            validate(repo)

    def test_val_05_duplicate_paths(self):
        """VAL-05: Duplicate file paths raises error."""
        f1 = _make_valid_file(path="chapters/same.md")
        f2 = _make_valid_file(path="chapters/same.md")
        repo = Repository(title="Test", files=[f1, f2])
        with pytest.raises(ValidationError, match="Duplicate"):
            validate(repo)

    def test_val_06_no_md_extension(self):
        """VAL-06: File without .md extension raises error."""
        repo = Repository(title="Test", files=[_make_valid_file(path="chapters/test.txt")])
        with pytest.raises(ValidationError, match=".md"):
            validate(repo)

    def test_val_07_reserved_index_md(self):
        """VAL-07: Reserved filename index.md used as concept raises error."""
        repo = Repository(title="Test", files=[_make_valid_file(path="chapters/index.md")])
        with pytest.raises(ValidationError, match="reserved"):
            validate(repo)

    def test_val_08_reserved_log_md(self):
        """VAL-08: Reserved filename log.md used as concept raises error."""
        repo = Repository(title="Test", files=[_make_valid_file(path="log.md")])
        with pytest.raises(ValidationError, match="reserved"):
            validate(repo)

    def test_val_09_empty_type(self):
        """VAL-09: File with empty type raises error."""
        repo = Repository(title="Test", files=[_make_valid_file(type="")])
        with pytest.raises(ValidationError, match="type"):
            validate(repo)

    def test_val_10_empty_title(self):
        """VAL-10: File with empty title raises error."""
        repo = Repository(title="Test", files=[_make_valid_file(title="")])
        with pytest.raises(ValidationError, match="title"):
            validate(repo)

    def test_val_11_empty_content(self):
        """VAL-11: File with empty content raises error."""
        repo = Repository(title="Test", files=[_make_valid_file(content="   ")])
        with pytest.raises(ValidationError, match="content"):
            validate(repo)

    def test_val_12_yaml_roundtrip(self):
        """VAL-12: YAML round-trip: frontmatter survives safe_dump -> safe_load."""
        # A file with special characters in tags that could break YAML
        f = _make_valid_file(
            tags=["machine-learning", "neural: networks", "test"],
            description="A concept with special chars: colons, brackets []",
        )
        repo = Repository(title="Test", files=[f])
        # Should not raise — YAML round-trip must succeed
        result = validate(repo)
        assert result is True
