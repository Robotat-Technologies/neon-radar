// circular_flow: cycles of PAID that return to the account they started from (PHASE-1.md M1.9b).
// Fixed template: the detector writes the hop bounds into the quantifier placeholders as validated
// integers from the typology catalog (Cypher takes no parameters in a quantifier); every other
// value is a parameter. $origin is null for a full run and an account id to reproduce one alert.
// lint-values: min_hops=2 max_hops=2,6,8
MATCH p = (a:Account)-[t:PAID]->{{{min_hops}},{{max_hops}}}(a)
WHERE ($origin IS NULL OR a.id = $origin)
  // hops strictly in time order, so each cycle is found once, from the account where it starts
  AND all(i IN range(0, size(t) - 2) WHERE t[i].ts < t[i + 1].ts)
  // the first payment to the last within the window
  AND duration.inSeconds(t[0].ts, t[-1].ts).seconds <= $max_window_days * 86400
  // the returned amount compared with the sent amount, in one currency
  AND t[-1].currency = t[0].currency
  AND t[-1].amount / t[0].amount >= $min_return_ratio
WITH a, t, nodes(p) AS ns
// a simple cycle: no account visited twice before the return to the origin
WHERE all(i IN range(0, size(ns) - 3) WHERE all(j IN range(i + 1, size(ns) - 2) WHERE ns[i] <> ns[j]))
WITH a, t, ns, [r IN t | r.id] AS edge_ids
ORDER BY a.id, edge_ids
LIMIT $limit
CALL (ns) {
  UNWIND ns[..-1] AS account
  // a holder is the source of HOLDS_ACCOUNT (C4); C2 makes it a LegalEntity
  MATCH (holder)-[:HOLDS_ACCOUNT]->(account)
  RETURN collect(DISTINCT holder {account: account.id, .id, .caption, .synthetic, .datasets}) AS holders
}
RETURN a.id AS origin,
       [n IN ns[..-1] | n {.id, .caption, .account_number, .synthetic, .datasets}] AS accounts,
       [r IN t | r {.id, .amount, .currency, .ts, .synthetic, .datasets, source: startNode(r).id, target: endNode(r).id}] AS hops,
       holders
