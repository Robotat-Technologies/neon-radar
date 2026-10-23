// L18 step 3 (M3.4, fail closed): the base references of an overlay ($refs) that resolve,
// directly or through a source record (L13), to a node that may hold no account (G1, PHASE-3.md
// 7.2.4): anything but an :Organization, a :PublicBody, a node with a topic or a dissolution
// date, or a node with a dataset of kind list or leak ($excluded, from contracts/datasets.yaml;
// a merged node carries the union of its records' datasets, L12). The loader stops before
// writing when the count is not zero
UNWIND $refs AS ref
OPTIONAL MATCH (direct:Entity {id: ref})
OPTIONAL MATCH (:SourceRecord {id: ref})-[:RESOLVED_TO]->(via:Entity)
WITH ref, coalesce(direct, via) AS node
WHERE node IS NOT NULL
  AND (NOT node:Organization OR node:PublicBody OR size(coalesce(node.topics, [])) > 0
    OR node.dissolution_date IS NOT NULL
    OR any(dataset IN coalesce(node.datasets, []) WHERE dataset IN $excluded))
RETURN count(ref) AS refused;
