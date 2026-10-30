// activity_counts: number of PAID relationships into or out of each account in [$start, $end).
// Parameters: $ids, $start, $end. One row per account, by id (0 when there is none).
UNWIND $ids AS account_id
MATCH (a:Entity:Account {id: account_id})
RETURN a.id AS account,
       COUNT { MATCH (a)-[r:PAID]-() WHERE r.ts >= datetime($start) AND r.ts < datetime($end) } AS payments
ORDER BY account
