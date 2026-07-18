"""
Central pipeline orchestrator for PDF-to-OKF extraction.

Chains all processing stages:
    1. Extract raw text from PDF (PyMuPDF)
    2. Canonicalize text (Unicode, whitespace, line endings)
    3. AI analyzes document structure (Gemini)
    4. Generate OKF repository with directory hierarchy
    5. Validate repository (§9 conformance + YAML round-trip)
    5b. Integrity check (paragraph coverage)
    6. Write ZIP archive with .md concept files + knowledge graph
"""

import logging
import time

from extractor.pdf_reader import read_pdf
from canonicalizer.pipeline import canonicalize
from converter.organizer import analyze_document
from converter.deduplicator import deduplicate_analysis
from generator.generator import generate_repository
from validator.validator import validate
from writer.writer import write_zip
from tester.repository_checker import check_repository

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    """Raised when a pipeline step fails."""

    def __init__(self, step: str, message: str, cause: Exception = None):
        self.step = step
        self.message = message
        self.cause = cause
        super().__init__(f"[{step}] {message}")


def _timed(step_name: str, func, *args, **kwargs):
    """Execute a function with timing and error handling."""
    logger.info(f"{step_name}...")
    start = time.time()
    try:
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        logger.info(f"  [OK] {step_name} completed in {elapsed:.2f}s")
        return result
    except PipelineError:
        raise
    except Exception as e:
        elapsed = time.time() - start
        logger.error(f"  [FAIL] {step_name} failed after {elapsed:.2f}s: {e}")
        raise PipelineError(step_name, str(e), cause=e) from e


def process_pdf(pdf_path: str) -> str:
    """
    Full extraction pipeline.

    Args:
        pdf_path: Path to the uploaded PDF file.

    Returns:
        Path to the generated output.zip file.
    """

    total_start = time.time()

    # Step 1: Extract raw text from PDF
    document = _timed("Step 1: Reading PDF", read_pdf, pdf_path)
    logger.info(f"  Loaded {document.page_count} pages")

    # Step 2: Canonicalize text
    document = _timed("Step 2: Canonicalizing text", canonicalize, document)

    # Step 3: AI analyzes document structure
    analysis = _timed(
        "Step 3: Analyzing document with Gemini AI",
        analyze_document, document
    )

    # Step 3b: Deduplicate overlapping paragraph assignments
    analysis = _timed(
        "Step 3b: Deduplicating overlapping segments",
        deduplicate_analysis, analysis
    )

    # Step 4: Generate OKF repository
    repository = _timed(
        "Step 4: Generating OKF repository",
        generate_repository, document, analysis
    )
    logger.info(f"  Generated {len(repository.files)} knowledge units")

    # Step 5: Validate repository
    _timed("Step 5: Validating repository", validate, repository)

    # Step 5b: Integrity check
    result = _timed(
        "Step 5b: Checking integrity",
        check_repository, document, repository
    )
    if result["missing"] > 0 or result["duplicates"] > 0:
        logger.warning(
            f"Integrity Check: {result['missing']} missing paragraphs, "
            f"{result['duplicates']} duplicate paragraphs. Continuing to package bundle."
        )

    # Step 6: Write ZIP archive
    zip_path = _timed("Step 6: Writing ZIP archive", write_zip, repository)
    logger.info(f"  ZIP created at {zip_path}")

    total_elapsed = time.time() - total_start
    logger.info(f"Pipeline completed in {total_elapsed:.2f}s")

    return zip_path, repository
