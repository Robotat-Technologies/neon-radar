// links_into: registry relationships of the types in $types that end at each of $ids, by id, then by
// relationship id. Parameters: $ids, $types (relationship type names from the registry list in source.py).
UNWIND $ids AS entity_id
MATCH (s)-[r]->(t:Entity {id: entity_id})
WHERE type(r) IN $types
RETURN t.id AS key, type(r) AS rel_type, r.id AS rel_id, s.id AS source, t.id AS target,
       r.share_pct_min AS share_min, r.share_pct_max AS share_max,
       coalesce(r.share_min_exclusive, false) AS share_min_exclusive,
       coalesce(r.share_max_exclusive, false) AS share_max_exclusive, coalesce(r.is_nominee, false) AS is_nominee,
       coalesce(r.role, r.relationship, '') AS role, coalesce(r.start_date, '') AS start_date,
       coalesce(r.end_date, '') AS end_date, coalesce(r.control_type, '') AS control_type
ORDER BY key, rel_id
