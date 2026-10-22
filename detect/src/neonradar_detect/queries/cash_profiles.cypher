// cash_profiles: companies whose accounts received cash deposits in $currency in [$prior_start, $end): sums in
// pence (each amount rounded to pence first, so sums are exact) and counts for [$start, $end) and for
// [$prior_start, $start), the sector, and the postcode and city of the registered address (the smallest
// postcode when there are several). By holder id. Parameters: $prior_start, $start, $end, $currency, $limit.
MATCH (c:Company)-[:HOLDS_ACCOUNT]->(a:Account)<-[r:PAID]-(:Account)
WHERE r.channel = 'cash_deposit' AND r.currency = $currency
  AND r.ts >= datetime($prior_start) AND r.ts < datetime($end)
WITH c, a, r, toInteger(round(r.amount * 100)) AS pence, r.ts >= datetime($start) AS recent
WITH c, collect(DISTINCT a.id) AS accounts,
     sum(CASE WHEN recent THEN pence ELSE 0 END) AS window_pence, sum(CASE WHEN recent THEN 1 ELSE 0 END) AS window_deposits,
     sum(CASE WHEN recent THEN 0 ELSE pence END) AS prior_pence, sum(CASE WHEN recent THEN 0 ELSE 1 END) AS prior_deposits
ORDER BY c.id
LIMIT $limit
OPTIONAL CALL (c) {
  MATCH (c)-[h:HAS_ADDRESS]->(addr:Address)
  WHERE h.role = 'registered'
  RETURN coalesce(addr.postal_code, '') AS postal_code, coalesce(addr.city, '') AS city
  ORDER BY postal_code, city
  LIMIT 1
}
RETURN c.id AS holder, coalesce(c.sector, '') AS sector, coalesce(postal_code, '') AS postal_code,
       coalesce(city, '') AS city, apoc.coll.sort(accounts) AS accounts,
       window_pence, window_deposits, prior_pence, prior_deposits
ORDER BY holder
