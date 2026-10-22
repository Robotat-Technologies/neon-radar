// payments_from: each account's outgoing payments in [$start, $end), in order of (ts, id).
// Parameters: $ids, $start, $end. Accounts without one are left out.
UNWIND $ids AS account_id
MATCH (a:Entity:Account {id: account_id})-[r:PAID]->(x:Account)
WHERE r.ts >= datetime($start) AND r.ts < datetime($end)
RETURN a.id AS account, r.id AS edge_id, x.id AS counterparty, r.ts AS ts, r.amount AS amount, r.currency AS currency,
       coalesce(r.channel, '') AS channel
ORDER BY account, ts, edge_id
