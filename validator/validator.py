"""
Validates an OKF repository for spec conformance (§9).

A bundle is conformant with OKF v0.1 if:
1. Every non-reserved .md file contains parseable YAML frontmatter.
2. Every frontmatter block contains a non-empty 'type' field.
3. Every reserved filename (index.md, log.md) follows its defined structure.
"""

import io
import os

import yaml

from models.repository import Repository


class ValidationError(Exception):
    pass


def validate(repository: Repository) -> bool:
    """
    Validate the OKF repository for spec conformance.
    """

    if not repository.title:
        raise ValidationError(
            "Repository title missing."
        )

    if not repository.files:
        raise ValidationError(
            "Repository is empty — no concept documents."
        )

    paths = set()

    for file in repository.files:

        # Check path exists
        if not file.path:
            raise ValidationError(
                "Concept document has no path."
            )

        # Check for duplicate paths
        if file.path in paths:
            raise ValidationError(
                f"Duplicate path: {file.path}"
            )
        paths.add(file.path)

        # §9 Rule: file must use .md extension
        if not file.path.endswith(".md"):
            raise ValidationError(
                f"{file.path}: must use .md extension."
            )

        # §3.1: reserved filenames must not be used for concepts
        basename = os.path.basename(file.path)
        if basename in ("index.md", "log.md"):
            raise ValidationError(
                f"{file.path}: reserved filename '{basename}' "
                f"must not be used for concept documents."
            )

        # §9 Rule 2: non-empty type field
        if not file.type or not file.type.strip():
            raise ValidationError(
                f"{file.path}: missing required 'type' field."
            )

        if not file.title:
            raise ValidationError(
                f"{file.path}: missing title."
            )

        if not file.content.strip():
            raise ValidationError(
                f"{file.path}: empty content."
            )

        # §9 Rule 1: verify the frontmatter we'll produce is parseable YAML
        frontmatter = {"type": file.type}
        if file.title:
            frontmatter["title"] = file.title
        if file.description:
            frontmatter["description"] = file.description
        if file.tags:
            frontmatter["tags"] = file.tags
        if file.timestamp:
            frontmatter["timestamp"] = file.timestamp
        for key, value in file.metadata.items():
            frontmatter[key] = value

        try:
            rendered = yaml.safe_dump(
                frontmatter,
                allow_unicode=True,
                sort_keys=False,
            )
            # Round-trip: verify it parses back
            yaml.safe_load(io.StringIO(rendered))
        except yaml.YAMLError as e:
            raise ValidationError(
                f"{file.path}: frontmatter would produce invalid YAML: {e}"
            )

    return True
