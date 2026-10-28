// listed_entities: every :Sanctioned entity with its labels, datasets and the :Sanction nodes it is SUBJECT_OF
// (by sanction id). By entity id.
MATCH (e:Entity:Sanctioned)
RETURN e.id AS entity, labels(e) AS labels, coalesce(e.datasets, []) AS datasets,
       COLLECT { MATCH (e)-[:SUBJECT_OF]->(s:Sanction)
                 RETURN {id: s.id, datasets: coalesce(s.datasets, []), authority: coalesce(s.authority, ''),
                         program: coalesce(s.program, ''), provisions: coalesce(s.provisions, []),
                         start_date: coalesce(s.start_date, ''), end_date: coalesce(s.end_date, '')}
                 ORDER BY s.id } AS sanctions
ORDER BY entity
