-- title: Login History Activity
-- domain: Authentication
-- priority: P0
-- sources: INFORMATION_SCHEMA.LOGIN_HISTORY(), ACCOUNT_USAGE.LOGIN_HISTORY
-- watermark_column: event_timestamp
-- timestamp_field: event_timestamp
-- native_id_field: event_id
-- max_latency_minutes: 120
-- recommended_cadence: every_15_minutes
-- chronicle_log_type: login_history
-- description: Monitor successful and failed logins, authentication factors, client fingerprints, and login errors.

SELECT
    event_id AS "event_id",
    event_timestamp AS "event_timestamp",
    event_type AS "event_type",
    user_name AS "user_name",
    client_ip AS "client_ip",
    reported_client_type AS "reported_client_type",
    reported_client_version AS "reported_client_version",
    first_authentication_factor AS "first_authentication_factor",
    second_authentication_factor AS "second_authentication_factor",
    first_authentication_factor_id AS "first_authentication_factor_id",
    second_authentication_factor_id AS "second_authentication_factor_id",
    is_success AS "is_success",
    error_code AS "error_code",
    error_message AS "error_message",
    connection AS "connection",
    client_private_link_id AS "client_private_link_id",
    login_details AS "login_details"
FROM snowflake.account_usage.login_history
WHERE event_timestamp >= DATEADD(hour, -4, CURRENT_TIMESTAMP())
ORDER BY event_timestamp DESC;
