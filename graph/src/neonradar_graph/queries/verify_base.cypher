// Phase 1's invariants I1 to I6 (PHASE-1.md 5.2, contracts/C2-graph-schema.md) as counts, for
// `neonradar graph verify`; I7 to I14 are in verify_resolution.cypher. I2 checks the nodes the
// C2 flag table puts :Synthetic on (:Entity and :Sanction) and every node that carries it.
// I1
MATCH (n:Entity)
WHERE n.id IS NULL OR n.schema IS NULL OR n.caption IS NULL OR n.datasets IS NULL
   OR n.synthetic IS NULL
RETURN count(n) AS violations;
// I2
MATCH (n) WHERE (n:Entity OR n:Sanction OR n:Synthetic)
  AND n:Synthetic <> coalesce(n.synthetic = true, false)
RETURN count(n) AS violations;
// I3
MATCH (a)-[r:PAID]->(b)
WHERE NOT (a:Account AND b:Account) OR NOT coalesce(r.amount > 0, false)
   OR NOT coalesce(r.currency =~ '[A-Z]{3}', false)
   OR NOT (r.ts IS :: ZONED DATETIME NOT NULL)
RETURN count(r) AS violations;
// I4
MATCH (a:Account) WHERE NOT EXISTS { (:LegalEntity)-[:HOLDS_ACCOUNT]->(a) }
RETURN count(a) AS violations;
// I5
MATCH ()-[r:OWNS]->()
WITH r, r.share_pct_min AS low, r.share_pct_max AS high
WHERE (low IS NOT NULL AND NOT (0 <= low AND low <= 100))
   OR (high IS NOT NULL AND NOT (0 <= high AND high <= 100))
   OR (low IS NOT NULL AND high IS NOT NULL AND low > high)
RETURN count(r) AS violations;
// I6
MATCH (:Alert {wording_class: 'synthetic_scenario'})-[:FLAGS]->(n)
WHERE NOT coalesce(n.synthetic = true, false)
RETURN count(n) AS violations;
