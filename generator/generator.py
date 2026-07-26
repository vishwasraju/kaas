import re
import logging
from datetime import datetime, timezone

from models.document import Document
from models.repository import Repository
from models.okf_file import OKFFile
from generator.slug import slugify

logger = logging.getLogger(__name__)


def _format_paragraph(text: str) -> str:
    """
    Applies lightweight markdown formatting heuristics to raw text paragraphs.
    
    1. Detects bullet points (•, –, ▪, *, -) and normalizes them to markdown bullets (-).
    2. Detects definition lists (Term: Description) and bolds the term (**Term:** Description).
    """
    if not text:
        return ""
        
    # If the text is a reconstructed markdown table, skip formatting
    if text.startswith("|"):
        return text

    lines = text.split("\n")
    formatted_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            formatted_lines.append(line)
            continue

        # 1. Normalize bullet markers
        bullet_match = re.match(r"^([•–▪\-*])\s*(.*)", stripped)
        if bullet_match:
            _, rest = bullet_match.groups()
            formatted_lines.append(f"- {rest}")
            continue

        # 2. Bold definition terms (except section/chapter headers like "Chapter 1: System Overview")
        def_match = re.match(r"^([A-Z0-9][A-Za-z0-9\s/()\-]{1,59}):\s+(.{3,})$", stripped)
        if def_match:
            term, desc = def_match.groups()
            if not re.match(r"^(Chapter|Section|Part|Appendix)\s+\d+", term.strip(), re.IGNORECASE):
                formatted_lines.append(f"**{term}:** {desc}")
                continue


        formatted_lines.append(line)

    return "\n".join(formatted_lines)


def generate_repository(document: Document, analysis: dict) -> Repository:
    """
    Generate an in-memory OKF repository from the AI analysis.

    Uses chunk_ids from the AI analysis to look up DoclingChunk objects
    on the document, assembling content from pre-formed structural chunks
    rather than raw paragraph ranges.
    """

    repository = Repository(
        title=analysis.get(
            "repository_title",
            document.filename.rsplit(".", 1)[0]
        )
    )

    knowledge_units = analysis["knowledge_units"]

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Build a lookup map from chunk_id to DoclingChunk
    chunk_map = {chunk.chunk_id: chunk for chunk in document.chunks}

    # Track used paths to avoid collisions
    used_paths = set()

    for unit in knowledge_units:

        content_parts = []
        page_start = None
        page_end = None

        chunk_ids = unit.get("chunk_ids", [])

        for cid in chunk_ids:
            chunk = chunk_map.get(cid)
            if not chunk:
                logger.warning(
                    "Knowledge unit '%s' references unknown chunk_id %d, skipping",
                    unit.get("title", "?"), cid
                )
                continue

            content_parts.append(chunk.content)

            # Track page range across all chunks in this unit
            if page_start is None or chunk.page_start < page_start:
                page_start = chunk.page_start
            if page_end is None or chunk.page_end > page_end:
                page_end = chunk.page_end

        # Determine directory path from AI-provided category
        category = unit.get("category", "concepts")
        slug = slugify(unit["title"])
        category_slug = slugify(category)
        path = f"{category_slug}/{slug}.md"

        # Deduplicate paths: append suffix if collision detected
        if path in used_paths:
            counter = 2
            while f"{category_slug}/{slug}-{counter}.md" in used_paths:
                counter += 1
            path = f"{category_slug}/{slug}-{counter}.md"

        used_paths.add(path)

        # Apply markdown formatting heuristics to content
        formatted_content = "\n\n".join(_format_paragraph(p) for p in content_parts)

        if not formatted_content.strip():
            logger.warning(
                "Skipping empty knowledge unit '%s' (no valid content found)",
                unit["title"]
            )
            continue

        okf_file = OKFFile(
            path=path,
            title=unit["title"],
            type=unit.get("type", "Concept"),
            description=unit.get("description", ""),
            content=formatted_content,
            tags=unit.get("tags", []),
            timestamp=now,
            metadata={
                "source": {
                    "document": document.filename,
                    "pages": f"{page_start or 'N/A'}-{page_end or 'N/A'}",
                },
            },
            relationships=unit.get("relationships", []),
            citations=[],
        )

        repository.files.append(okf_file)

    # Second pass: resolve cross-link targets to bundle paths (§5)
    title_to_path = {f.title.lower(): f.path for f in repository.files}

    for okf in repository.files:
        for rel in okf.relationships:
            target_title = rel.get("target", "")
            target_path = title_to_path.get(target_title.lower())
            if target_path:
                rel["target_path"] = target_path

    return repository