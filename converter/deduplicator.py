import logging

logger = logging.getLogger(__name__)

def deduplicate_analysis(analysis: dict) -> dict:
    """
    Deduplicates overlapping chunk_ids across knowledge units in place.
    
    If a chunk_id is claimed by multiple knowledge units, it is assigned exclusively
    to the unit with the smallest total chunk count.
    
    Then, it rebuilds each unit's chunk_ids list.
    """
    if "knowledge_units" not in analysis or not analysis["knowledge_units"]:
        return analysis

    units = analysis["knowledge_units"]
    
    # 1. Map each chunk_id to the list of unit indices claiming it
    claims = {}
    unit_sizes = {}
    
    for i, unit in enumerate(units):
        chunk_ids = unit.get("chunk_ids", [])
        unit_sizes[i] = len(chunk_ids)
        for cid in chunk_ids:
            claims.setdefault(cid, []).append(i)

    # 2. Assign each chunk_id exclusively to the claiming unit with the smallest overall size
    kept_chunks = {i: [] for i in range(len(units))}
    duplicates_resolved = 0
    
    for cid, unit_indices in claims.items():
        if len(unit_indices) == 1:
            kept_chunks[unit_indices[0]].append(cid)
        else:
            # Multi-claim chunk_id: deduplicate!
            winner = min(unit_indices, key=lambda idx: unit_sizes[idx])
            kept_chunks[winner].append(cid)
            duplicates_resolved += len(unit_indices) - 1

    # 3. Rebuild the chunk_ids list for each unit
    for i, unit in enumerate(units):
        # Sort chunk_ids for consistency
        unit["chunk_ids"] = sorted(kept_chunks[i])

    # 4. Filter out any units that no longer have any chunk_ids
    non_empty_units = []
    for unit in units:
        if unit.get("chunk_ids"):
            non_empty_units.append(unit)
        else:
            logger.info("Removing empty knowledge unit: '%s' (no chunks remaining after deduplication)", unit["title"])
            
    analysis["knowledge_units"] = non_empty_units

    if duplicates_resolved > 0:
        logger.info("Deduplicated overlapping assignments: resolved %d duplicate chunk_id references", duplicates_resolved)
    else:
        logger.info("No overlapping chunk assignments found.")

    return analysis
