// L18: the base references of an overlay ($refs: every id an overlay record names that is not an
// overlay id) that resolve to no node, directly or through a source record (L13); the loader
// stops before writing when the count is not zero
UNWIND $refs AS ref
OPTIONAL MATCH (direct:Entity {id: ref})
OPTIONAL MATCH (:SourceRecord {id: ref})-[:RESOLVED_TO]->(via:Entity)
WITH ref, coalesce(direct, via) AS node
WHERE node IS NULL
RETURN count(ref) AS unresolved;
