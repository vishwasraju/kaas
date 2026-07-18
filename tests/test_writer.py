"""
Test suite for the writer module.
Tests: WRT-01 through WRT-13
"""

import os
import sys
import zipfile
import tempfile
import shutil

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from writer.writer import (
    build_index_file,
    build_subdir_index,
    build_concept_file,
    build_log_file,
    write_zip,
    cleanup_temp_dir,
)
from writer.graph_builder import build_graph_html
from models.repository import Repository
from models.okf_file import OKFFile


class TestBuildIndexFile:
    """Tests for build_index_file()."""

    def test_wrt_01_no_frontmatter(self, sample_repository):
        """WRT-01: build_index_file() produces markdown with no frontmatter (§6)."""
        content = build_index_file(sample_repository)
        assert not content.startswith("---"), "index.md must not have frontmatter"
        assert content.startswith("#")

    def test_wrt_02_groups_by_directory(self, sample_repository):
        """WRT-02: build_index_file() groups files by directory with links."""
        content = build_index_file(sample_repository)
        # Both files are in chapters/ directory
        assert "Chapters" in content
        assert "[Introduction to Testing]" in content
        assert "[Unit Testing Basics]" in content


class TestBuildSubdirIndex:
    """Tests for build_subdir_index()."""

    def test_wrt_03_subdir_index(self, sample_okf_file, sample_okf_file_2):
        """WRT-03: build_subdir_index() creates subdirectory indexes."""
        content = build_subdir_index("Chapters", [sample_okf_file, sample_okf_file_2])
        assert "# Chapters" in content
        assert not content.startswith("---")
        assert "[Introduction to Testing]" in content


class TestBuildConceptFile:
    """Tests for build_concept_file()."""

    def test_wrt_04_yaml_frontmatter(self, sample_okf_file):
        """WRT-04: build_concept_file() includes YAML frontmatter with type, title."""
        content = build_concept_file(sample_okf_file)
        assert content.startswith("---\n")
        assert "type: Chapter" in content
        assert "title: Introduction to Testing" in content

    def test_wrt_05_related_and_citations(self, sample_okf_file):
        """WRT-05: build_concept_file() includes Related Concepts and Citations sections."""
        content = build_concept_file(sample_okf_file)
        assert "## Related Concepts" in content
        assert "Unit Testing Basics" in content
        assert "# Citations" in content
        assert "example.com" in content


class TestBuildLogFile:
    """Tests for build_log_file()."""

    def test_wrt_06_log_format(self, sample_repository):
        """WRT-06: build_log_file() starts with '# Directory Update Log' and ISO date (§7)."""
        content = build_log_file(sample_repository)
        assert content.startswith("# Directory Update Log")
        # Should contain an ISO date heading (YYYY-MM-DD)
        import re
        assert re.search(r"## \d{4}-\d{2}-\d{2}", content)


class TestWriteZip:
    """Tests for write_zip()."""

    def test_wrt_07_valid_zip(self, sample_repository, tmp_path):
        """WRT-07: write_zip() creates valid ZIP with all expected files."""
        zip_path = write_zip(sample_repository, str(tmp_path))
        assert os.path.exists(zip_path)
        assert zipfile.is_zipfile(zip_path)

    def test_wrt_08_zip_contains_required_files(self, sample_repository, tmp_path):
        """WRT-08: ZIP contains index.md, log.md, visualize_graph.html."""
        zip_path = write_zip(sample_repository, str(tmp_path))
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            assert "index.md" in names
            assert "log.md" in names
            assert "visualize_graph.html" in names

    def test_wrt_09_concept_files_have_frontmatter(self, sample_repository, tmp_path):
        """WRT-09: ZIP concept files start with --- (YAML frontmatter)."""
        zip_path = write_zip(sample_repository, str(tmp_path))
        with zipfile.ZipFile(zip_path, "r") as zf:
            for name in zf.namelist():
                if name.endswith(".md") and os.path.basename(name) not in ("index.md", "log.md"):
                    content = zf.read(name).decode("utf-8")
                    assert content.startswith("---"), f"{name} missing YAML frontmatter"


class TestCleanupTempDir:
    """Tests for cleanup_temp_dir()."""

    def test_wrt_10_cleanup(self):
        """WRT-10: cleanup_temp_dir() removes temporary directory."""
        temp_dir = tempfile.mkdtemp(prefix="pdf_to_okf_")
        dummy_file = os.path.join(temp_dir, "output.zip")
        with open(dummy_file, "w") as f:
            f.write("dummy")
        cleanup_temp_dir(dummy_file)
        assert not os.path.exists(temp_dir)


class TestGraphBuilder:
    """Tests for writer/graph_builder.py."""

    def test_wrt_11_vis_network_reference(self, sample_repository):
        """WRT-11: Graph HTML contains vis-network reference."""
        html = build_graph_html(sample_repository)
        assert "vis-network" in html

    def test_wrt_12_concept_nodes(self, sample_repository):
        """WRT-12: Graph HTML includes all concept nodes."""
        html = build_graph_html(sample_repository)
        assert "Introduction to Testing" in html
        assert "Unit Testing Basics" in html

    def test_wrt_13_relationship_edges(self, sample_repository):
        """WRT-13: Graph HTML includes relationship edges."""
        html = build_graph_html(sample_repository)
        # The graph should reference relationships
        assert "related" in html.lower() or "prerequisite" in html.lower() or "edges" in html.lower()
