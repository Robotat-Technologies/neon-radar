// appointment_counts: number of DIRECTOR_OF relationships each of $ids starts that still hold on $as_of (no
// end_date, or one after it). Parameters: $ids, $as_of (an ISO date). One row per id, by id.
UNWIND $ids AS person_id
MATCH (p:Entity {id: person_id})
RETURN p.id AS id,
       COUNT { (p)-[d:DIRECTOR_OF]->() WHERE coalesce(d.end_date, '') = '' OR d.end_date > $as_of } AS appointments
ORDER BY id
