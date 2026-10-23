// run_alert_ids: the ids of the alerts one detection run produced, sorted (`neonradar detect
// verify-alert --run`). Parameters: $run_id.
MATCH (:DetectionRun {run_id: $run_id})-[:PRODUCED]->(a:Alert)
RETURN a.alert_id AS alert_id
ORDER BY alert_id
