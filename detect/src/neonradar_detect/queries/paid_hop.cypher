// paid_hop: the next hop of every partial path (PHASE-3.md 7.1.3). Parameters: $frontier, a list of maps
// {key, account, after, until, min_amount, max_amount, currency, visited}; after and until are ISO strings.
// A hop leaves the frontier account after `after` and at or before `until`, in the currency, with an
// amount in [min_amount, max_amount], to a customer account not visited yet. By key, then (ts, id).
UNWIND $frontier AS f
MATCH (a:Entity:Account {id: f.account})-[r:PAID]->(b:Account)
WHERE r.ts > datetime(f.after) AND r.ts <= datetime(f.until)
  AND r.amount >= f.min_amount AND r.amount <= f.max_amount AND r.currency = f.currency
  AND NOT b.id IN f.visited AND coalesce(b.account_kind, 'customer') <> 'cash_ledger'
RETURN f.key AS key, r.id AS edge_id, a.id AS source, b.id AS target, r.ts AS ts, r.amount AS amount,
       r.currency AS currency,
       COLLECT { MATCH (h:Entity)-[:HOLDS_ACCOUNT]->(b) RETURN h.id ORDER BY h.id } AS target_holders
ORDER BY key, ts, edge_id
