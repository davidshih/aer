-- title: Trust Center Findings
-- domain: Trust Center
-- priority: P0
-- sources: SNOWFLAKE.TRUST_CENTER.FINDINGS
-- watermark_column: updated_on
-- timestamp_field: event_timestamp
-- native_id_field: event_id
-- max_latency_minutes: 60
-- recommended_cadence: every_60_minutes
-- chronicle_log_type: trust_center_finding
-- description: Collect native Snowflake Trust Center findings, severity, lifecycle state, and at-risk entities.

SELECT
    COALESCE(updated_on, end_timestamp, start_timestamp) AS "event_timestamp",
    event_id AS "event_id",
    start_timestamp AS "start_timestamp",
    end_timestamp AS "end_timestamp",
    scanner_package_id AS "scanner_package_id",
    scanner_package_name AS "scanner_package_name",
    scanner_id AS "scanner_id",
    scanner_name AS "scanner_name",
    scanner_short_description AS "scanner_short_description",
    severity AS "severity",
    completion_status AS "completion_status",
    state AS "state",
    created_on AS "created_on",
    updated_on AS "updated_on",
    total_at_risk_count AS "total_at_risk_count",
    at_risk_entities AS "at_risk_entities",
    recommendation AS "recommendation",
    impact AS "impact"
FROM snowflake.trust_center.findings
WHERE completion_status = 'SUCCEEDED'
  AND COALESCE(updated_on, end_timestamp, start_timestamp) >= DATEADD(hour, -2, CURRENT_TIMESTAMP())
ORDER BY COALESCE(updated_on, end_timestamp, start_timestamp) DESC;
