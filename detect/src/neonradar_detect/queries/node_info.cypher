// node_info: evidence nodes, and the holders of evidence accounts, for the policy and the wording.
// Parameters: $ids. One row per node, by id; holders of an account sorted by id.
UNWIND $ids AS node_id
MATCH (n:Entity {id: node_id})
OPTIONAL MATCH (h:Entity)-[:HOLDS_ACCOUNT]->(n)
WITH n, h ORDER BY h.id
WITH n, collect(h {.id, labels: labels(h), caption: coalesce(h.caption, h.id), .synthetic,
                   datasets: coalesce(h.datasets, [])}) AS holders
RETURN n.id AS id, labels(n) AS labels, coalesce(n.caption, n.id) AS caption, n.synthetic AS synthetic,
       coalesce(n.datasets, []) AS datasets, holders
ORDER BY id
