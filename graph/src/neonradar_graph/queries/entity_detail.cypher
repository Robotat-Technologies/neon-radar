// M2.12: entity detail (C3 GET /entities/{entity_id}) with its relationship counts by type.
// The id is an :Entity, a :Sanction, or a record merged into an entity (C3 1.1.0: any id in
// `referents`), through its :SourceRecord and RESOLVED_TO. One row per entity found: more than
// one is an I7 violation, which the API refuses.
OPTIONAL MATCH (e:Entity {id: $id})
OPTIONAL MATCH (s:Sanction {id: $id})
OPTIONAL MATCH (:SourceRecord {id: $id})-[:RESOLVED_TO]->(m:Entity)
WITH DISTINCT coalesce(e, s, m) AS root
WHERE root IS NOT NULL
CALL (root) {
  MATCH (root)-[r]-()
  WHERE type(r) IN $types
  WITH type(r) AS type, count(DISTINCT r) AS count
  RETURN collect([type, count]) AS counts
}
RETURN {props: properties(root), labels: labels(root)} AS node, counts;
