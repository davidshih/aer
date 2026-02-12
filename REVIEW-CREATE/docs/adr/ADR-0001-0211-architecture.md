# ADR-0001: AER 0211 Workflow Architecture

- Status: Accepted
- Date: 2026-02-12
- Scope: `aer_create_0211.json` (Stage 1 / 1.5 / 2 / 3)

## Context
近期修正集中在三個問題:
1. 快取路徑分散，導致需要手動搬檔。
2. Stage 1.5 部門主管定義不精準，容易選錯節點。
3. Stage 2/3 人工審查可讀性與排序不穩定。

## Decision
### D1. input/ad_cache 作為跨 stage 的主要 cache source
- Stage 1 下載後同時寫 `input/ad_cache` 與 output mirror。
- Stage 1.5、Stage 2 讀取時優先 `input/ad_cache`。

### D2. Stage 1.5 採 branch-boundary 選 head
- dept head 候選條件: manager 的 department 與自己不同。
- service/shared/system identity 先排除。
- 同部門多候選時採 deterministic 規則選一個，並暴露 candidateCount。

### D3. Stage 2 Email-first policy
- Email 命中 AD 即為 100% 且強制使用 AD name。
- 不再因 name mismatch 進入人工審查。

### D4. Stage 3 輸出可讀性優先
- 存檔前排序與欄位重排固定。
- Excel 欄寬自適應 + wrap text。

## Tradeoffs
- Pro: 跨 stage 一致性提高、人工審查成本下降、輸出可讀性顯著提升。
- Con: service account 判定是 heuristic，可能有 false positive/negative。
- Con: branch-boundary 規則對 org 資料品質敏感，資料缺漏會走 fallback。

## Consequences
- Notebook 可獨立重跑，不再依賴手動複製 cache。
- Stage 1.5 結果更接近「跨 branch 第一主管」定義。
- Stage 2/3 更偏向審查效率而非保留所有原始雜訊。

## Follow-up
- 新增可配置的 service account 規則清單（外部 yaml/csv）。
- 為 Stage 1.5 增加選 head 的 debug 匯出（per-department rationale）。
