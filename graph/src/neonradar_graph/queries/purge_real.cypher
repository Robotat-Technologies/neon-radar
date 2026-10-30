// L9 (real-data instance): before a resolved load, remove every entity, sanction and source
// record, and every detection result (detections are re-run after a load)
MATCH (n) WHERE n:Entity OR n:Sanction OR n:SourceRecord
CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS;
MATCH (n) WHERE n:Alert OR n:DetectionRun
CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS;
