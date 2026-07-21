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
    Produces a spec-conformant bundle with directory hierarchy,
    proper frontmatter, and markdown cross-links.
    """

    repository = Repository(
        title=analysis.get(
            "repository_title",
            document.filename.rsplit(".", 1)[0]
        )
    )

    knowledge_units = analysis["knowledge_units"]

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Track used paths to avoid collisions
    used_paths = set()

    # First pass: create all OKFFile objects with paths
    for unit in knowledge_units:

        content_parts = []
        citations = []
        seen_urls = set()

        for segment in unit["segments"]:

            page_number = segment["page"]
            start_paragraph = segment["start_paragraph"]
            end_paragraph = segment["end_paragraph"]

            # Guard against invalid page references
            if page_number < 1 or page_number > len(document.pages):
                continue

            page = document.pages[page_number - 1]

            for paragraph in page.paragraphs:

                if start_paragraph <= paragraph.index <= end_paragraph:
                    content_parts.append(paragraph.text)

            # Collect hyperlinks from source pages for citations (§8)
            for link in page.links:
                url = link.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    text = link.get("text", "").strip() or url
                    citations.append({"text": text, "url": url})

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

        # Apply markdown formatting heuristics to paragraph content
        formatted_content = "\n\n".join(_format_paragraph(p) for p in content_parts)

        if not formatted_content.strip():
            logger.warning(
                "Skipping empty knowledge unit '%s' (no valid paragraph content found)",
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
                    "pages": f"{unit.get('start_page', 'N/A')}-{unit.get('end_page', 'N/A')}",
                },
            },
            relationships=unit.get("relationships", []),
            citations=citations,
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