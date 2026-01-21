import sys
import os
import shutil
import time
import glob
import platform
import threading
import subprocess
from datetime import datetime

# GUI Imports
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# Logic Imports
try:
    import pandas as pd
    from openpyxl import load_workbook
except ImportError:
    print("Installing required packages...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas", "openpyxl"])
    import pandas as pd
    from openpyxl import load_workbook

# Windows COM Check
WIN32COM_AVAILABLE = False
if platform.system() == 'Windows':
    try:
        import win32com.client
        import pythoncom
        WIN32COM_AVAILABLE = True
    except ImportError:
        # User might need pywin32
        pass

# ==========================================
# 1. Global Variables & Helper Functions
# ==========================================

excel_com_instance = None
log_file_path = None

def sanitize_folder_name(name: str) -> str:
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '#', '%']
    sanitized = str(name).strip()
    for char in invalid_chars:
        sanitized = sanitized.replace(char, '_')
    return sanitized[:255].rstrip()

def find_column(worksheet, column_name):
    for col_idx, cell in enumerate(worksheet[1], start=1):
        if cell.value == column_name:
            return col_idx
    raise ValueError(f"Column '{column_name}' not found!")

def copy_selected_documents(source_dir, dest_dir, logger, copy_word=True, copy_pdf=True):
    if copy_word:
        for pattern in ["*.docx", "*.doc"]:
            for file in glob.glob(os.path.join(source_dir, pattern)):
                shutil.copy2(file, os.path.join(dest_dir, os.path.basename(file)))
                logger(f"  📎 Copied Word: {os.path.basename(file)}")

    if copy_pdf:
        for file in glob.glob(os.path.join(source_dir, "*.pdf")):
            shutil.copy2(file, os.path.join(dest_dir, os.path.basename(file)))
            logger(f"  📎 Copied PDF: {os.path.basename(file)}")

def copy_additional_files_list(file_paths_str: str, dest_dir: str, logger):
    if not file_paths_str: return
    paths = [p.strip() for p in file_paths_str.replace(',', '\n').split('\n') if p.strip()]
    
    for path in paths:
        clean_path = path.strip('"').strip("'")
        if os.path.exists(clean_path) and os.path.isfile(clean_path):
            try:
                shutil.copy2(clean_path, os.path.join(dest_dir, os.path.basename(clean_path)))
                logger(f"  📎 Copied Extra: {os.path.basename(clean_path)}")
            except Exception as e:
                logger(f"  ❌ Copy Error: {e}")
        else:
            logger(f"  ⚠️ File not found: {clean_path}")

# ==========================================
# 2. Excel Logic
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

def process_hide_rows(file_path, reviewer, column_name, output_folder, logger):
    try:
        r_name = sanitize_folder_name(str(reviewer))
        r_folder = os.path.join(output_folder, r_name)
        os.makedirs(r_folder, exist_ok=True)
        
        base, ext = os.path.splitext(os.path.basename(file_path))
        new_path = os.path.join(r_folder, f"{base} - {r_name}{ext}")
        
        shutil.copy2(file_path, new_path)
        
        wb = load_workbook(new_path, keep_vba=True)
        ws = wb.active
        col_idx = find_column(ws, column_name)
        
        rows_to_hide = [r for r in range(2, ws.max_row + 1) 
                        if str(ws.cell(r, col_idx).value).strip() != str(reviewer).strip()]
        
        for r in rows_to_hide:
            ws.row_dimensions[r].hidden = True
            
        wb.save(new_path)
        wb.close()
        logger(f"  ✅ Processed (OpenPyXL): {os.path.basename(new_path)}")
        return True, r_folder
    except Exception as e:
        logger(f"  ❌ Error: {e}")
        return False, None

def process_com(file_path, reviewer, column_name, output_folder, logger):
    if not WIN32COM_AVAILABLE: return False, None
    global excel_com_instance
    if not initialize_excel_com(logger): return False, None
    
    try:
        r_name = sanitize_folder_name(str(reviewer))
        r_folder = os.path.join(output_folder, r_name)
        os.makedirs(r_folder, exist_ok=True)
        
        base, ext = os.path.splitext(os.path.basename(file_path))
        dst_path = os.path.join(r_folder, f"{base} - {r_name}.xlsx")
        
        # Absolute paths required for COM
        abs_src = os.path.abspath(file_path)
        abs_dst = os.path.abspath(dst_path)
        
        wb_src = excel_com_instance.Workbooks.Open(abs_src, ReadOnly=True)
        wb_src.SaveCopyAs(abs_dst)
        wb_src.Close(False)
        
        wb_dest = excel_com_instance.Workbooks.Open(abs_dst)
        ws = wb_dest.Worksheets(1)
        
        col_idx = None
        for col in range(1, ws.UsedRange.Columns.Count + 1):
            if ws.Cells(1, col).Value == column_name:
                col_idx = col
                break
        
        if col_idx:
            if ws.AutoFilterMode: ws.AutoFilterMode = False
            ws.UsedRange.AutoFilter(Field=col_idx, Criteria1=f"<>{reviewer}")
            try:
                ws.UsedRange.Offset(1, 0).SpecialCells(12).EntireRow.Delete()
            except: pass
            ws.AutoFilterMode = False
            logger(f"  ✅ Processed (COM): {os.path.basename(dst_path)}")
        
        wb_dest.Save()
        wb_dest.Close()
        return True, r_folder
    except Exception as e:
        logger(f"  ❌ COM Error: {e}")
        return False, None

# ==========================================
# 3. GUI Application
# ==========================================

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Excel Reviewer Splitter Tool")
        self.geometry("700x750")
        
        # Variables
        self.file_path_var = tk.StringVar()
        self.col_name_var = tk.StringVar(value="Reviewer")
        self.out_dir_var = tk.StringVar(value=os.path.join(os.getcwd(), "output"))
        self.copy_word_var = tk.BooleanVar(value=True)
        self.copy_pdf_var = tk.BooleanVar(value=True)
        self.use_com_var = tk.BooleanVar(value=WIN32COM_AVAILABLE)
        
        self.create_widgets()
        
    def create_widgets(self):
        # File Selection Frame
        pnl = ttk.LabelFrame(self, text="File & Folder Settings", padding=10)
        pnl.pack(fill="x", padx=10, pady=5)
        
        # Input File
        ttk.Label(pnl, text="Excel File:").grid(row=0, column=0, sticky="w")
        ttk.Entry(pnl, textvariable=self.file_path_var, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(pnl, text="Browse", command=self.browse_file).grid(row=0, column=2)
        
        # Reviewer Column
        ttk.Label(pnl, text="Column Name:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(pnl, textvariable=self.col_name_var, width=20).grid(row=1, column=1, sticky="w", padx=5)
        
        # Output Folder
        ttk.Label(pnl, text="Output Folder:").grid(row=2, column=0, sticky="w")
        ttk.Entry(pnl, textvariable=self.out_dir_var, width=50).grid(row=2, column=1, padx=5)
        ttk.Button(pnl, text="Browse", command=self.browse_folder).grid(row=2, column=2)

        # Other Files Frame
        pnl_files = ttk.LabelFrame(self, text="Additional Files (One path per line)", padding=10)
        pnl_files.pack(fill="x", padx=10, pady=5)
        self.txt_extra_files = tk.Text(pnl_files, height=4, width=70)
        self.txt_extra_files.pack()

        # Settings Frame
        pnl_opt = ttk.LabelFrame(self, text="Processing Options", padding=10)
        pnl_opt.pack(fill="x", padx=10, pady=5)
        
        ttk.Checkbutton(pnl_opt, text="Copy Word Docs (.doc/x)", variable=self.copy_word_var).pack(anchor="w")
        ttk.Checkbutton(pnl_opt, text="Copy PDF Files (.pdf)", variable=self.copy_pdf_var).pack(anchor="w")
        
        com_state = "normal" if WIN32COM_AVAILABLE else "disabled"
        com_text = "Use Windows Excel COM (Best Format)" if WIN32COM_AVAILABLE else "Windows Excel COM Unavailable"
        ttk.Checkbutton(pnl_opt, text=com_text, variable=self.use_com_var, state=com_state).pack(anchor="w")

        # Buttons & Progress
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        
        self.btn_run = ttk.Button(btn_frame, text="🚀 Start Processing", command=self.start_thread)
        self.btn_run.pack(side="left", padx=5)
        
        self.progress = ttk.Progressbar(self, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", padx=10, pady=5)

        # Log Area
        ttk.Label(self, text="Execution Log:").pack(anchor="w", padx=10)
        self.log_area = scrolledtext.ScrolledText(self, height=12, state='disabled')
        self.log_area.pack(fill="both", expand=True, padx=10, pady=5)

    def browse_file(self):
        f = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx *.xlsm")])
        if f: self.file_path_var.set(f)

    def browse_folder(self):
        d = filedialog.askdirectory()
        if d: self.out_dir_var.set(d)

    def log(self, msg, level="INFO"):
        ts = datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{ts}] {msg}"
        
        # UI Update
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, full_msg + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')
        
        # File Write
        if self.log_file_handle:
            try:
                self.log_file_handle.write(full_msg + "\n")
                self.log_file_handle.flush()
            except: pass

    def start_thread(self):
        self.btn_run.config(state="disabled")
        t = threading.Thread(target=self.run_process)
        t.start()

    def run_process(self):
        file_path = self.file_path_var.get()
        col_name = self.col_name_var.get()
        out_folder = self.out_dir_var.get()
        extra_files = self.txt_extra_files.get("1.0", tk.END)

        # Create Log File
        today_str = datetime.now().strftime("%Y-%m-%d")
        log_dir = os.path.join(out_folder, "log", today_str)
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"aer-share-{today_str}.log")
        
        self.log_file_handle = open(log_path, "a", encoding="utf-8")
        
        self.log("🚀 Starting Task...")
        
        try:
            if not os.path.exists(file_path):
                self.log("❌ File not found!", "ERROR")
                return

            df = pd.read_excel(file_path, engine='openpyxl')
            if col_name not in df.columns:
                self.log(f"❌ Column '{col_name}' not found.", "ERROR")
                return

            reviewers = df[col_name].dropna().unique().tolist()
            self.log(f"🔎 Found {len(reviewers)} reviewers.")
            
            self.progress["maximum"] = len(reviewers)
            self.progress["value"] = 0

            # Need to initialize COM in this thread if needed
            if WIN32COM_AVAILABLE and self.use_com_var.get():
                pythoncom.CoInitialize()

            for i, reviewer in enumerate(reviewers):
                self.log(f"Processing: {reviewer}")
                success = False
                r_folder = None
                
                if self.use_com_var.get() and WIN32COM_AVAILABLE:
                    success, r_folder = process_com(file_path, reviewer, col_name, out_folder, self.log)
                else:
                    success, r_folder = process_hide_rows(file_path, reviewer, col_name, out_folder, self.log)

                if success and r_folder:
                    base_dir = os.path.dirname(file_path)
                    copy_selected_documents(base_dir, r_folder, self.log, 
                                          self.copy_word_var.get(), self.copy_pdf_var.get())
                    copy_additional_files_list(extra_files, r_folder, self.log)
                
                self.progress["value"] = i + 1
            
            self.log("🎉 All tasks completed!")
            messagebox.showinfo("Done", "Processing Complete!")

        except Exception as e:
            self.log(f"❌ Critical Error: {e}")
            messagebox.showerror("Error", str(e))
        finally:
            if self.log_file_handle:
                self.log_file_handle.close()
            cleanup_excel_com()
            self.btn_run.config(state="normal")

if __name__ == "__main__":
    app = App()
    app.mainloop()