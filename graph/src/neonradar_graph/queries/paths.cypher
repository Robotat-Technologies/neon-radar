// C3 1.1.0 paths: up to 5 shortest paths, any direction, over the allowed relationship types.
// lint-values: max_hops=1,2,3,4,5,6
MATCH (a:Entity {id: $from_id})
WITH a
MATCH (b:Entity {id: $to_id})
MATCH p = SHORTEST 5 (a)((x)-[r]-(y) WHERE type(r) IN $rel_types){1,{{max_hops}}}(b)
RETURN [n IN nodes(p) | n.id] AS node_ids, [rel IN relationships(p) | rel.id] AS edge_ids,
       [rel IN relationships(p) | type(rel)] AS types,
       [rel IN relationships(p) | startNode(rel).id] AS starts,
       [rel IN relationships(p) | rel.share_pct_min] AS mins,
       [rel IN relationships(p) | rel.share_pct_max] AS maxes,
       [rel IN relationships(p) | coalesce(rel.share_min_exclusive, false)] AS mins_open,
       [rel IN relationships(p) | coalesce(rel.share_max_exclusive, false)] AS maxes_open,
       length(p) AS hops
ORDER BY hops, node_ids;
