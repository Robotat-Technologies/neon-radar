// merge_run: the :DetectionRun of one run with its C2 properties (1.0.0 and the five of 1.2.0;
// a null value leaves the property absent). Parameters: $run, a map of the properties.
MERGE (r:DetectionRun {run_id: $run.run_id})
SET r += $run
