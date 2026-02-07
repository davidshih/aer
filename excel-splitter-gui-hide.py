import sys
import os
import shutil
import glob
import platform
import threading
import subprocess
from datetime import datetime

# --- CONFIGURATION ---
LOG_ROOT_DIR = os.path.join(os.getcwd(), "logs") 

# GUI Imports
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# Logic Imports
try:
    import pandas as pd
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas", "openpyxl"])
    import pandas as pd

# Windows COM Import
WIN32COM_AVAILABLE = False
if platform.system() == 'Windows':
    try:
        import win32com.client
        import pythoncom
        WIN32COM_AVAILABLE = True
    except: pass

# ==========================================
# 1. Helper Functions
# ==========================================

excel_com_instance = None
log_file_handle = None

def sanitize_folder_name(name: str) -> str:
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '#', '%']
    sanitized = str(name).strip()
    for char in invalid_chars:
        sanitized = sanitized.replace(char, '_')
    return sanitized[:255].rstrip()

# ==========================================
# 2. Excel COM Logic (Hiding Mode)
# ==========================================

def initialize_excel_com(logger):
    global excel_com_instance
    if WIN32COM_AVAILABLE and excel_com_instance is None:
        try:
            pythoncom.CoInitialize()
            excel_com_instance = win32com.client.Dispatch("Excel.Application")
            excel_com_instance.Visible = False
            excel_com_instance.DisplayAlerts = False
            return True
        except Exception as e:
            logger(f"  ❌ COM 初始化失敗: {e}")
            return False
    return excel_com_instance is not None

def cleanup_excel_com():
    global excel_com_instance
    if excel_com_instance:
        try: excel_com_instance.Quit()
        except: pass
        excel_com_instance = None

def process_reviewer_hide_only(file_path, reviewer, column_name, output_folder, logger):
    """
    這個函數只會套用篩選器 (Filter)，讓非該 Reviewer 的資料隱藏，而不刪除任何資料。
    """
    if not WIN32COM_AVAILABLE: return False, None
    global excel_com_instance
    if not initialize_excel_com(logger): return False, None
    
    wb_dest = None
    try:
        r_name = sanitize_folder_name(str(reviewer))
        r_folder = os.path.join(output_folder, r_name)
        os.makedirs(r_folder, exist_ok=True)
        
        base, ext = os.path.splitext(os.path.basename(file_path))
        dst_path = os.path.join(r_folder, f"{base} - {r_name}{ext}")
        
        # 1. 複製檔案
        shutil.copy2(file_path, dst_path)
        
        # 2. 開啟副本
        abs_dst = os.path.abspath(dst_path)
        wb_dest = excel_com_instance.Workbooks.Open(abs_dst)
        ws = wb_dest.Worksheets(1)
        
        # 先清除舊的篩選
        if ws.AutoFilterMode:
            ws.AutoFilterMode = False

        # 3. 抓取範圍
        last_row = ws.UsedRange.Rows.Count
        last_col = ws.UsedRange.Columns.Count
        
        # 4. 找欄位索引
        col_idx = 0
        for col in range(1, last_col + 1):
            if str(ws.Cells(1, col).Value).strip() == str(column_name).strip():
                col_idx = col
                break
        
        if col_idx == 0:
            logger(f"  ❌ 找不到欄位: {column_name}")
            wb_dest.Close(False)
            return False, None

        # 5. 判斷型態 (處理數字 ID vs 字串姓名)
        sample_val = ws.Cells(2, col_idx).Value
        criteria = reviewer
        if isinstance(sample_val, (int, float)):
            try:
                # 轉成浮點數以符合 Excel 內部的數值存儲
                criteria = float(reviewer)
                if criteria.is_integer(): criteria = int(criteria)
            except: pass

        # 6. 【關鍵：套用篩選】
        # 這裡 Criteria1 直接等於 reviewer (不加 <>)
        # Excel 會自動把不符合的人隱藏起來
        data_range = ws.Range(ws.Cells(1, 1), ws.Cells(last_row, last_col))
        data_range.AutoFilter(Field=col_idx, Criteria1=criteria)

        # 7. 存檔並關閉 (注意：不關閉 AutoFilterMode，這樣開啟時才是篩選狀態)
        wb_dest.Save()
        wb_dest.Close()
        
        logger(f"  ✅ 已隱藏非 {reviewer} 之資料並存檔")
        return True, r_folder

    except Exception as e:
        logger(f"  ❌ 發生錯誤: {e}")
        if wb_dest: wb_dest.Close(False)
        return False, None

# ==========================================
# 3. GUI Application (簡化版)
# ==========================================

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Excel 隱藏版分檔工具 (PTT 版)")
        self.geometry("700 objetivos 650")
        
        self.file_path_var = tk.StringVar()
        self.col_name_var = tk.StringVar(value="Reviewer")
        self.out_dir_var = tk.StringVar()
        
        self.create_widgets()
        
    def create_widgets(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        ttk.Label(main_frame, text="1. 選擇 Excel 原始檔:", font=('Arial', 10, 'bold')).pack(anchor="w")
        f_frame = ttk.Frame(main_frame)
        f_frame.pack(fill="x", pady=5)
        ttk.Entry(f_frame, textvariable=self.file_path_var).pack(side="left", fill="x", expand=True)
        ttk.Button(f_frame, text="瀏覽", command=self.browse_file).pack(side="right")
        
        ttk.Label(main_frame, text="2. 審稿人欄位名稱:", font=('Arial', 10, 'bold')).pack(anchor="w", pady=(10, 0))
        ttk.Entry(main_frame, textvariable=self.col_name_var).pack(fill="x", pady=5)
        
        ttk.Label(main_frame, text="3. 輸出資料夾:", font=('Arial', 10, 'bold')).pack(anchor="w", pady=(10, 0))
        d_frame = ttk.Frame(main_frame)
        d_frame.pack(fill="x", pady=5)
        ttk.Entry(d_frame, textvariable=self.out_dir_var).pack(side="left", fill="x", expand=True)
        ttk.Button(d_frame, text="瀏覽", command=self.browse_folder).pack(side="right")

        self.btn_run = ttk.Button(main_frame, text="🚀 開始分發 (僅隱藏模式)", command=self.start_thread)
        self.btn_run.pack(pady=20, fill="x")

        self.log_area = scrolledtext.ScrolledText(main_frame, height=15, state='disabled', bg="#f0f0f0")
        self.log_area.pack(fill="both", expand=True)

    def browse_file(self):
        f = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xlsb *.xlsm *.xls")])
        if f: self.file_path_var.set(f)

    def browse_folder(self):
        d = filedialog.askdirectory()
        if d: self.out_dir_var.set(d)

    def log(self, msg):
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')

    def start_thread(self):
        self.btn_run.config(state="disabled")
        threading.Thread(target=self.run_process, daemon=True).start()

    def run_process(self):
        f_path = self.file_path_var.get()
        col = self.col_name_var.get()
        out = self.out_dir_var.get()
        
        if not f_path or not out:
            messagebox.showwarning("警告", "請填好路徑！")
            self.btn_run.config(state="normal")
            return

        try:
            self.log("讀取審稿清單中...")
            df = pd.read_excel(f_path)
            reviewers = df[col].dropna().unique().tolist()
            
            pythoncom.CoInitialize()
            for r in reviewers:
                self.log(f"正在處理: {r}...")
                process_reviewer_hide_only(f_path, r, col, out, self.log)
                
            self.log("🎉 全部處理完成！")
            messagebox.showinfo("完成", "檔案已產出，非該人資料已隱藏。")
        except Exception as e:
            self.log(f"❌ 錯誤: {e}")
        finally:
            cleanup_excel_com()
            self.btn_run.config(state="normal")

if __name__ == "__main__":
    app = App()
    app.mainloop()