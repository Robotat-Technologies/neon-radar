// flows_by_outbound: customer accounts with at least $min_counterparties distinct payees in one bucket of
// $bucket_hours counted from $start, with every payment in and out in [$start, $end).
// Parameters: $min_counterparties, $start, $end, $bucket_hours, $limit.
MATCH (a:Account)-[r:PAID]->(p:Account)
WHERE r.ts >= datetime($start) AND r.ts < datetime($end)
  AND coalesce(a.account_kind, 'customer') <> 'cash_ledger'
WITH a, duration.inSeconds(datetime($start), r.ts).seconds / ($bucket_hours * 3600) AS bucket, count(DISTINCT p) AS payees
WHERE payees >= $min_counterparties
WITH DISTINCT a
ORDER BY a.id
LIMIT $limit
RETURN a.id AS account,
       COLLECT { MATCH (h:Entity)-[:HOLDS_ACCOUNT]->(a) RETURN h.id ORDER BY h.id } AS holders,
       COLLECT { MATCH (x:Account)-[r:PAID]->(a) WHERE r.ts >= datetime($start) AND r.ts < datetime($end)
                 RETURN r {edge_id: r.id, counterparty: x.id, .ts, .amount, .currency, channel: coalesce(r.channel, '')}
                 ORDER BY r.ts, r.id } AS inflows,
       COLLECT { MATCH (a)-[r:PAID]->(x:Account) WHERE r.ts >= datetime($start) AND r.ts < datetime($end)
                 RETURN r {edge_id: r.id, counterparty: x.id, .ts, .amount, .currency, channel: coalesce(r.channel, '')}
                 ORDER BY r.ts, r.id } AS outflows
ORDER BY account
