// merge_alerts: the :Alert nodes of one run with their C2 properties (the two 1.2.0 evidence lists
// included), PRODUCED from the run and one FLAGS per alert and subject (C4); FLAGS to entities that
// are no longer subjects are removed. Parameters: $run_id, $rows (props and subjects per alert).
MATCH (r:DetectionRun {run_id: $run_id})
UNWIND $rows AS row
MERGE (a:Alert {alert_id: row.props.alert_id})
SET a += row.props
MERGE (r)-[:PRODUCED]->(a)
WITH a, row
CALL (a, row) {
  MATCH (a)-[old:FLAGS]->(e:Entity)
  WHERE NOT e.id IN [s IN row.subjects | s.entity_id]
  DELETE old
}
CALL (a, row) {
  UNWIND row.subjects AS s
  MATCH (e:Entity {id: s.entity_id})
  // one FLAGS per alert and subject (C4): drop duplicates made outside the runner
  OPTIONAL MATCH (a)-[old:FLAGS]->(e)
  WITH a, s, e, collect(old) AS existing
  FOREACH (extra IN existing[1..] | DELETE extra)
  MERGE (a)-[f:FLAGS]->(e)
  SET f.role = s.role
  RETURN count(f) AS flagged
}
RETURN count(a) AS alerts, sum(flagged) AS flagged
