// flows_by_inbound: customer accounts with at least $min_counterparties distinct payers in one bucket of
// $bucket_hours counted from $start (payments of $channel only, when it is not null), with every payment
// in and out in [$start, $end). Parameters: $min_counterparties, $start, $end, $channel, $bucket_hours, $limit.
MATCH (p:Account)-[r:PAID]->(a:Account)
WHERE r.ts >= datetime($start) AND r.ts < datetime($end) AND ($channel IS NULL OR r.channel = $channel)
  AND coalesce(a.account_kind, 'customer') <> 'cash_ledger'
WITH a, duration.inSeconds(datetime($start), r.ts).seconds / ($bucket_hours * 3600) AS bucket, count(DISTINCT p) AS payers
WHERE payers >= $min_counterparties
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
