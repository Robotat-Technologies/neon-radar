// L13: rows with an endpoint that is neither loaded in this run nor in the resolution map,
// for example Phase 3 overlay records that reference a record id of a merged entity.
// Reconciliation E4 (orchestrator decision under OD-10): as Phase 1's loader did, each end
// must carry its C2 label ($labels.source and $labels.target, from the C2 mapping table), a
// relationship with the row's id between other nodes is deleted first (its end moved), and
// every row comes back with what happened to it: an end missing (dangling), both ends on one
// node (a self-loop, not written), and which ends were found through a :SourceRecord.
// lint-values: rel_type=OWNS,CONTROLS,CONSOLIDATES,DIRECTOR_OF,HOLDS_ACCOUNT,PAID,HAS_ADDRESS,REPRESENTS,FAMILY_OF,ASSOCIATE_OF,MEMBER_OF,EMPLOYED_BY,LINKED_TO,SUCCEEDED_BY,HOLDS_POSITION
UNWIND $rows AS row
CALL (row) {
  OPTIONAL MATCH (direct:Entity {id: row.source}) WHERE $labels.source IN labels(direct)
  OPTIONAL MATCH (:SourceRecord {id: row.source})-[:RESOLVED_TO]->(via:Entity)
    WHERE $labels.source IN labels(via)
  RETURN coalesce(direct, via) AS s, direct IS NULL AND via IS NOT NULL AS s_via
  LIMIT 1
}
CALL (row) {
  OPTIONAL MATCH (direct:Entity {id: row.target}) WHERE $labels.target IN labels(direct)
  OPTIONAL MATCH (:SourceRecord {id: row.target})-[:RESOLVED_TO]->(via:Entity)
    WHERE $labels.target IN labels(via)
  RETURN coalesce(direct, via) AS t, direct IS NULL AND via IS NOT NULL AS t_via
  LIMIT 1
}
OPTIONAL MATCH (a)-[old:{{rel_type}} {id: row.id}]->(b)
  WHERE s IS NULL OR t IS NULL OR s = t OR a <> s OR b <> t
DELETE old
FOREACH (_ IN CASE WHEN s IS NOT NULL AND t IS NOT NULL AND s <> t THEN [1] ELSE [] END |
  MERGE (s)-[r:{{rel_type}} {id: row.id}]->(t)
  SET r += row.props)
RETURN row.id AS id, s IS NULL AS source_missing, t IS NULL AS target_missing,
       s IS NOT NULL AND s = t AS self_loop, s_via, t_via;
