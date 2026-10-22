// I15: the only relationship between a synthetic and a non-synthetic node is HOLDS_ACCOUNT from a
// non-synthetic organisation to a synthetic account (C2 1.2.0; support nodes have no synthetic
// property, so FLAGS, PRODUCED and RESOLVED_TO never count)
MATCH (a)-[r]->(b)
WHERE a.synthetic <> b.synthetic
  AND NOT (type(r) = 'HOLDS_ACCOUNT' AND a.synthetic = false AND a:Organization AND b:Account)
RETURN count(r) AS violations;
// I16: no payment joins two accounts that are both held by non-synthetic entities
MATCH (h1:LegalEntity)-[:HOLDS_ACCOUNT]->(:Account)-[p:PAID]-(:Account)<-[:HOLDS_ACCOUNT]-(h2:LegalEntity)
WHERE NOT h1:Synthetic AND NOT h2:Synthetic
RETURN count(DISTINCT p) AS violations;
// I17: no alert names a non-synthetic person (a :LegalEntity that is not an :Organization) as a
// subject or among its evidence nodes, and no alert that involves a non-synthetic entity has a
// payment among its evidence relationships (R-REAL, G12; :Alert.evidence_node_ids and
// :Alert.evidence_edge_ids, C2 1.2.0)
MATCH (a:Alert)
WHERE EXISTS { (a)-[:FLAGS]->(p:LegalEntity) WHERE NOT p:Organization AND p.synthetic = false }
   OR EXISTS {
        MATCH (p:Entity)
        WHERE p.id IN coalesce(a.evidence_node_ids, [])
          AND p:LegalEntity AND NOT p:Organization AND p.synthetic = false
      }
   OR (a.involves_real_entities = true
       AND EXISTS { MATCH ()-[x:PAID]->() WHERE x.id IN coalesce(a.evidence_edge_ids, []) })
RETURN count(a) AS violations;
