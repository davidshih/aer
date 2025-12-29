#!/usr/bin/env python3
"""
診斷 access_review.ipynb 第7個cell UI不顯示的問題
"""

print("=== 診斷 access_review.ipynb UI 問題 ===")
print()

# 檢查可能的問題原因和解決方案
print("🔍 可能的問題原因:")
print("1. 第4個cell（資料收集）可能執行失敗")
print("2. df 變數為空（len(df) == 0）")
print("3. SharePoint 連線問題")
print("4. Excel 檔案讀取失敗")
print("5. 沒有找到審核人資料夾")
print()

print("🛠 建議的調試步驟:")
print()

print("步驟1：檢查變數狀態")
print("在新的 cell 中執行以下代碼：")
print("""
# 檢查關鍵變數是否存在
try:
    print(f"df 變數存在: {type(df)}")
    print(f"df 長度: {len(df)}")
    print(f"df 欄位: {list(df.columns) if len(df) > 0 else '無資料'}")
    print(f"all_responses 長度: {len(all_responses) if 'all_responses' in locals() else '變數不存在'}")
    print(f"errors 數量: {len(errors) if 'errors' in locals() else '變數不存在'}")
except NameError as e:
    print(f"❌ 變數不存在: {e}")
""")

print()
print("步驟2：檢查 SharePoint 連線")
print("在新的 cell 中執行：")
print("""
# 檢查 SharePoint 連線和資料夾
try:
    print(f"Site ID: {site_id[:20]}...")
    print(f"BASE_PATH: {BASE_PATH}")
    folders = list_folders(site_id, BASE_PATH)
    print(f"找到 {len(folders)} 個資料夾:")
    for f in folders[:5]:  # 只顯示前5個
        print(f"  - {f['name']}")
    if len(folders) > 5:
        print(f"  ... 還有 {len(folders)-5} 個資料夾")
except Exception as e:
    print(f"❌ SharePoint 連線失敗: {e}")
""")

print()
print("步驟3：重新執行資料收集（簡化版）")
print("""
# 簡化版資料收集，含更多除錯資訊
import pandas as pd

all_responses_debug = []
errors_debug = []

try:
    folders = list_folders(site_id, BASE_PATH)
    print(f"開始處理 {len(folders)} 個資料夾...")
    
    for i, folder in enumerate(folders[:2]):  # 先只處理前2個
        reviewer_name = folder["name"]
        print(f"\\n[{i+1}] 處理: {reviewer_name}")
        
        try:
            folder_path = f"{BASE_PATH}/{reviewer_name}"
            excel_files = list_excel_files(site_id, folder_path)
            print(f"  找到 {len(excel_files)} 個 Excel 檔案")
            
            if excel_files:
                print(f"  檔案: {excel_files[0]['name']}")
                # 這裡可以繼續處理...
                
        except Exception as e:
            print(f"  ❌ 錯誤: {e}")
            errors_debug.append({"reviewer": reviewer_name, "error": str(e)})
    
    print(f"\\n調試完成，錯誤數: {len(errors_debug)}")
    
except Exception as e:
    print(f"❌ 整體失敗: {e}")
""")

print()
print("步驟4：強制顯示第7個cell的UI")
print("如果 df 為空，可以創建測試資料：")
print("""
# 創建測試資料以顯示UI
import pandas as pd
from IPython.display import display, HTML

if 'df' not in locals() or len(df) == 0:
    print("創建測試資料...")
    test_data = [
        {
            "reviewer": "Test User 1",
            "response": "Approved", 
            "details": "Test details",
            "is_missing": False,
            "Audit_History": "2025-12-29 10:00:00 - Admin (v1.0)",
            "Last_Modified": "2025-12-29T10:00:00Z",
            "row_number": 2,
            "file_name": "test.xlsx",
            "folder_url": "#"
        },
        {
            "reviewer": "Test User 2", 
            "response": "",
            "details": "",
            "is_missing": True,
            "Audit_History": "2025-12-29 11:00:00 - Admin (v1.0)",
            "Last_Modified": "2025-12-29T11:00:00Z", 
            "row_number": 3,
            "file_name": "test2.xlsx",
            "folder_url": "#"
        }
    ]
    
    df = pd.DataFrame(test_data)
    print(f"測試資料已創建，包含 {len(df)} 筆記錄")
    
    # 現在重新執行第7個cell
    display(HTML("<p style='color: blue;'>⚠️ 使用測試資料顯示UI</p>"))
""")

print()
print("步驟5：檢查第6個cell的UI問題")
print("第6個cell也可能有類似問題，檢查：")
print("""
# 檢查第6個cell的 ipywidgets
try:
    import ipywidgets as widgets
    from IPython.display import display, clear_output
    
    print("✅ ipywidgets 正常")
    
    # 測試簡單的widget
    test_button = widgets.Button(description="測試按鈕")
    display(test_button)
    print("如果看到按鈕，則widget正常")
    
except ImportError:
    print("❌ 需要安裝 ipywidgets:")
    print("!pip install ipywidgets")
    
except Exception as e:
    print(f"❌ Widget 錯誤: {e}")
""")

print()
print("=== 常見解決方案 ===")
solutions = [
    "重新按順序執行所有 cell（特別是 1-4）",
    "檢查 .env 檔案的 Azure 憑證設定",
    "確認 SharePoint 路徑 BASE_PATH 正確",
    "檢查是否有網路連線問題",
    "確認審核人資料夾確實存在且包含 Excel 檔案",
    "重新啟動 Jupyter kernel",
    "安裝缺少的套件: pip install ipywidgets openpyxl pandas"
]

for i, solution in enumerate(solutions, 1):
    print(f"{i}. {solution}")

print()
print("💡 如果問題持續存在，請逐步執行上述診斷代碼，並分享錯誤訊息！")
