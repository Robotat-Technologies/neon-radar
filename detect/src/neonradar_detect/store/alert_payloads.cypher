// alert_payloads: the stored C4 payload of each alert id asked for, by alert id (`neonradar detect
// verify-alert`). Parameters: $alert_ids.
UNWIND $alert_ids AS alert_id
MATCH (a:Alert {alert_id: alert_id})
RETURN a.alert_id AS alert_id, a.payload AS payload
ORDER BY alert_id
