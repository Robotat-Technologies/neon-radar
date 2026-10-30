// L11: RESOLVED_TO from each source record to its canonical entity
UNWIND $rows AS row
MATCH (s:SourceRecord {id: row.record_id})
MATCH (e:Entity {id: row.canonical_id})
MERGE (s)-[r:RESOLVED_TO]->(e)
SET r += row.props;
