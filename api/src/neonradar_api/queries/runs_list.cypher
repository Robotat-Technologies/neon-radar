// api/runs_list: the detection runs, newest first (C3 1.2.0 GET /runs).
// Parameters: $limit.
MATCH (r:DetectionRun)
RETURN r.run_id AS run_id, r.status AS status, r.started_at AS started_at,
       r.finished_at AS finished_at, r.profile AS profile, r.window_start AS window_start,
       r.window_end AS window_end, r.typologies AS typologies, r.detectors AS detectors,
       r.alert_count AS alert_count, r.params_sha256 AS params_sha256, null AS summary
ORDER BY coalesce(r.started_at, '') DESC, run_id DESC
LIMIT $limit;
