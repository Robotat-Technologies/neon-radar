// paid_time_range: the first and last PAID time in the graph (null, null when there is none).
MATCH ()-[r:PAID]->()
RETURN min(r.ts) AS first, max(r.ts) AS last
