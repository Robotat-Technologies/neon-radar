// recent_account_edges: the PAID relationships in [$start, $end) whose two customer accounts were each
// opened at most $new_days before the payment (the projection of the ring variant; MemSource reference:
// recent_account_components). Parameters: $new_days, $start, $end.
MATCH (a:Account)-[r:PAID]->(b:Account)
WHERE r.ts >= datetime($start) AND r.ts < datetime($end)
  AND size(coalesce(a.opening_date, '')) = 10 AND size(coalesce(b.opening_date, '')) = 10
  AND coalesce(a.account_kind, 'customer') <> 'cash_ledger' AND coalesce(b.account_kind, 'customer') <> 'cash_ledger'
  AND date(a.opening_date) <= date(r.ts) AND date(r.ts) <= date(a.opening_date) + duration({days: $new_days})
  AND date(b.opening_date) <= date(r.ts) AND date(r.ts) <= date(b.opening_date) + duration({days: $new_days})
RETURN r.ts AS ts, r.id AS edge_id, a.id AS source, b.id AS target, r.amount AS amount, r.currency AS currency,
       coalesce(r.channel, '') AS channel
ORDER BY ts, edge_id
