// M2.12: the nodes of the returned ownership or shortest paths, by C2 id, for the C3 subgraph.
// A path node is an :Entity, or a :Sanction reached through SUBJECT_OF; both lookups use an index.
UNWIND $ids AS id
OPTIONAL MATCH (e:Entity {id: id})
OPTIONAL MATCH (s:Sanction {id: id})
WITH coalesce(e, s) AS n
WHERE n IS NOT NULL
RETURN {props: properties(n), labels: labels(n)} AS node;

// M2.12: the relationships of the returned paths, each found between its two ends by its type
// and its C2 id, so no relationship is scanned by id. Both ends are bound through an index
// first, so the planner expands into the pair from the end with fewer relationships (a hub
// such as a mass-registration address is never walked whole, risk R12).
UNWIND $links AS link
MATCH (a:Entity {id: link.a})
OPTIONAL MATCH (be:Entity {id: link.b})
OPTIONAL MATCH (bs:Sanction {id: link.b})
WITH link, a, coalesce(be, bs) AS b
WHERE b IS NOT NULL
MATCH (a)-[r]-(b)
WHERE type(r) = link.type AND r.id = link.id
RETURN DISTINCT {props: properties(r), type: type(r), source: startNode(r).id,
                 target: endNode(r).id} AS edge;
