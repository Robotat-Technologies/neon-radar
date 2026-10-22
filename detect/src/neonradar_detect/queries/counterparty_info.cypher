// counterparty_info: each account's opening date, its holders (sorted) and the labels they carry.
// Parameters: $ids. By account id.
UNWIND $ids AS account_id
MATCH (a:Entity:Account {id: account_id})
RETURN a.id AS account, coalesce(a.opening_date, '') AS opening_date,
       COLLECT { MATCH (h:Entity)-[:HOLDS_ACCOUNT]->(a) UNWIND labels(h) AS label RETURN DISTINCT label ORDER BY label } AS holder_labels,
       COLLECT { MATCH (h:Entity)-[:HOLDS_ACCOUNT]->(a) RETURN h.id ORDER BY h.id } AS holders
ORDER BY account
