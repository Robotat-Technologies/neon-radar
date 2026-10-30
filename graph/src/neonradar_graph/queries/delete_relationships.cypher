// Reconciliation E4 (orchestrator decision under OD-10): before the relationships built from
// Ownership records are written, those with the same ids under the other types an Ownership
// can build are deleted, so a reload that changes the type moves the relationship, as Phase 1's
// loader did. The type comes from the C2 mapping table.
// lint-values: rel_type=OWNS,CONSOLIDATES,HOLDS_ACCOUNT
UNWIND $ids AS id
MATCH ()-[old:{{rel_type}} {id: id}]->()
DELETE old;
