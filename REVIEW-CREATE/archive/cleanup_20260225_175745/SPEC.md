# AER 0211 規格 (SPEC)

Last Updated: 2026-02-12
Primary Artifact: `aer_create_0211.json`

## 1. 目標與範圍
- 以三階段流程產生可交付的 Access Review 檔案。
- Stage 1 下載與快取 AD 使用者。
- Stage 1.5 建立 Steven Bush 範圍內的部門主管樹與 reviewer mapping。
- Stage 2 做身分驗證與人工修正 UI。
- Stage 3 指派 reviewer 並輸出最終審查檔。

## 2. 非目標
- 不在此規格定義郵件寄送流程。
- 不處理跨租戶/多 root 組織樹推導。
- 不保證 service account 偵測 100% 精準（採 heuristic）。

## 3. 資料路徑與命名
- 輸入 AD cache 優先路徑: `input/ad_cache/ad_users_*.csv`
- 當日輸出 cache mirror: `output/{YYYY-MM-DD}/ad_cache/ad_users_*.csv`
- Stage 2 輸出: `output/{YYYY-MM-DD}/stage2_validated/*_validated_{YYYYMMDD}.xlsx`
- Stage 3 輸出: `output/{YYYY-MM-DD}/stage3_review/*_review_{YYYYMMDD_HHMM}.xlsx`

## 4. Stage 規格

### 4.1 Stage 1
- 勾選 `Use latest cache from input/ad_cache` 時:
  - 只讀 `input/ad_cache` 最新檔並跳過 Graph 下載。
- 正常下載完成後:
  - 同步寫入 `input/ad_cache` 與當日 `output/.../ad_cache`。
- 若可用，附帶 sign-in activity 欄位並輸出 3 個月活動狀態欄位。

### 4.2 Stage 1.5 (Org Tree)
- Root 優先鎖定 `Steven Bush`，找不到才 fallback。
- 只看 root 往下 L1-L3。
- service/shared/system 帳號從候選中排除。
- 部門主管 (dept head) 定義:
  - 使用 branch-boundary 規則：`user.department != manager.department` 才是候選。
  - 每部門從候選中選最上層節點（level 小者優先），再比 title rank、姓名。
  - 若無候選，fallback 為該部門範圍內最佳節點。
- UI 必須同時顯示:
  - Tree structure（可展開）
  - Head rows table（含候選數與選擇理由）
- 狀態列顯示 `IgnoredService` 與 `AmbiguousDept`。

### 4.3 Stage 2
- Email 命中 AD 時:
  - 一律採 AD name。
  - 一律視為 `VALID_PERFECT` (100% match)。
- 非 100% 記錄集中於 compact review table。
- Candidate 預設選取門檻: top score >= 90。
- 未選取仍輸出，狀態標記為 unresolved。
- 100% matches 預設 hidden（不展開明細列表）。
- 長時間處理顯示 progress bar。

### 4.4 Stage 3
- Reviewer 指派優先序:
  1) Email exact match（標記 Manual Review=Yes）
  2) Department match / contains
- 儲存前做最終排序與欄位重排:
  - 前三欄固定: `Validation Status`, `is_AD_active`, `Manual Review`
  - `Manual Review=Yes` 排最上
  - auto-matched + inactive AD 排最下
- 輸出 Excel:
  - 自動欄寬
  - wrap text
  - dropdown validation 保留

## 5. 介面契約 (Data Contract)
- Stage 2 依賴至少 `Email` 欄位，`User Name` 若存在會用於 fuzzy。
- Stage 3 依賴 `Email`, `Department`。
- Mapping 檔至少需要 `department`, `reviewer` 欄位；`email` 可選。

## 6. Threat Model (實務版)
- 風險 A: 錯誤 reviewer 指派導致存取審查錯派。
  - 緩解: 明確優先序、Manual Review 標記、可人工覆寫。
- 風險 B: stale cache 導致舊人員資料。
  - 緩解: input cache 明確來源、可強制 refresh、顯示使用檔名與時間。
- 風險 C: service/shared identity 汙染 org tree。
  - 緩解: Stage 1.5 heuristic 過濾 + 狀態揭露忽略數量。
- 風險 D: Notebook UI 導致人工判讀錯誤。
  - 緩解: compact table 行高/欄寬可讀性調整、tree 與 rows 同步顯示。

## 7. 驗收準則
- Stage 1 勾 cache 時可直接從 `input/ad_cache` 成功跑完後續 stages。
- Stage 1.5 不再只列 rows，必有 tree 視圖。
- Stage 2 email match 不會再落入 name mismatch 分類。
- Stage 3 輸出欄位與排序符合第 4.4 節。

## 8. 目前限制
- service account 過濾為 heuristic，需持續依租戶命名規則調整。
- 組織資料若 manager chain 缺漏嚴重，仍可能出現 fallback head。
