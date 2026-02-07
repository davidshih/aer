# AER 工作區檔案整理說明（繁中）

## 1. 目的
這份文件說明 `/Users/davidshih/projects/work/aer` 的檔案分類方式，
目標是降低 root 目錄雜訊、讓工具/文件/研究檔更容易找，
同時不破壞既有執行流程（尤其是 `REVIEW-CREATE`、`REVIEW-REPORT` 與 `output/`）。

## 2. 目前建議目錄結構
```text
/Users/davidshih/projects/work/aer
├── REVIEW-CREATE/            # Create 流程主專案
├── REVIEW-REPORT/            # Report 流程主專案
├── output/                   # 執行輸出（log、xlsx、中間產物）
├── docs/
│   └── guardium/             # Guardium 相關文件與清單
├── tools/
│   └── excel-splitter/       # Excel 拆分工具腳本
├── notebooks/
│   └── research/             # 研究/實驗 notebook 與對應 json
├── archive/
│   ├── report/               # 舊版 report 歷史檔案
│   └── notes/                # cell 草稿與對話快照
├── aer_bot.py                # 核心腳本（保留 root）
├── aer_cache.json            # 執行快取（保留 root）
├── aer_manual_notes.json     # 手動註記（保留 root）
├── requirements.txt          # 依賴設定（保留 root）
└── opencode.sh               # 常用啟動腳本（保留 root）
```

## 3. 分類原則
1. **主流程檔不拆散**：`REVIEW-CREATE/`、`REVIEW-REPORT/` 保持原樣。  
2. **可執行核心留 root**：會被流程直接讀取的腳本/快取/設定留在 root。  
3. **工具腳本集中**：獨立工具移到 `tools/`。  
4. **研究檔集中**：探索性 notebook 移到 `notebooks/research/`。  
5. **草稿與歷史集中**：零散文本與舊報表移到 `archive/`。

## 4. 本次已完成搬遷

### 4.1 Guardium 文件
- `Guardium_MSSQL_local_user_listing.txt` → `docs/guardium/`
- `guardium_SSO_checklist.md` → `docs/guardium/`

### 4.2 工具腳本
- `excel-splitter-gui-hide.py` → `tools/excel-splitter/`
- `excel-splitter-gui-remove.py` → `tools/excel-splitter/`

### 4.3 研究 notebook
- `m365_copilot_chat.ipynb` → `notebooks/research/`
- `synk_scan_all_branches.ipynb` → `notebooks/research/`
- `synk_scan_all_branches.json` → `notebooks/research/`

### 4.4 草稿與暫存內容
- `cell1.txt`、`cell2.txt`、`cell4.txt`、`cell5.txt`、`cell6.txt` → `archive/notes/`
- `chat.json` → `archive/notes/`

### 4.5 舊版報表檔
- `aer_report_01-28.json` → `archive/report/`

## 5. 保留在 root 的檔案（不要隨便移）
- `aer_bot.py`
- `aer_cache.json`
- `aer_manual_notes.json`
- `requirements.txt`
- `opencode.sh`

原因：這些檔案常被直接用相對路徑讀取；若移動會影響既有流程。

## 6. 後續維護規範
1. 新增工具：放 `tools/<tool-name>/`。  
2. 新增研究 notebook：放 `notebooks/research/`。  
3. 新增流程正式文件：優先放到對應專案（`REVIEW-CREATE/` 或 `REVIEW-REPORT/`），共用文件才放 `docs/`。  
4. 舊版輸出或一次性草稿：放 `archive/`，避免 root 再度堆積。

## 7. 建議下一步（可選）
1. 在 `.gitignore` 補上 macOS/編輯器暫存檔（例如 `.DS_Store`、`*.swp`）。
2. 在 root 再補一份英文版短 README，方便跨團隊協作。
3. 後續若要搬動 `aer_cache.json` / `aer_manual_notes.json`，先統一改成可配置路徑再做。
