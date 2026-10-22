// evidence: the nodes and relationships of one alert, re-selected by id (C4 evidence.query).
// Parameters: $node_ids, $edge_ids. `neonradar detect verify-alert` checks that both lists come back whole.
MATCH (n:Entity)
WHERE n.id IN $node_ids
WITH collect(n) AS nodes
CALL () {
  UNWIND $edge_ids AS rid
  CALL (rid) {
      MATCH (s)-[r:PAID {id: rid}]->(t) RETURN r
      UNION
      MATCH (s)-[r:OWNS {id: rid}]->(t) RETURN r
      UNION
      MATCH (s)-[r:CONTROLS {id: rid}]->(t) RETURN r
      UNION
      MATCH (s)-[r:CONSOLIDATES {id: rid}]->(t) RETURN r
      UNION
      MATCH (s)-[r:DIRECTOR_OF {id: rid}]->(t) RETURN r
      UNION
      MATCH (s)-[r:HOLDS_ACCOUNT {id: rid}]->(t) RETURN r
      UNION
      MATCH (s)-[r:HAS_ADDRESS {id: rid}]->(t) RETURN r
      UNION
      MATCH (s)-[r:REPRESENTS {id: rid}]->(t) RETURN r
      UNION
      MATCH (s)-[r:FAMILY_OF {id: rid}]->(t) RETURN r
      UNION
      MATCH (s)-[r:ASSOCIATE_OF {id: rid}]->(t) RETURN r
      UNION
      MATCH (s)-[r:HOLDS_POSITION {id: rid}]->(t) RETURN r
  }
  RETURN collect(r) AS rels
}
RETURN [n IN nodes | n.id] AS node_ids, [r IN rels | r.id] AS edge_ids, nodes, rels
