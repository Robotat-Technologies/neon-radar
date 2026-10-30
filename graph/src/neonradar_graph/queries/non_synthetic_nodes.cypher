// Nodes of the default instance that are not synthetic (C2 L17): any `synthetic = false`, and any
// :Entity or :Sanction without the :Synthetic label (I2). `neonradar eval run --engine neo4j`
// wipes the instance only when this count is 0.
MATCH (n)
WHERE n.synthetic = false OR ((n:Entity OR n:Sanction) AND NOT n:Synthetic)
RETURN count(n) AS n
