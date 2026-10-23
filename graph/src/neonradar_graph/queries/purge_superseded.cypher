// L9 (default instance): before a resolved load, remove the synthetic entities and source
// records whose id or referents include a record id of this load ($record_ids), so a re-run
// after a resolver change leaves no stale node (I13), and every detection result
MATCH (n)
WHERE (n:Entity OR n:SourceRecord) AND n.synthetic = true
  AND (n.id IN $record_ids OR any(r IN coalesce(n.referents, []) WHERE r IN $record_ids))
CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS;
MATCH (n) WHERE n:Alert OR n:DetectionRun
CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS;
