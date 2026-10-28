// paid_starts: payments of at least $min_amount in [$start, $end) between customer accounts, with the
// holders of both ends (sorted), in order of (ts, id). Parameters: $min_amount, $start, $end, $limit.
MATCH (a:Account)-[r:PAID]->(b:Account)
WHERE r.ts >= datetime($start) AND r.ts < datetime($end) AND r.amount >= $min_amount
  AND coalesce(a.account_kind, 'customer') <> 'cash_ledger' AND coalesce(b.account_kind, 'customer') <> 'cash_ledger'
RETURN r.id AS edge_id, a.id AS source, b.id AS target, r.ts AS ts, r.amount AS amount, r.currency AS currency,
       COLLECT { MATCH (h:Entity)-[:HOLDS_ACCOUNT]->(a) RETURN h.id ORDER BY h.id } AS source_holders,
       COLLECT { MATCH (h:Entity)-[:HOLDS_ACCOUNT]->(b) RETURN h.id ORDER BY h.id } AS target_holders
ORDER BY ts, edge_id
LIMIT $limit
