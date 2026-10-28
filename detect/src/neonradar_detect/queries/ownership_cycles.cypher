// ownership_cycles: simple cycles of 2 to {{max_hops}} OWNS relationships that still hold on $as_of (no end_date,
// or one after it), each once, starting at its smallest node id (node_ids[0] = node_ids[-1]). Ordered by the
// node ids. Parameters: $limit, $as_of (an ISO date).
// lint-values: max_hops=2,6,8
MATCH p = (a:LegalEntity)-[:OWNS*2..{{max_hops}}]->(a)
WHERE all(r IN relationships(p) WHERE coalesce(r.end_date, '') = '' OR r.end_date > $as_of)
  AND all(n IN nodes(p) WHERE n.id >= a.id)
  AND size(tail(nodes(p))) = size(apoc.coll.toSet(tail(nodes(p))))
WITH [n IN nodes(p) | n.id] AS node_ids, relationships(p) AS rels
ORDER BY node_ids
LIMIT $limit
RETURN node_ids,
       [r IN rels | {rel_type: type(r), rel_id: r.id, source: startNode(r).id, target: endNode(r).id,
                     share_min: r.share_pct_min, share_max: r.share_pct_max,
                     share_min_exclusive: coalesce(r.share_min_exclusive, false),
                     share_max_exclusive: coalesce(r.share_max_exclusive, false),
                     is_nominee: coalesce(r.is_nominee, false), role: coalesce(r.role, ''),
                     start_date: coalesce(r.start_date, ''), end_date: coalesce(r.end_date, ''), control_type: ''}] AS links
