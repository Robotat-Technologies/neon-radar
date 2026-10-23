// L13 for additive loads (M2.11): which owners outside this load the graph holds as a
// :LegalEntity, by id or through a :SourceRecord. A non-strict load keeps a BankAccount whose
// only holder is one of them (C1 R8 counts the holder in the graph) and drops the others, so
// invariant I4 still holds. Read-only.
UNWIND $ids AS id
OPTIONAL MATCH (direct:Entity {id: id}) WHERE direct:LegalEntity
OPTIONAL MATCH (:SourceRecord {id: id})-[:RESOLVED_TO]->(via:Entity) WHERE via:LegalEntity
WITH id, direct, via WHERE direct IS NOT NULL OR via IS NOT NULL
RETURN DISTINCT id
ORDER BY id
LIMIT $limit;
