// M2.13 `neonradar bench queries`: the ids of the eligible entities, the :Company and :Person
// nodes with at least one OWNS relationship (either way), sorted by id. Python picks `n` of them
// by the order of sha1("<seed>:<id>"), since Neo4j has no sha1 without APOC. Read-only.
MATCH (e:Entity)
WHERE (e:Company OR e:Person) AND EXISTS { (e)-[:OWNS]-() }
RETURN e.id AS id
ORDER BY id
LIMIT $limit;
