// 0002_resolution: NeonRadar graph schema v1.1.0 (entity resolution)
CREATE CONSTRAINT possibly_same_as_id IF NOT EXISTS FOR ()-[r:POSSIBLY_SAME_AS]-() REQUIRE r.id IS UNIQUE;
CREATE INDEX source_record_canonical_id IF NOT EXISTS FOR (n:SourceRecord) ON (n.canonical_id);
CREATE INDEX source_record_dataset IF NOT EXISTS FOR (n:SourceRecord) ON (n.dataset);
DROP INDEX entity_names IF EXISTS;
CREATE FULLTEXT INDEX entity_names IF NOT EXISTS FOR (n:LegalEntity|Address) ON EACH [n.names_text, n.names_latin_text] OPTIONS { indexConfig: { `fulltext.analyzer`: 'standard-no-stop-words' } };
