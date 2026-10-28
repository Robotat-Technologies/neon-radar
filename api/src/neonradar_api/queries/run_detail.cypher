// api/run_detail: one detection run with its counts-only summary (C3 1.2.0 GET /runs/{run_id}).
// Parameters: $run_id.
MATCH (r:DetectionRun {run_id: $run_id})
RETURN r.run_id AS run_id, r.status AS status, r.started_at AS started_at,
       r.finished_at AS finished_at, r.profile AS profile, r.window_start AS window_start,
       r.window_end AS window_end, r.typologies AS typologies, r.detectors AS detectors,
       r.alert_count AS alert_count, r.params_sha256 AS params_sha256, r.summary AS summary;
