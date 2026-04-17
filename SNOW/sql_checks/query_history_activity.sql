-- title: Query History Activity
-- domain: Query and Control Plane
-- priority: P0
-- sources: INFORMATION_SCHEMA.QUERY_HISTORY*(), ACCOUNT_USAGE.QUERY_HISTORY
-- watermark_column: start_time
-- timestamp_field: event_timestamp
-- native_id_field: query_id
-- max_latency_minutes: 45
-- recommended_cadence: every_15_minutes
-- chronicle_log_type: query_history
-- description: Track privilege changes, export activity, network policy changes, account parameter changes, and risky control-plane SQL.

SELECT
    start_time AS "event_timestamp",
    query_id AS "query_id",
    start_time AS "start_time",
    end_time AS "end_time",
    query_type AS "query_type",
    query_text AS "query_text",
    user_name AS "user_name",
    role_name AS "role_name",
    role_type AS "role_type",
    warehouse_name AS "warehouse_name",
    warehouse_size AS "warehouse_size",
    warehouse_type AS "warehouse_type",
    query_tag AS "query_tag",
    execution_status AS "execution_status",
    error_code AS "error_code",
    error_message AS "error_message",
    total_elapsed_time AS "total_elapsed_time",
    bytes_scanned AS "bytes_scanned",
    bytes_written AS "bytes_written",
    bytes_written_to_result AS "bytes_written_to_result",
    bytes_read_from_result AS "bytes_read_from_result",
    rows_inserted AS "rows_inserted",
    rows_updated AS "rows_updated",
    rows_deleted AS "rows_deleted",
    rows_unloaded AS "rows_unloaded",
    rows_produced AS "rows_produced",
    outbound_data_transfer_cloud AS "outbound_data_transfer_cloud",
    outbound_data_transfer_region AS "outbound_data_transfer_region",
    outbound_data_transfer_bytes AS "outbound_data_transfer_bytes",
    session_id AS "session_id",
    authn_event_id AS "authn_event_id",
    query_hash AS "query_hash",
    query_parameterized_hash AS "query_parameterized_hash",
    is_client_generated_statement AS "is_client_generated_statement"
FROM snowflake.account_usage.query_history
WHERE start_time >= DATEADD(hour, -4, CURRENT_TIMESTAMP())
  AND (
        query_type IN (
            'GRANT',
            'REVOKE',
            'ALTER_ACCOUNT',
            'CREATE_NETWORK_POLICY',
            'ALTER_NETWORK_POLICY',
            'DROP_NETWORK_POLICY',
            'CREATE_USER',
            'ALTER_USER',
            'DROP_USER',
            'CREATE_ROLE',
            'ALTER_ROLE',
            'DROP_ROLE',
            'COPY',
            'UNLOAD'
        )
        OR query_text ILIKE 'COPY INTO ''s3://%'
        OR query_text ILIKE 'COPY INTO ''gcs://%'
        OR query_text ILIKE 'COPY INTO ''azure://%'
        OR query_text ILIKE 'COPY INTO ''https://%'
        OR query_text ILIKE '%PREVENT_UNLOAD_TO_INLINE_URL%'
        OR query_text ILIKE '%REQUIRE_STORAGE_INTEGRATION_FOR_STAGE_CREATION%'
        OR query_text ILIKE '%REQUIRE_STORAGE_INTEGRATION_FOR_STAGE_OPERATION%'
      )
ORDER BY start_time DESC;
