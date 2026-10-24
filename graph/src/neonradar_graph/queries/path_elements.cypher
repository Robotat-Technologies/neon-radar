// M2.12: the nodes of the returned ownership or shortest paths, by C2 id, for the C3 subgraph.
// A path node is an :Entity, or a :Sanction reached through SUBJECT_OF; both lookups use an index.
UNWIND $ids AS id
OPTIONAL MATCH (e:Entity {id: id})
OPTIONAL MATCH (s:Sanction {id: id})
WITH coalesce(e, s) AS n
WHERE n IS NOT NULL
RETURN {props: properties(n), labels: labels(n)} AS node;

// M2.12: the relationships of the returned paths, each found from its :Entity end by its type,
// its C2 id and its other end, so no relationship is scanned by id.
UNWIND $links AS link
MATCH (a:Entity {id: link.a})-[r]-(b)
WHERE type(r) = link.type AND r.id = link.id AND b.id = link.b
RETURN DISTINCT {props: properties(r), type: type(r), source: startNode(r).id,
                 target: endNode(r).id} AS edge;
