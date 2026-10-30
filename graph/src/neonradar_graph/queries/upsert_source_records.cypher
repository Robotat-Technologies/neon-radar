// L11: one :SourceRecord per member of a merged entity
UNWIND $rows AS row
MERGE (s:SourceRecord {id: row.id})
SET s += row.props;
