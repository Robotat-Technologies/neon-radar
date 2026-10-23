// quiet_account_histories: customer accounts with a quiet period that ends with a payment in
// [$start, $end): at least $min_gap_days from a payment, or from the opening date when that is on or after
// $history_start, to that payment, with at most $max_quiet_payments payments between them totalling at most
// $max_quiet_amount. Each with every payment of the account before $end, in order of (ts, id).
// Parameters: $min_gap_days, $max_quiet_payments, $max_quiet_amount, $history_start, $start, $end, $limit.
MATCH (a:Account)
WHERE coalesce(a.account_kind, 'customer') <> 'cash_ledger'
CALL (a) {
  MATCH (a)-[r:PAID]-(x:Account)
  WHERE r.ts < datetime($end)
  WITH r, x, startNode(r) = a AS out
  ORDER BY r.ts, r.id
  RETURN collect({edge_id: r.id, counterparty: x.id, ts: r.ts, amount: r.amount, currency: r.currency,
                  channel: coalesce(r.channel, ''), direction: CASE WHEN out THEN 'out' ELSE 'in' END}) AS pays
}
WITH a, pays, size(pays) AS n
WHERE n > 0
WITH a, pays, n,
     CASE WHEN size(coalesce(a.opening_date, '')) = 10 AND a.opening_date >= $history_start
          THEN datetime(a.opening_date + 'T00:00:00Z') ELSE null END AS opened
WITH a, pays, [j IN range(0, n - 1) WHERE pays[j].ts >= datetime($start) AND pays[j].ts < datetime($end) AND (
       any(m IN range(0, $max_quiet_payments) WHERE j - m - 1 >= 0
           AND duration.inSeconds(pays[j - m - 1].ts, pays[j].ts).seconds >= $min_gap_days * 86400
           AND reduce(s = 0.0, i IN range(j - m, j - 1) | s + pays[i].amount) <= $max_quiet_amount)
       OR (opened IS NOT NULL AND j <= $max_quiet_payments
           AND reduce(s = 0.0, i IN range(0, j - 1) | s + pays[i].amount) <= $max_quiet_amount
           AND duration.inSeconds(opened, pays[j].ts).seconds >= $min_gap_days * 86400))] AS ends
WHERE size(ends) > 0
WITH a, pays ORDER BY a.id LIMIT $limit
RETURN a.id AS account, coalesce(a.opening_date, '') AS opening_date,
       COLLECT { MATCH (h:Entity)-[:HOLDS_ACCOUNT]->(a) RETURN h.id ORDER BY h.id } AS holders, pays
ORDER BY account
