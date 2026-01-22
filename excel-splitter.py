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
    except ImportError:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pywin32"])
            import win32com.client
            import pythoncom
            WIN32COM_AVAILABLE = True
        except:
            pass

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

def copy_selected_documents(source_dir, dest_dir, logger):
    for pattern in ["*.docx", "*.doc"]:
        for file in glob.glob(os.path.join(source_dir, pattern)):
            try:
                shutil.copy2(file, os.path.join(dest_dir, os.path.basename(file)))
                logger(f"  📎 Copied Word: {os.path.basename(file)}")
            except: pass

    for file in glob.glob(os.path.join(source_dir, "*.pdf")):
        try:
            shutil.copy2(file, os.path.join(dest_dir, os.path.basename(file)))
            logger(f"  📎 Copied PDF: {os.path.basename(file)}")
        except: pass

def copy_additional_files_list(file_paths: list, dest_dir: str, logger):
    if not file_paths: return
    for path in file_paths:
        if os.path.exists(path) and os.path.isfile(path):
            try:
                shutil.copy2(path, os.path.join(dest_dir, os.path.basename(path)))
                logger(f"  📎 Copied Extra: {os.path.basename(path)}")
            except Exception as e:
                logger(f"  ❌ Copy Error: {e}")

# ==========================================
# 2. Excel COM Logic (Improved)
# ==========================================

def initialize_excel_com(logger):
    global excel_com_instance
    if WIN32COM_AVAILABLE and excel_com_instance is None:
        try:
            pythoncom.CoInitialize()
            excel_com_instance = win32com.client.Dispatch("Excel.Application")
            excel_com_instance.Visible = False
            excel_com_instance.DisplayAlerts = False
            excel_com_instance.ScreenUpdating = False
            return True
        except Exception as e:
            logger(f"  ❌ COM Init Failed: {e}")
            return False
    return excel_com_instance is not None

def cleanup_excel_com():
    global excel_com_instance
    if excel_com_instance:
        try:
            excel_com_instance.Quit()
        except: pass
        excel_com_instance = None

def process_reviewer_com(file_path, reviewer, column_name, output_folder, logger):
    if not WIN32COM_AVAILABLE: return False, None
    global excel_com_instance
    if not initialize_excel_com(logger): return False, None
    
    wb_source = None
    wb_dest = None
    
    try:
        r_name = sanitize_folder_name(str(reviewer))
        r_folder = os.path.join(output_folder, r_name)
        os.makedirs(r_folder, exist_ok=True)
        
        base, ext = os.path.splitext(os.path.basename(file_path))
        dst_path = os.path.join(r_folder, f"{base} - {r_name}{ext}")
        
        abs_src = os.path.abspath(file_path)
        abs_dst = os.path.abspath(dst_path)
        
        # 1. 先做備份
        wb_source = excel_com_instance.Workbooks.Open(abs_src, ReadOnly=True)
        wb_source.SaveCopyAs(abs_dst)
        wb_source.Close(False)
        
        # 2. 開啟新檔進行刪減
        wb_dest = excel_com_instance.Workbooks.Open(abs_dst)
        ws = wb_dest.Worksheets(1)
        
        # 強制關閉原本可能存在的篩選
        if ws.AutoFilterMode:
            ws.AutoFilterMode = False

        # 3. 抓取正確的範圍 (UsedRange 最保險)
        last_row = ws.UsedRange.Rows.Count
        last_col = ws.UsedRange.Columns.Count
        
        if last_row < 2:
            logger(f"  ⚠️ 檔案無資料列，跳過。")
            wb_dest.Close(True)
            return True, r_folder

        # 4. 尋找標頭索引
        col_idx = 0
        for col in range(1, last_col + 1):
            if str(ws.Cells(1, col).Value).strip() == str(column_name).strip():
                col_idx = col
                break
                
        if col_idx == 0:
            logger(f"  ❌ 找不到欄位 '{column_name}'")
            wb_dest.Close(False)
            return False, None

        # 5. 【關鍵 fix】處理篩選條件與型態
        # 先抓第二列的第一筆資料來判斷這欄是數字還是字串
        sample_val = ws.Cells(2, col_idx).Value
        if isinstance(sample_val, (int, float)):
            try:
                # 確保數值比對是一致的
                criteria_str = f"<>{float(reviewer):.0f}" if float(reviewer).is_integer() else f"<>{float(reviewer)}"
            except:
                criteria_str = f"<>{reviewer}"
        else:
            criteria_str = f"<>{reviewer}"

        # 6. 【執行篩選】 範圍必須包含 Header (Row 1)
        data_range = ws.Range(ws.Cells(1, 1), ws.Cells(last_row, last_col))
        data_range.AutoFilter(Field=col_idx, Criteria1=criteria_str)

        # 7. 【精確刪除】 僅選取除了 Header 以外的資料列
        try:
            # 建立純資料範圍 (從 Row 2 開始)
            body_range = ws.Range(ws.Cells(2, 1), ws.Cells(last_row, last_col))
            
            # xlCellTypeVisible = 12
            # 只針對「顯示出來」(即不等於該審稿人) 的列進行刪除
            visible_cells = body_range.SpecialCells(12) 
            if visible_cells:
                visible_cells.EntireRow.Delete()
                logger(f"  ✨ 已刪除其他 Reviewer 資料")
        except Exception as e:
            # 如果報錯 1004 通常是因為篩選後沒有剩餘列 (代表全部都是該 Reviewer 的資料)
            if "1004" not in str(e):
                logger(f"  ⚠️ 刪除過程異常: {e}")

        # 8. 收尾
        ws.AutoFilterMode = False
        wb_dest.Save()
        wb_dest.Close()
        
        logger(f"  ✅ 處理完成: {os.path.basename(dst_path)}")
        return True, r_folder

    except Exception as e:
        logger(f"  ❌ 嚴重錯誤: {e}")
        try: 
            wb_dest.Close(False) 
        except: 
            pass
        return False, None
# ==========================================
# 3. GUI Application
# ==========================================

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Excel Reviewer Splitter (COM Only)")
        self.geometry("720x750")
        
        self.file_path_var = tk.StringVar()
        self.col_name_var = tk.StringVar(value="Reviewer")
        self.out_dir_var = tk.StringVar()
        self.extra_files = [] 
        
        if not WIN32COM_AVAILABLE:
            messagebox.showerror("Error", "Windows Excel Required.")
            self.destroy()
            return

        self.create_widgets()
        
    def create_widgets(self):
        pnl = ttk.LabelFrame(self, text="File Settings", padding=10)
        pnl.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(pnl, text="Excel File:").grid(row=0, column=0, sticky="w")
        ttk.Entry(pnl, textvariable=self.file_path_var, width=55).grid(row=0, column=1, padx=5)
        ttk.Button(pnl, text="Browse", command=self.browse_file).grid(row=0, column=2)
        
        ttk.Label(pnl, text="Column Name:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(pnl, textvariable=self.col_name_var, width=20).grid(row=1, column=1, sticky="w", padx=5)
        
        ttk.Label(pnl, text="Output Folder:").grid(row=2, column=0, sticky="w")
        ttk.Entry(pnl, textvariable=self.out_dir_var, width=55).grid(row=2, column=1, padx=5)
        ttk.Button(pnl, text="Browse", command=self.browse_folder).grid(row=2, column=2)

        pnl_files = ttk.LabelFrame(self, text="Attachments", padding=10)
        pnl_files.pack(fill="x", padx=10, pady=5)
        
        btn_box = ttk.Frame(pnl_files)
        btn_box.pack(anchor="w", pady=(0, 5))
        ttk.Button(btn_box, text="➕ Add Files...", command=self.add_extra_files).pack(side="left", padx=5)
        ttk.Button(btn_box, text="🗑️ Clear List", command=self.clear_extra_files).pack(side="left")
        
        list_frame = ttk.Frame(pnl_files)
        list_frame.pack(fill="x")
        self.lst_files = tk.Listbox(list_frame, height=5)
        self.lst_files.pack(side="left", fill="x", expand=True)
        
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        self.btn_run = ttk.Button(btn_frame, text="🚀 Start Processing", command=self.start_thread)
        self.btn_run.pack()

        self.lbl_progress = ttk.Label(self, text="Ready", font=("Arial", 9, "bold"))
        self.lbl_progress.pack(pady=5)
        self.progress = ttk.Progressbar(self, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", padx=10)

        self.log_area = scrolledtext.ScrolledText(self, height=10, state='disabled')
        self.log_area.pack(fill="both", expand=True, padx=10, pady=5)

    def browse_file(self):
        f = filedialog.askopenfilename()
        if f: 
            self.file_path_var.set(f)
            self.out_dir_var.set(os.path.dirname(f))

    def browse_folder(self):
        d = filedialog.askdirectory()
        if d: self.out_dir_var.set(d)

    def add_extra_files(self):
        files = filedialog.askopenfilenames()
        for f in files:
            if f not in self.extra_files:
                self.extra_files.append(f)
                self.lst_files.insert(tk.END, f)
    
    def clear_extra_files(self):
        self.extra_files = []
        self.lst_files.delete(0, tk.END)

    def log(self, msg, level="INFO"):
        ts = datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{ts}] {msg}"
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, full_msg + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')
        if self.log_file_handle:
            try: self.log_file_handle.write(full_msg + "\n"); self.log_file_handle.flush()
            except: pass

    def start_thread(self):
        self.btn_run.config(state="disabled")
        t = threading.Thread(target=self.run_process)
        t.start()

    def run_process(self):
        file_path = self.file_path_var.get()
        col_name = self.col_name_var.get()
        out_folder = self.out_dir_var.get()
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        log_dir = os.path.join(LOG_ROOT_DIR, today_str)
        try:
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, f"aer-share-{today_str}.log")
            self.log_file_handle = open(log_path, "a", encoding="utf-8")
        except: pass
        
        self.log("🚀 Starting Task (COM Mode)")
        
        try:
            if not os.path.exists(file_path): return
            
            # Read reviewers
            df = pd.read_excel(file_path)
            if col_name not in df.columns:
                self.log(f"❌ Column '{col_name}' not found.")
                return

            reviewers = df[col_name].dropna().unique().tolist()
            total = len(reviewers)
            
            self.progress["maximum"] = total
            self.progress["value"] = 0
            pythoncom.CoInitialize()

            for i, reviewer in enumerate(reviewers):
                self.lbl_progress.config(text=f"Processing: {reviewer} ({i+1}/{total})")
                self.log(f"Processing: {reviewer}")
                
                success, r_folder = process_reviewer_com(file_path, reviewer, col_name, out_folder, self.log)

                if success:
                    base_dir = os.path.dirname(file_path)
                    copy_selected_documents(base_dir, r_folder, self.log)
                    copy_additional_files_list(self.extra_files, r_folder, self.log)
                
                self.progress["value"] = i + 1
            
            self.lbl_progress.config(text="Done!")
            self.log("🎉 Completed!")
            messagebox.showinfo("Done", "Processing Complete!")

        except Exception as e:
            self.log(f"❌ Error: {e}")
            messagebox.showerror("Error", str(e))
        finally:
            if self.log_file_handle: self.log_file_handle.close()
            cleanup_excel_com()
            self.btn_run.config(state="normal")

if __name__ == "__main__":
    app = App()
    app.mainloop()