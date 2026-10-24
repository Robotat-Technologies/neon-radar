// C3 1.1.0 ownership, direction=down: chains of OWNS that start at the root (its holdings).
// One query per max_hops value; Python picks the file variant and never builds Cypher from input.
// Effective shares are rounded to 4 decimals here, so the filter, the order and the API see the same values.
// lint-values: max_hops=1,2,3,4,5,6,7,8
MATCH (root:Entity {id: $root_id})
MATCH p = (root)-[:OWNS]->{1,{{max_hops}}}(bottom:LegalEntity)
WHERE all(n IN nodes(p) WHERE single(m IN nodes(p) WHERE m = n))
WITH p, relationships(p) AS rels
WITH p, rels,
     CASE WHEN all(r IN rels WHERE r.share_pct_min IS NOT NULL)
          THEN round(reduce(acc = 1.0, r IN rels | acc * r.share_pct_min / 100.0) * 100.0, 4) END AS eff_min,
     CASE WHEN all(r IN rels WHERE r.share_pct_max IS NOT NULL)
          THEN round(reduce(acc = 1.0, r IN rels | acc * r.share_pct_max / 100.0) * 100.0, 4) END AS eff_max,
     any(r IN rels WHERE coalesce(r.share_min_exclusive, false)) AS min_open,
     any(r IN rels WHERE coalesce(r.share_max_exclusive, false)) AS max_open
WHERE $min_share = 0
   OR (eff_max IS NOT NULL AND (eff_max > $min_share OR (eff_max = $min_share AND NOT max_open)))
RETURN [n IN nodes(p) | n.id] AS node_ids, [r IN rels | r.id] AS edge_ids,
       eff_min, eff_max,
       CASE WHEN eff_min IS NULL THEN null ELSE min_open END AS eff_min_exclusive,
       CASE WHEN eff_max IS NULL THEN null ELSE max_open END AS eff_max_exclusive,
       size(rels) AS hops
ORDER BY eff_max IS NULL, eff_max DESC, hops, node_ids
LIMIT $scan_limit;
