# Adaptive Shield 週報實作參考（v2, with ServiceNow Mapping）

## 1. 目標
主流程維持：

1. 拉取過去 `x` 天（預設 3 天）alerts。
2. 過濾 `configuration_drift` 與 `integration_failure`。
3. 補 security check 明細。
4. 展開 affected entities。
5. 匯出 XLSX + CSV。

新增 ServiceNow enhancement：

1. 用 Selenium 自動抓 incidents（`short description` 包含 `AdaptiveShield`，opened date 在 lookback 內）。
2. 將 incidents 映射到 `SaaS | Alias | Check`。
3. 回填票務欄位到 summary。
4. 追加一個含票務狀態的 Drift UI（保留原本 Cell 8 UI）。

## 2. API 定稿（Adaptive Shield）
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
- `SNOW_BASE_URL`
- `SNOW_USERNAME`
- `SNOW_PASSWORD`
- `SNOW_COOKIE_PATH`
- `SNOW_HEADLESS`
- `SNOW_USER_DATA_DIR`
- `SNOW_CHROMEDRIVER_PATH`
- `SNOW_LOGIN_TIMEOUT_SECONDS`
- `SNOW_MAX_INCIDENTS`
- `SNOW_FETCH_DETAIL_NOTES`
- `SNOW_INCIDENT_QUERY`
- `RATE_LIMIT_PER_MINUTE`
- `REQUEST_TIMEOUT_SECONDS`
- `MAX_RETRIES`

Output:
- Embedded runtime functions (AS client, transform, exporter, drift UI, ServiceNow collection/mapping)
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

### Cell 7 - Summary table
Input:
- `alerts_filtered_df`
- `checks_df`
- `entities_df`
- `accounts_df`

Output:
- `summary_df`

### Cell 8 - Configuration drift timeline UI (baseline)
Input:
- `summary_df` (drift subset)
- `entities_df`

Output:
- Baseline infographic timeline view

### Cell 9 - ServiceNow Collection + Mapping
Input:
- `summary_df`
- `LOOKBACK_DAYS`
- `config` (SNOW settings)

Output:
- `snow_row_df`（alert 粒度）
- `snow_incidents_raw_df`（抓回原始 incident）
- `snow_ticket_details_df`（check-key 粒度）
- `summary_with_snow_df`

### Cell 10 - Configuration drift timeline UI (enhanced with ServiceNow)
Input:
- `summary_with_snow_df` (drift subset)
- `entities_df`
- `snow_ticket_details_df`

Output:
- Enhanced timeline with ServiceNow badge, open ticket count, stale days hint, folded ticket list

### Cell 11 - Quality checks
Input:
- `summary_with_snow_df`
- `entities_df`
- `snow_incidents_raw_df`
- `snow_ticket_details_df`
- `pipeline_errors`

Output:
- `quality_report_df`
- `errors_df`

### Cell 12 - Export
Input:
- `summary_with_snow_df`
- `entities_df`
- `errors_df`
- `snow_ticket_details_df`

Output files (under `output/YYYY-MM-DD/`):
- `AS_Weekly_Report_{timestamp}.xlsx`
- `AS_Weekly_Summary_{timestamp}.csv`
- `AS_Weekly_Entities_{timestamp}.csv`
- `AS_Weekly_Errors_{timestamp}.csv`
- `AS_Weekly_ServiceNow_Tickets_{timestamp}.csv`

## 4. 票務欄位（summary 合併後）
- `ticket_number`
- `ticket_opened_datetime`
- `ticket_state`
- `ticket_assigned_to`
- `ticket_owner` (compat alias)
- `ticket_status` (compat alias)
- `ticket_last_update_datetime`
- `ticket_last_update_days_ago`
- `ticket_last_note_source`
- `ticket_last_update_content`
- `ticket_is_closed`
- `ticket_match_key`
- `ticket_count_for_check`
- `open_ticket_count_for_check`

## 5. ServiceNow Mapping 規則
1. Query 先以 `short_description CONTAINS AdaptiveShield` 抓清單。
2. opened date 為時間窗基準。
3. `short description` 解析 key：
   - 優先 structured（`AdaptiveShield ... SaaS | Alias | Check`）
   - fallback 為 normalized contains（三段都命中才算 match）
4. 同 check-key 多票策略：
   - 主表/卡片取 latest ticket
   - 折疊區列出 all tickets

## 6. 錯誤處理
1. `SNOW_ENABLED=false`：直接回傳空 schema，不中斷 AS 流程。
2. Selenium 初始化失敗：記錄 `pipeline_errors`，SNOW 輸出為空。
3. 單票 detail 抓取失敗：該票 note 欄位留空，流程繼續。
4. 時間欄位不可解析：該票 skip 或 days_ago 留空並記錄錯誤。

## 7. UI 驗收（Enhanced）
1. 保留原 Cell 8 基礎 Drift UI。
2. Cell 10 提供 SNOW enhanced UI。
3. 卡片顯示：`SaaS | Alias | Check` + status badge + `SN: none/open/closed`。
4. open ticket 有 stale hint（`last update N d ago`）。
5. 票務明細折疊區顯示：number/opened/state/assigned/last update/days/note source/last note。
6. Timeline 與 status grouping 規則維持不變（failed first, passed folded, flip-flop badge）。
