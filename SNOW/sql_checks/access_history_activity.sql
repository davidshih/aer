-- title: Access History Activity
-- domain: Data Access
-- priority: P0
-- sources: ACCOUNT_USAGE.ACCESS_HISTORY
-- watermark_column: query_start_time
-- timestamp_field: event_timestamp
-- native_id_field: query_id
-- max_latency_minutes: 180
-- recommended_cadence: every_60_minutes
-- chronicle_log_type: access_history
-- description: Capture object-level access, policy references, and write lineage for sensitive data monitoring.

SELECT
    query_start_time AS "event_timestamp",
    query_id AS "query_id",
    query_start_time AS "query_start_time",
    user_name AS "user_name",
    direct_objects_accessed AS "direct_objects_accessed",
    base_objects_accessed AS "base_objects_accessed",
    objects_modified AS "objects_modified",
    object_modified_by_ddl AS "object_modified_by_ddl",
    policies_referenced AS "policies_referenced",
    parent_query_id AS "parent_query_id",
    root_query_id AS "root_query_id",
    event_source AS "event_source",
    additional_properties AS "additional_properties"
FROM snowflake.account_usage.access_history
WHERE query_start_time >= DATEADD(hour, -6, CURRENT_TIMESTAMP())
ORDER BY query_start_time DESC;
