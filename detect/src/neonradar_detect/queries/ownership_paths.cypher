// ownership_paths: maximal paths of 1 to {{max_hops}} OWNS relationships that still hold on $as_of (no end_date,
// or one after it), from a top (a legal entity no such OWNS points to) that owns an organisation, through
// organisations, to a leaf company (one that owns no organisation through such an OWNS), never repeating a
// node. Ordered by the node ids along the path. Parameters: $limit, $as_of (an ISO date).
// lint-values: max_hops=2,6,8
MATCH p = (top:LegalEntity)-[:OWNS*1..{{max_hops}}]->(leaf:Company)
WHERE all(r IN relationships(p) WHERE coalesce(r.end_date, '') = '' OR r.end_date > $as_of)
  AND NOT EXISTS { ()-[o:OWNS]->(top) WHERE coalesce(o.end_date, '') = '' OR o.end_date > $as_of }
  AND all(n IN tail(nodes(p)) WHERE n:Organization)
  AND NOT EXISTS { (leaf)-[o:OWNS]->(:Organization) WHERE coalesce(o.end_date, '') = '' OR o.end_date > $as_of }
  AND size(nodes(p)) = size(apoc.coll.toSet(nodes(p)))
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
