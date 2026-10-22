// prune_run: a run id used again (`--run-id` with `--keep-previous`): drop what the earlier attempt
// produced and this one did not find, and alerts that no run produces any more (PHASE-1.md M1.9b).
// Parameters: $run_id, $alert_ids.
MATCH (:DetectionRun {run_id: $run_id})-[p:PRODUCED]->(a:Alert)
WHERE NOT a.alert_id IN $alert_ids
DELETE p
WITH DISTINCT a
WHERE NOT EXISTS { (:DetectionRun)-[:PRODUCED]->(a) }
DETACH DELETE a
