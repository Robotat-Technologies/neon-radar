// L14: one POSSIBLY_SAME_AS per line of candidates.jsonl, from the smaller id to the larger,
// only between two LegalEntity nodes (I10); the loader compares `written` with the rows sent
UNWIND $rows AS row
MATCH (a:Entity {id: row.a}) WHERE a:LegalEntity
MATCH (b:Entity {id: row.b}) WHERE b:LegalEntity
MERGE (a)-[r:POSSIBLY_SAME_AS {id: row.id}]->(b)
SET r += row.props
RETURN count(r) AS written;
