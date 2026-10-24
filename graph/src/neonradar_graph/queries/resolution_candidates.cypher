// C3 1.1.0 resolution, second query: at most 50 possible matches, highest match probability first;
// deterministic and source-hint matches have no probability and come last (Neo4j sorts nulls first in DESC).
MATCH (e:Entity {id: $id})-[p:POSSIBLY_SAME_AS]-(o:Entity)
RETURN properties(o) AS other, labels(o) AS labels, properties(p) AS link
ORDER BY p.match_probability IS NULL, p.match_probability DESC, o.id
LIMIT 50;
