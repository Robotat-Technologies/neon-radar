// C3 1.1.0 resolution, first query: the entity and its source records, in record id order.
MATCH (e:Entity {id: $id})
OPTIONAL MATCH (s:SourceRecord)-[r:RESOLVED_TO]->(e)
WITH e, s, r
ORDER BY s.id
WITH e, collect(CASE WHEN s IS NULL THEN NULL ELSE {record: properties(s), link: properties(r)} END) AS members
RETURN properties(e) AS entity, labels(e) AS labels, members;
