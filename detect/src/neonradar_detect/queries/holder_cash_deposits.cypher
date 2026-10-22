// holder_cash_deposits: holders whose accounts received at least $min_in_band cash deposits of $band_low to
// $threshold (both included) in [$start, $end), with every cash deposit of the period into any of their
// accounts, in order of (ts, id). Parameters: $band_low, $threshold, $min_in_band, $start, $end, $limit.
MATCH (h:LegalEntity)-[:HOLDS_ACCOUNT]->(a:Account)<-[r:PAID]-(:Account)
WHERE r.channel = 'cash_deposit' AND r.ts >= datetime($start) AND r.ts < datetime($end)
  AND r.amount >= $band_low AND r.amount <= $threshold
WITH h, count(DISTINCT r) AS in_band
WHERE in_band >= $min_in_band
WITH h ORDER BY h.id LIMIT $limit
RETURN h.id AS holder,
       COLLECT { MATCH (h)-[:HOLDS_ACCOUNT]->(a:Account)<-[r:PAID]-(b:Account)
                 WHERE r.channel = 'cash_deposit' AND r.ts >= datetime($start) AND r.ts < datetime($end)
                 RETURN {ts: r.ts, edge_id: r.id, account: a.id, branch: b.id, amount: r.amount, currency: r.currency}
                 ORDER BY r.ts, r.id } AS deposits
ORDER BY holder
