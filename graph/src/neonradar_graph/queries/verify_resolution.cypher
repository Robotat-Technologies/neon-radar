// Invariants I7 to I14 (C2 1.1.0) as counts, for `neonradar graph verify`; I1 to I6 are in
// verify_base.cypher. As PHASE-2.md M2.11 gives them, except I11's flag check, which follows the
// C2 flag table (reconciliation E2, orchestrator decision under OD-10): :PEP and :RCA also
// stand for the sub-topics role.pep.* and role.rca.*, and :Sanctioned only for `sanction`.
// I7
MATCH (s:SourceRecord)
OPTIONAL MATCH (s)-[r:RESOLVED_TO]->(e:Entity)
WITH s, count(r) AS n, collect(e) AS es
WHERE n <> 1 OR NOT es[0].id STARTS WITH 'nr-' OR NOT s.id IN es[0].referents
RETURN count(s) AS violations;
// I8 (merged entities)
MATCH (e:Entity) WHERE e.cluster_size >= 2
OPTIONAL MATCH (s:SourceRecord)-[:RESOLVED_TO]->(e)
WITH e, count(s) AS n
WHERE n <> e.cluster_size OR size(e.referents) <> e.cluster_size
RETURN count(e) AS violations;
// I8 (single-record entities)
MATCH (e:Entity) WHERE coalesce(e.cluster_size, 1) = 1 AND e.referents <> [e.id]
RETURN count(e) AS violations;
// I9
MATCH (s:SourceRecord)-[:RESOLVED_TO]->(e:Entity) WHERE s.synthetic <> e.synthetic
RETURN count(s) AS violations;
// I10 (endpoints and direction)
MATCH (a)-[r:POSSIBLY_SAME_AS]->(b)
WHERE a = b OR NOT a:LegalEntity OR NOT b:LegalEntity OR a.synthetic <> b.synthetic OR a.id >= b.id
RETURN count(r) AS violations;
// I10 (at most one per pair)
MATCH (a)-[r:POSSIBLY_SAME_AS]-(b) WHERE a.id < b.id
WITH a, b, count(r) AS n WHERE n > 1
RETURN count(*) AS violations;
// I11 (topics of merged entities)
MATCH (s:SourceRecord)-[:RESOLVED_TO]->(e:Entity)
WITH e, collect(s.topics) AS lists
WITH e, reduce(acc = [], l IN lists | acc + [t IN coalesce(l, []) WHERE NOT t IN acc]) AS merged
WHERE size(merged) <> size(coalesce(e.topics, [])) OR any(t IN merged WHERE NOT t IN coalesce(e.topics, []))
RETURN count(e) AS violations;
// I11 (flags follow topics)
MATCH (e:Entity)
WHERE (e:Sanctioned) <> ('sanction' IN coalesce(e.topics, []))
   OR (e:PEP) <> any(t IN coalesce(e.topics, []) WHERE t = 'role.pep' OR t STARTS WITH 'role.pep.')
   OR (e:RCA) <> any(t IN coalesce(e.topics, []) WHERE t = 'role.rca' OR t STARTS WITH 'role.rca.')
RETURN count(e) AS violations;
// I12
MATCH (n)-[r:OWNS|CONTROLS]->(n)
RETURN count(r) AS violations;
// I13
MATCH (s:SourceRecord)
MATCH (e:Entity {id: s.id})
RETURN count(e) AS violations;
// I14
MATCH ()-[r:CONTROLS]->()
WHERE (r.share_pct_min IS NOT NULL AND (r.share_pct_min < 0 OR r.share_pct_min > 100))
   OR (r.share_pct_max IS NOT NULL AND (r.share_pct_max < 0 OR r.share_pct_max > 100))
   OR (r.share_pct_min IS NOT NULL AND r.share_pct_max IS NOT NULL AND r.share_pct_min > r.share_pct_max)
RETURN count(r) AS violations;
