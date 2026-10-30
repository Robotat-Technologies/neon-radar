// L12: relationship rows whose endpoints the loader already re-pointed to loaded node ids.
// Labels and the type come from the C2 mapping table, never from data. For PAID, row.props.ts
// is a timezone-aware datetime from Python, so Neo4j stores a DATETIME (I3).
// Reconciliation E4 (orchestrator decision under OD-10): as Phase 1's loader did, a
// relationship with the row's id between other nodes is deleted first (its end moved), and a
// row whose end has no node comes back, so the loader reports it as dangling. Each end is a
// record of this load whose C2 label the mapping checked, or (SUBJECT_OF) a node of its C2 label.
// lint-values: rel_type=OWNS,CONTROLS,CONSOLIDATES,DIRECTOR_OF,HOLDS_ACCOUNT,PAID,HAS_ADDRESS,REPRESENTS,FAMILY_OF,ASSOCIATE_OF,MEMBER_OF,EMPLOYED_BY,LINKED_TO,SUCCEEDED_BY,HOLDS_POSITION,SUBJECT_OF target_label=Entity,Sanction
UNWIND $rows AS row
OPTIONAL MATCH (s:Entity {id: row.source})
OPTIONAL MATCH (t:{{target_label}} {id: row.target})
OPTIONAL MATCH (a)-[old:{{rel_type}} {id: row.id}]->(b)
  WHERE s IS NULL OR t IS NULL OR a <> s OR b <> t
DELETE old
FOREACH (_ IN CASE WHEN s IS NOT NULL AND t IS NOT NULL THEN [1] ELSE [] END |
  MERGE (s)-[r:{{rel_type}} {id: row.id}]->(t)
  SET r += row.props)
WITH row, s, t WHERE s IS NULL OR t IS NULL
RETURN row.id AS id, s IS NULL AS source_missing, t IS NULL AS target_missing;
