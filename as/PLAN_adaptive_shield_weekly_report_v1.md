# Adaptive Shield 週報實作參考（v1）

## 1. 目標
MVP 只做 Adaptive Shield 主流程：

1. 拉取過去 `x` 天（預設 3 天）alerts。
2. 過濾 `configuration_drift` 與 `integration_failure`。
3. 補 security check 明細。
4. 展開 affected entities。
5. 匯出 XLSX + CSV。

ServiceNow 先保留 stub 欄位，不做 Selenium 實抓。

## 2. API 定稿
1. Base URL: `https://api.adaptive-shield.com`
2. Authorization Header: `Authorization: Token {api_key}`
3. 核心端點：
   - `GET /api/v1/accounts`
   - `GET /api/v1/accounts/{accountId}/alerts`
   - `GET /api/v1/accounts/{accountId}/security_checks/{securityCheckId}`
   - `GET /api/v1/accounts/{accountId}/security_checks/{securityCheckId}/affected`
   - `GET /api/v1/accounts/{accountId}/integrations`
4. 分頁規則：
   - 優先 `next_page_uri`
   - 若存在 `meta.pagination`，則依 `next/offset/limit` 續抓
   - 兩者都不存在則單頁結束

## 3. Notebook Contract（Input / Output）

### Cell 0 - Project intro
Input: None  
Output: Project scope and version

### Cell 1 - Standalone initialization
Input:
- `AS_API_KEY`
- `AS_BASE_URL`
- `AS_ACCOUNT_IDS`
- `LOOKBACK_DAYS`
- `OUTPUT_ROOT`
- `EXPORT_XLSX`
- `EXPORT_CSV`
- `SNOW_ENABLED`
- `RATE_LIMIT_PER_MINUTE`
- `REQUEST_TIMEOUT_SECONDS`
- `MAX_RETRIES`

Output:
- Embedded runtime functions (API client, transform, UI renderer, exporter, SNOW stub)
- `config` dictionary
- `RUN_TS` timestamp (UTC)
- output directory path

### Cell 2 - API client init
Input: `config`  
Output: `client` (`AdaptiveShieldClient`)

### Cell 3 - Accounts collection
Input: `AS_ACCOUNT_IDS` (optional)  
Output: `accounts_df` (`account_id`, `account_name`)

### Cell 4 - Alerts collection
Input:
- `account_id`
- `from_date`
- `to_date`
- `alert_type` (configuration_drift / integration_failure)

Output:
- `alerts_raw_df`
- `alerts_filtered_df` (not archived, target types only)

### Cell 5 - Security check enrichment
Input: `alerts_filtered_df`  
Output:
- `checks_df`
- `pipeline_errors` append failures per alert/check

### Cell 6 - Affected entities enrichment
Input:
- `account_id`
- `security_check_id`
- `is_global`

Output:
- `entities_df` (one row per entity)
- `affected_resolve_log_df` (`global` / `fetched` / `unresolved`)
- Full entity details from `GET /security_checks/{securityCheckId}/affected` mapped into:
  - `entity_extra_context_json`
  - `entity_usage_json`
  - `entity_raw_json`

### Cell 7 - Summary table
Input:
- `alerts_filtered_df`
- `checks_df`
- `entities_df`
- `accounts_df`

Output:
- `summary_df`

### Cell 8 - Configuration drift timeline UI
Input:
- `summary_df` (drift subset)
- `entities_df`

Output:
- Infographic timeline view (latest on top)
- Grouped cards by `integration + security check`
- Folded sections for details/remediation/entity payload/history

### Cell 9 - ServiceNow stub
Input:
- `SNOW_ENABLED`
- `LOOKBACK_DAYS`

Output:
- `snow_df` (stub dataframe)
- `summary_with_snow_df` (left-merged)

### Cell 10 - Quality checks
Input:
- `summary_with_snow_df`
- `entities_df`
- `pipeline_errors`

Output:
- `quality_report_df`
- `errors_df`

### Cell 11 - Export
Input:
- `summary_with_snow_df`
- `entities_df`
- `errors_df`
- export switches

Output files (under `output/YYYY-MM-DD/`):
- `AS_Weekly_Report_{timestamp}.xlsx`
- `AS_Weekly_Summary_{timestamp}.csv`
- `AS_Weekly_Entities_{timestamp}.csv`
- `AS_Weekly_Errors_{timestamp}.csv`

## 4. 固定輸出欄位
`summary_df`:
- `change_datetime`
- `security_check_name`
- `security_check_details`
- `remediation_steps`
- `impact_level`
- `current_status`
- `affected_entities_count`
- `affected_scope`
- `affected_entities_detail`
- `account_id`
- `account_name`
- `integration_id`
- `integration_name`
- `integration_alias`
- `saas_name`
- `security_check_id`
- `alert_id`
- `alert_type`
- `source`
- `source_id`
- `is_archived`
- `ticket_number`
- `ticket_owner`
- `ticket_status`
- `ticket_last_update_datetime`
- `ticket_last_update_content`
- `extracted_at_utc`

`entities_df`:
- `account_id`
- `security_check_id`
- `alert_id`
- `entity_type`
- `entity_name`
- `entity_dismissed`
- `entity_dismissed_reason`
- `entity_dismiss_expiration_date`
- `entity_extra_context_json`
- `entity_usage_json`
- `entity_raw_json`

## 7. UI 驗收（Configuration Drift）
1. 同 integration + security check 需合併為單一卡片。
2. 以目前 status 分群，`failed` 先顯示，`passed` 預設收合。
3. 每個 status 群組內採時間軸呈現，最新 change 在上方。
4. 卡片標題需同時顯示 `SaaS name`、`integration alias`、`security check name`。
5. `details` 與 `remediation` 預設為可折疊區塊。
6. `affected entities` 預設折疊，且可展開 entity-level 全細節（extra context/usage/raw payload）。
7. flip-flop（failed/passed 來回）需標記 badge 並保留折疊歷史。

## 5. 錯誤處理
1. 401 -> fail fast.
2. 429 -> retry with `Retry-After` else exponential backoff.
3. 5xx -> retry up to max retries.
4. 單一 alert/check/entity 失敗 -> 記錄到 `errors_df`，不中斷整體流程。
5. 空資料 -> 仍輸出空 schema 檔案。

## 6. 測試驗收
1. 分頁：`next_page_uri` 與 `meta.pagination` 都可完整拉回。
2. 型別過濾：僅 `configuration_drift` + `integration_failure`。
3. global 判定：`is_global=true` -> `affected_scope=global`。
4. 匯出：同次執行輸出 1 xlsx + 3 csv。
5. 容錯：429/5xx 可恢復；401 直接終止。
