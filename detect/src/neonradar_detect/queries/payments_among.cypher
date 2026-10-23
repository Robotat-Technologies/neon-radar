// payments_among: (edge id, payer, payee) for every PAID between two of $ids in [$start, $end), by edge id.
UNWIND $ids AS account_id
MATCH (a:Entity:Account {id: account_id})-[r:PAID]->(b:Account)
WHERE b.id IN $ids AND r.ts >= datetime($start) AND r.ts < datetime($end)
RETURN r.id AS edge_id, a.id AS payer, b.id AS payee
ORDER BY edge_id
