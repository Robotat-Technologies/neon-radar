// Ring variant, step 1: project the recent-account payments (recent_account_edges) as an undirected graph.
// $graph_name is unique per call ("nr-ring-" and 32 random hex digits); the source drops it in a finally block.
MATCH (a:Account)-[r:PAID]->(b:Account)
WHERE r.ts >= datetime($start) AND r.ts < datetime($end)
  AND size(coalesce(a.opening_date, '')) = 10 AND size(coalesce(b.opening_date, '')) = 10
  AND coalesce(a.account_kind, 'customer') <> 'cash_ledger' AND coalesce(b.account_kind, 'customer') <> 'cash_ledger'
  AND date(a.opening_date) <= date(r.ts) AND date(r.ts) <= date(a.opening_date) + duration({days: $new_days})
  AND date(b.opening_date) <= date(r.ts) AND date(r.ts) <= date(b.opening_date) + duration({days: $new_days})
WITH a, b, count(r) AS payments
WITH gds.graph.project($graph_name, a, b, {relationshipProperties: {payments: payments}},
                       {undirectedRelationshipTypes: ['*'], readConcurrency: 4}) AS g
RETURN g.graphName AS graph_name, g.nodeCount AS node_count, g.relationshipCount AS relationship_count
