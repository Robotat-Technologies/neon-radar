// An entity id or the id of any record merged into it (C3: "accepts a canonical id or any id in referents").
MATCH (e:Entity {id: $id})
RETURN e.id AS id
UNION
MATCH (:SourceRecord {id: $id})-[:RESOLVED_TO]->(e:Entity)
RETURN e.id AS id;
