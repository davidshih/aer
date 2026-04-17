-- title: Grants to Roles Changes
-- domain: RBAC
-- priority: P0
-- sources: ACCOUNT_USAGE.GRANTS_TO_ROLES
-- watermark_column: created_on
-- timestamp_field: event_timestamp
-- native_id_field: none
-- max_latency_minutes: 120
-- recommended_cadence: every_60_minutes
-- chronicle_log_type: grants_to_roles
-- description: Detect role chaining, high-risk object privileges, and grant-option changes.

SELECT
    COALESCE(deleted_on, modified_on, created_on) AS "event_timestamp",
    created_on AS "created_on",
    modified_on AS "modified_on",
    deleted_on AS "deleted_on",
    privilege AS "privilege",
    granted_on AS "granted_on",
    name AS "name",
    table_catalog AS "table_catalog",
    table_schema AS "table_schema",
    granted_to AS "granted_to",
    grantee_name AS "grantee_name",
    grant_option AS "grant_option",
    granted_by AS "granted_by",
    CASE
        WHEN deleted_on IS NULL THEN 'GRANT'
        ELSE 'REVOKE'
    END AS "action"
FROM snowflake.account_usage.grants_to_roles
WHERE (
        created_on >= DATEADD(hour, -4, CURRENT_TIMESTAMP())
        OR (modified_on IS NOT NULL AND modified_on >= DATEADD(hour, -4, CURRENT_TIMESTAMP()))
        OR (deleted_on IS NOT NULL AND deleted_on >= DATEADD(hour, -4, CURRENT_TIMESTAMP()))
      )
ORDER BY COALESCE(deleted_on, modified_on, created_on) DESC;
