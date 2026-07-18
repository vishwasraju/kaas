import logging

logger = logging.getLogger(__name__)

def deduplicate_analysis(analysis: dict) -> dict:
    """
    Deduplicates overlapping paragraph segments across knowledge units in place.
    
    If a paragraph is claimed by multiple knowledge units, it is assigned exclusively
    to the unit with the smallest total paragraph count (i.e. the most specific/granular unit).
    
    Then, it rebuilds each unit's segments list, grouping contiguous paragraphs on the same
    page together, and updates start_page/end_page references.
    """
    if "knowledge_units" not in analysis or not analysis["knowledge_units"]:
        return analysis

    units = analysis["knowledge_units"]
    
    # 1. Map each (page, paragraph_index) to the list of units claiming it
    claims = {}
    unit_sizes = {}
    
    for i, unit in enumerate(units):
        size = 0
        for segment in unit.get("segments", []):
            page = segment["page"]
            start = segment["start_paragraph"]
            end = segment["end_paragraph"]
            for p_idx in range(start, end + 1):
                claims.setdefault((page, p_idx), []).append(i)
                size += 1
        unit_sizes[i] = size

    # 2. Assign each paragraph exclusively to the claiming unit with the smallest overall size
    kept_paragraphs = {i: set() for i in range(len(units))}
    duplicates_resolved = 0
    
    for (page, p_idx), unit_indices in claims.items():
        if len(unit_indices) == 1:
            kept_paragraphs[unit_indices[0]].add((page, p_idx))
        else:
            # Multi-claim paragraph: deduplicate!
            winner = min(unit_indices, key=lambda idx: unit_sizes[idx])
            kept_paragraphs[winner].add((page, p_idx))
            duplicates_resolved += len(unit_indices) - 1

    # 3. Rebuild the segments list for each unit
    for i, unit in enumerate(units):
        orig_segments = unit.get("segments", [])
        
        # Group kept paragraphs by page
        page_groups = {}
        for page, p_idx in kept_paragraphs[i]:
            page_groups.setdefault(page, []).append(p_idx)
            
        new_segments = []
        for page in sorted(page_groups.keys()):
            p_indices = sorted(page_groups[page])
            if not p_indices:
                continue
            
            start = p_indices[0]
            prev = p_indices[0]
            for idx in p_indices[1:]:
                if idx == prev + 1:
                    prev = idx
                else:
                    new_segments.append({
                        "page": page,
                        "start_paragraph": start,
                        "end_paragraph": prev
                    })
                    start = idx
                    prev = idx
            new_segments.append({
                "page": page,
                "start_paragraph": start,
                "end_paragraph": prev
            })
            
        unit["segments"] = new_segments
        
        # Update start_page and end_page
        if new_segments:
            unit["start_page"] = min(s["page"] for s in new_segments)
            unit["end_page"] = max(s["page"] for s in new_segments)
        # Note: if new_segments is empty, we leave original start_page/end_page as is

    # 4. Filter out any units that no longer have any segments
    non_empty_units = []
    for unit in units:
        if unit.get("segments"):
            non_empty_units.append(unit)
        else:
            logger.info("Removing empty knowledge unit: '%s' (no segments remaining after deduplication)", unit["title"])
            
    analysis["knowledge_units"] = non_empty_units

    if duplicates_resolved > 0:
        logger.info("Deduplicated overlapping assignments: resolved %d duplicate paragraph references", duplicates_resolved)
    else:
        logger.info("No overlapping paragraph assignments found.")

    return analysis
