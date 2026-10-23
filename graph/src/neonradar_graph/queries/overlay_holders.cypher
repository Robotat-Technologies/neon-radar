// L18 step 3 (M3.4, fail closed): the base references of an overlay ($refs) that resolve,
// directly or through a source record (L13), to a node that is not an :Organization or that
// carries a topic. Only base organisations without a topic receive an account (G1, PHASE-3.md
// 7.2), so the loader stops before writing when the count is not zero
UNWIND $refs AS ref
OPTIONAL MATCH (direct:Entity {id: ref})
OPTIONAL MATCH (:SourceRecord {id: ref})-[:RESOLVED_TO]->(via:Entity)
WITH ref, coalesce(direct, via) AS node
WHERE node IS NOT NULL AND (NOT node:Organization OR size(coalesce(node.topics, [])) > 0)
RETURN count(ref) AS refused;
