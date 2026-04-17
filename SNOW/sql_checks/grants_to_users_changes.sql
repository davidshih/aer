-- title: Grants to Users Changes
-- domain: RBAC
-- priority: P0
-- sources: ACCOUNT_USAGE.GRANTS_TO_USERS
-- watermark_column: created_on
-- timestamp_field: event_timestamp
-- native_id_field: none
-- max_latency_minutes: 120
-- recommended_cadence: every_60_minutes
-- chronicle_log_type: grants_to_users
-- description: Detect direct user role grants and revocations, including high-risk administrative roles.

SELECT
    COALESCE(deleted_on, created_on) AS "event_timestamp",
    created_on AS "created_on",
    deleted_on AS "deleted_on",
    role AS "role",
    granted_to AS "granted_to",
    grantee_name AS "grantee_name",
    granted_by AS "granted_by",
    CASE
        WHEN deleted_on IS NULL THEN 'GRANT'
        ELSE 'REVOKE'
    END AS "action"
FROM snowflake.account_usage.grants_to_users
WHERE (
        created_on >= DATEADD(hour, -4, CURRENT_TIMESTAMP())
        OR (deleted_on IS NOT NULL AND deleted_on >= DATEADD(hour, -4, CURRENT_TIMESTAMP()))
      )
ORDER BY COALESCE(deleted_on, created_on) DESC;
