// company_account_histories: customer accounts held by a company filed as dormant, or incorporated on or after
// $incorporated_since, with at least $min_payments payments in [$start, $end) (those payments only, in order of
// (ts, id)). Parameters: $incorporated_since, $start, $end, $min_payments, $limit.
MATCH (c:Company)-[:HOLDS_ACCOUNT]->(a:Account)
WHERE coalesce(a.account_kind, 'customer') <> 'cash_ledger'
  AND (toUpper(coalesce(c.accounts_category, '')) = 'DORMANT'
       OR (size(coalesce(c.incorporation_date, '')) = 10 AND c.incorporation_date >= $incorporated_since))
WITH DISTINCT a
CALL (a) {
  MATCH (a)-[r:PAID]-(x:Account)
  WHERE r.ts >= datetime($start) AND r.ts < datetime($end)
  WITH r, x, startNode(r) = a AS out
  ORDER BY r.ts, r.id
  RETURN collect({edge_id: r.id, counterparty: x.id, ts: r.ts, amount: r.amount, currency: r.currency,
                  channel: coalesce(r.channel, ''), direction: CASE WHEN out THEN 'out' ELSE 'in' END}) AS pays
}
WITH a, pays WHERE size(pays) >= $min_payments
WITH a, pays ORDER BY a.id LIMIT $limit
RETURN a.id AS account, coalesce(a.opening_date, '') AS opening_date,
       COLLECT { MATCH (h:Entity)-[:HOLDS_ACCOUNT]->(a) RETURN h.id ORDER BY h.id } AS holders, pays
ORDER BY account
