# === CELL 4: Stage 4 — Reviewer Splitter (Windows COM) ===
# Splits review Excel into per-reviewer files using Windows COM AutoFilter.
# Preserves original Win COM logic.

# ============================================
# EXCEL COM HELPERS (WINDOWS ONLY)
# ============================================

_excel_app = None

def _init_excel_com():
    global _excel_app
    if not WIN32COM_AVAILABLE:
        return None
    try:
        pythoncom.CoInitialize()
        _excel_app = win32com.client.Dispatch("Excel.Application")
        _excel_app.Visible = False
        _excel_app.DisplayAlerts = False
        return _excel_app
    except Exception as e:
        logger(f"Excel COM init failed: {e}", "error")
        return None

def _cleanup_excel_com():
    global _excel_app
    if _excel_app:
        try:
            _excel_app.Quit()
        except Exception:
            pass
        _excel_app = None
    try:
        pythoncom.CoUninitialize()
    except Exception:
        pass


def _process_reviewer_hide_only(main_file, reviewer, column_name, output_root, log_fn):
    """Copy main file, apply AutoFilter to show only this reviewer's rows."""
    wb_dest = None
    try:
        r_folder_name = sanitize_folder_name(reviewer)
        r_folder = os.path.join(output_root, r_folder_name)
        os.makedirs(r_folder, exist_ok=True)

        dest_file = os.path.join(r_folder, os.path.basename(main_file))
        shutil.copy2(main_file, dest_file)

        excel = _excel_app
        if not excel:
            excel = _init_excel_com()
        if not excel:
            return False, None

        abs_path = os.path.abspath(dest_file)
        wb_dest = excel.Workbooks.Open(abs_path)
        ws = wb_dest.Sheets(1)

        last_row = ws.UsedRange.Rows.Count
        last_col = ws.UsedRange.Columns.Count

        # Find column index
        col_idx = 0
        for c in range(1, last_col + 1):
            if str(ws.Cells(1, c).Value or "").strip().lower() == column_name.strip().lower():
                col_idx = c
                break

        if col_idx == 0:
            log_fn(f"  [ERROR] Column not found: {column_name}")
            wb_dest.Close(False)
            return False, None

        # Handle numeric or text criteria
        sample_val = ws.Cells(2, col_idx).Value
        criteria = reviewer
        if isinstance(sample_val, (int, float)):
            try:
                criteria = float(reviewer)
                if criteria.is_integer():
                    criteria = int(criteria)
            except Exception:
                pass

        # Apply filter
        data_range = ws.Range(ws.Cells(1, 1), ws.Cells(last_row, last_col))
        data_range.AutoFilter(Field=col_idx, Criteria1=criteria)

        wb_dest.Save()
        wb_dest.Close()

        log_fn(f"  [OK] Filtered workbook saved for reviewer: {reviewer}")
        return True, r_folder

    except Exception as e:
        log_fn(f"  [ERROR] Split failed: {e}")
        if wb_dest:
            wb_dest.Close(False)
        return False, None


# ============================================
# STATE & UI
# ============================================

s4_support_files = []
s4_status = widgets.HTML(value="<i>Ready. Select main xlsx or use default Stage 3 output.</i>")
s4_output = widgets.Output()

s4_input_path = widgets.Text(value="", description="Input XLSX", placeholder="Stage 3 review workbook path",
                              layout=widgets.Layout(width="80%"))
s4_reviewer_col = widgets.Text(value="Reviewer", description="Reviewer Col",
                                layout=widgets.Layout(width="50%"))
s4_btn_browse = widgets.Button(description="Browse Main XLSX", button_style="info",
                                layout=widgets.Layout(width="180px"))
s4_btn_support = widgets.Button(description="Pick Support Files", button_style="info",
                                 layout=widgets.Layout(width="180px"))
s4_btn_run = widgets.Button(description="Run Stage 4 Split", button_style="success",
                             layout=widgets.Layout(width="220px", height="40px"))
s4_support_status = widgets.HTML(value="<i>No support files selected</i>")


def _get_latest_stage3_output():
    patterns = [os.path.join(STAGE3_DIR, "*review*.xlsx"), os.path.join(STAGE3_DIR, "*.xlsx")]
    files = []
    for p in patterns:
        files.extend(glob.glob(p))
    files = [f for f in files if os.path.isfile(f)]
    return max(files, key=os.path.getmtime) if files else None


def _refresh_s4_default():
    if s4_input_path.value.strip() and os.path.isfile(s4_input_path.value.strip()):
        return
    latest = _get_latest_stage3_output()
    if latest:
        s4_input_path.value = latest
        s4_status.value = f"<span style='color:green'>✅ Default: {os.path.basename(latest)}</span>"


def on_s4_browse(_):
    if not TK_AVAILABLE:
        s4_status.value = "<span style='color:orange'>⚠️ Tkinter not available for file dialog</span>"
        return
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        selected = filedialog.askopenfilename(
            title="Select Stage 3 review workbook",
            initialdir=STAGE3_DIR if os.path.isdir(STAGE3_DIR) else None,
            filetypes=[("Excel files", "*.xlsx")]
        )
        if selected:
            s4_input_path.value = selected
    finally:
        root.destroy()

s4_btn_browse.on_click(on_s4_browse)


def on_s4_support(_):
    global s4_support_files
    if not TK_AVAILABLE:
        return
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        selected = filedialog.askopenfilenames(title="Select support files", filetypes=[("All files", "*.*")])
        s4_support_files = list(selected)
        if s4_support_files:
            s4_support_status.value = f"<span style='color:green'>✅ {len(s4_support_files)} files selected</span>"
    finally:
        root.destroy()

s4_btn_support.on_click(on_s4_support)


def s4_log(msg):
    with s4_output:
        now = datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] {msg}")


def on_s4_run(_):
    s4_output.clear_output()
    s4_btn_run.disabled = True
    try:
        if platform.system() != "Windows":
            s4_status.value = "<span style='color:red'>❌ Stage 4 requires Windows + Excel COM</span>"
            return
        if not WIN32COM_AVAILABLE:
            s4_status.value = "<span style='color:red'>❌ pywin32 not available</span>"
            return

        main_file = s4_input_path.value.strip()
        if not main_file or not os.path.isfile(main_file):
            s4_status.value = "<span style='color:red'>❌ Main xlsx file required</span>"
            return

        reviewer_col = s4_reviewer_col.value.strip() or "Reviewer"
        df = pd.read_excel(main_file)

        # Load AD for preflight
        ad_df, _, ad_err = load_ad_cache()
        if ad_df is None:
            s4_status.value = f"<span style='color:red'>❌ {ad_err}</span>"
            return
        ad_email_set, ad_name_map = build_identity_index(ad_df)

        # Preflight: validate all reviewers
        if reviewer_col not in df.columns:
            s4_status.value = f"<span style='color:red'>❌ Column '{reviewer_col}' not found</span>"
            return

        unique_reviewers = df[reviewer_col].dropna().unique()
        errors = []
        resolved = []
        for val in unique_reviewers:
            ok, email, err = resolve_identity(val, ad_email_set, ad_name_map)
            if ok:
                resolved.append({"raw": val, "email": email})
            else:
                errors.append({"raw": val, "error": err})

        if errors:
            s4_status.value = "<span style='color:red'>❌ Preflight failed</span>"
            s4_log(f"Preflight errors: {len(errors)}")
            for e in errors[:50]:
                s4_log(f"  '{e['raw']}' -> {e['error']}")
            return

        # Derive output root
        base_name = re.split(r'(?i)(?:[_\-\s]*user.*)$', os.path.splitext(os.path.basename(main_file))[0], maxsplit=1)[0].strip(" _-")
        app_name = sanitize_folder_name(base_name or "review")
        output_root = os.path.join(STAGE4_DIR, app_name)

        s4_log(f"Starting split for {len(resolved)} reviewers")
        _init_excel_com()

        success = 0
        for item in resolved:
            s4_log(f"Processing: {item['raw']}")
            ok, folder = _process_reviewer_hide_only(main_file, item["raw"], reviewer_col, output_root, s4_log)
            if ok and folder:
                for sf in s4_support_files:
                    if os.path.abspath(sf) != os.path.abspath(main_file):
                        try:
                            shutil.copy2(sf, os.path.join(folder, os.path.basename(sf)))
                        except Exception as e:
                            s4_log(f"  Support copy failed: {e}")
                success += 1

        _cleanup_excel_com()
        s4_log(f"Done: {success}/{len(resolved)} reviewers")
        s4_status.value = f"<span style='color:green'>✅ Split complete: {success}/{len(resolved)}</span>"
        globals()["s4_last_output_root"] = output_root
        logger(f"Stage 4: {success}/{len(resolved)} reviewers split")
    except Exception as e:
        s4_status.value = f"<span style='color:red'>❌ {e}</span>"
        _cleanup_excel_com()
    finally:
        s4_btn_run.disabled = False

s4_btn_run.on_click(on_s4_run)

_refresh_s4_default()

stage4_ui = widgets.VBox([
    widgets.HTML("""
        <div style='background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            padding: 20px; border-radius: 8px; color: white; margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
            <h2 style='margin: 0 0 10px 0;'>📦 Stage 4: Reviewer Splitter</h2>
            <p style='margin: 0; opacity: 0.95;'>
                Validate reviewers against AD, then create one filtered workbook per reviewer (Windows COM).
            </p>
        </div>
    """),
    widgets.HBox([s4_input_path, s4_btn_browse]),
    widgets.HBox([s4_btn_support, s4_support_status]),
    s4_reviewer_col,
    s4_btn_run,
    s4_status,
    s4_output,
])

clear_output()
display(stage4_ui)
