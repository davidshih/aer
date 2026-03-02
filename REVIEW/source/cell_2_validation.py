# === CELL 2: Stage 2 — Email/User Validation & AD Status Check ===
# Validates uploaded user list against AD cache with fuzzy matching and cross-period diff.

from enum import Enum

class ValidationStatus(Enum):
    VALID_PERFECT = "G0_PERFECT"
    VALID_FUZZY_HIGH = "G1_FUZZY_HIGH"
    WARN_FUZZY_LOW = "G2_FUZZY_LOW"
    WARN_NAME_MISMATCH = "G3_NAME_MISMATCH"
    ERR_NOT_FOUND = "G4_NOT_FOUND"
    ERR_MISSING_INPUT = "G5_MISSING_INPUT"
    ERR_FUZZY_MULTIPLE = "G6_FUZZY_MULTIPLE"

# ============================================
# STATE
# ============================================
s2_input_df = None
s2_ad_df = None
s2_ad_email_set = set()
s2_ad_name_map = {}
s2_results = []
s2_output = widgets.Output()
s2_status = widgets.HTML(value="<i>Ready. Upload a user list file.</i>")

s2_upload = widgets.FileUpload(accept=".csv,.xlsx,.xls", multiple=False, description="Upload File")
s2_btn_validate = widgets.Button(description="🔍 Validate", button_style="success",
                                  layout=widgets.Layout(width="150px", height="40px"), disabled=True)
s2_btn_save = widgets.Button(description="💾 Save Results", button_style="info",
                              layout=widgets.Layout(width="150px", height="40px"), disabled=True)

# ============================================
# HANDLERS
# ============================================

def on_s2_upload_change(change):
    global s2_input_df, s2_ad_df, s2_ad_email_set, s2_ad_name_map
    if not s2_upload.value:
        return
    s2_output.clear_output()
    try:
        uploaded = list(s2_upload.value.values())[0] if isinstance(s2_upload.value, dict) else s2_upload.value[0]
        content = uploaded["content"] if isinstance(uploaded, dict) else uploaded.content
        fname = uploaded["name"] if isinstance(uploaded, dict) else uploaded.name

        if fname.lower().endswith(".csv"):
            # Try encoding detection
            encoding = "utf-8"
            if CHARDET_AVAILABLE:
                det = chardet.detect(content)
                encoding = det.get("encoding", "utf-8") or "utf-8"
            s2_input_df = pd.read_csv(io.BytesIO(content), encoding=encoding)
        else:
            s2_input_df = pd.read_excel(io.BytesIO(content))

        # Load AD cache
        s2_ad_df, ad_path, ad_err = load_ad_cache()
        if s2_ad_df is None:
            s2_status.value = f"<span style='color:red'>❌ {ad_err}</span>"
            return
        s2_ad_email_set, s2_ad_name_map = build_identity_index(s2_ad_df)

        s2_status.value = (
            f"<span style='color:green'>✅ Loaded: {fname} ({len(s2_input_df)} rows) | "
            f"AD cache: {os.path.basename(ad_path)} ({len(s2_ad_email_set)} emails)</span>"
        )
        s2_btn_validate.disabled = False
        logger(f"Stage 2: Uploaded {fname} ({len(s2_input_df)} rows)")
    except Exception as e:
        s2_status.value = f"<span style='color:red'>❌ Upload error: {e}</span>"

s2_upload.observe(on_s2_upload_change, names="value")


def _detect_email_col(df):
    for col in df.columns:
        cl = str(col).strip().lower()
        if "email" in cl or cl == "mail":
            return col
    return None

def _detect_name_col(df):
    for col in df.columns:
        cl = str(col).strip().lower()
        if "reviewer" in cl or "manager" in cl:
            continue
        if "name" in cl or ("display" in cl and "user" in cl):
            return col
    return None


def on_s2_validate(_):
    global s2_results
    s2_output.clear_output()
    s2_btn_validate.disabled = True

    try:
        if s2_input_df is None:
            s2_status.value = "<span style='color:red'>❌ No file uploaded</span>"
            return

        email_col = _detect_email_col(s2_input_df)
        name_col = _detect_name_col(s2_input_df)

        if not email_col:
            s2_status.value = "<span style='color:red'>❌ No email column found in uploaded file</span>"
            return

        # Cross-period diff
        prev_cache = find_previous_ad_cache()
        ad_df_for_diff = s2_ad_df if s2_ad_df is not None else pd.DataFrame()

        s2_results = []
        counters = {s.value: 0 for s in ValidationStatus}

        for idx, row in s2_input_df.iterrows():
            raw_email = str(row.get(email_col, "")).strip().lower()
            raw_name = str(row.get(name_col, "")).strip() if name_col else ""

            result = {"idx": idx, "raw_email": raw_email, "raw_name": raw_name, "row_data": row.to_dict()}

            if not raw_email or raw_email == "nan":
                if not raw_name or raw_name == "nan":
                    result["status"] = ValidationStatus.ERR_MISSING_INPUT
                    result["message"] = "No email or name provided"
                else:
                    # Try fuzzy match by name
                    matches = fuzzy_match_name(raw_name, s2_ad_name_map, AER_FUZZY_THRESHOLD)
                    if not matches:
                        result["status"] = ValidationStatus.ERR_NOT_FOUND
                        result["message"] = "Name not found in AD (no email provided)"
                    elif len(matches) == 1 and len(matches[0][2]) == 1:
                        result["status"] = ValidationStatus.VALID_FUZZY_HIGH if matches[0][1] >= 90 else ValidationStatus.WARN_FUZZY_LOW
                        result["matched_email"] = matches[0][2][0]
                        result["matched_name"] = matches[0][0]
                        result["score"] = matches[0][1]
                        result["message"] = f"Fuzzy matched ({matches[0][1]}%)"
                    else:
                        result["status"] = ValidationStatus.ERR_FUZZY_MULTIPLE
                        result["message"] = f"Multiple fuzzy matches ({len(matches)})"
                        result["candidates"] = matches[:5]
            else:
                # Correct known domain typos
                corrected_email, was_corrected = correct_email_domain(raw_email)
                if was_corrected:
                    raw_email = corrected_email
                    result["raw_email"] = corrected_email
                    result["domain_corrected"] = True

                if raw_email in s2_ad_email_set:
                    # Email found in AD
                    ad_row = s2_ad_df[s2_ad_df["email"].str.strip().str.lower() == raw_email].iloc[0]
                    ad_name = str(ad_row.get("displayName", "")).strip()
                    if raw_name and normalize_person_name(raw_name) != normalize_person_name(ad_name):
                        result["status"] = ValidationStatus.WARN_NAME_MISMATCH
                        result["message"] = f"Email match but name differs: '{raw_name}' vs '{ad_name}'"
                        result["ad_name"] = ad_name
                    else:
                        result["status"] = ValidationStatus.VALID_PERFECT
                        result["message"] = "Perfect match"
                    result["matched_email"] = raw_email
                    result["department"] = str(ad_row.get("department", "")).strip()
                    result["is_active"] = ad_row.get("accountEnabled", True)
                else:
                    # Email not in AD, try fuzzy name
                    if raw_name:
                        matches = fuzzy_match_name(raw_name, s2_ad_name_map, AER_FUZZY_THRESHOLD)
                        if matches and len(matches[0][2]) == 1:
                            result["status"] = ValidationStatus.VALID_FUZZY_HIGH if matches[0][1] >= 90 else ValidationStatus.WARN_FUZZY_LOW
                            result["matched_email"] = matches[0][2][0]
                            result["score"] = matches[0][1]
                            result["message"] = f"Email not found, fuzzy name match ({matches[0][1]}%)"
                        else:
                            result["status"] = ValidationStatus.ERR_NOT_FOUND
                            result["message"] = "Email not in AD, no fuzzy match"
                    else:
                        result["status"] = ValidationStatus.ERR_NOT_FOUND
                        result["message"] = "Email not in AD"

            counters[result["status"].value] += 1
            s2_results.append(result)

        # Summary
        with s2_output:
            total = len(s2_results)
            print(f"Validation complete: {total} records")
            print(f"  ✅ Perfect: {counters['G0_PERFECT']}")
            print(f"  ✅ Fuzzy High: {counters['G1_FUZZY_HIGH']}")
            print(f"  ⚠️  Fuzzy Low: {counters['G2_FUZZY_LOW']}")
            print(f"  ⚠️  Name Mismatch: {counters['G3_NAME_MISMATCH']}")
            print(f"  ❌ Not Found: {counters['G4_NOT_FOUND']}")
            print(f"  ❌ Missing Input: {counters['G5_MISSING_INPUT']}")
            print(f"  ❌ Multiple Matches: {counters['G6_FUZZY_MULTIPLE']}")

        s2_status.value = (
            f"<span style='color:green'>✅ Validated {total} records | "
            f"OK: {counters['G0_PERFECT']+counters['G1_FUZZY_HIGH']} | "
            f"Warn: {counters['G2_FUZZY_LOW']+counters['G3_NAME_MISMATCH']} | "
            f"Err: {counters['G4_NOT_FOUND']+counters['G5_MISSING_INPUT']+counters['G6_FUZZY_MULTIPLE']}</span>"
        )
        s2_btn_save.disabled = False
        logger(f"Stage 2: {total} records validated")
    except Exception as e:
        s2_status.value = f"<span style='color:red'>❌ Validation error: {e}</span>"
        logger(f"Stage 2 error: {e}", "error")
    finally:
        s2_btn_validate.disabled = False

s2_btn_validate.on_click(on_s2_validate)


def on_s2_save(_):
    if not s2_results:
        return
    try:
        rows = []
        prev_cache = find_previous_ad_cache()
        for r in s2_results:
            row = dict(r.get("row_data", {}))
            row["Validation_Status"] = r["status"].value
            row["Validation_Message"] = r.get("message", "")
            row["Matched_Email"] = r.get("matched_email", "")
            row["Department"] = r.get("department", "")
            row["is_AD_active"] = r.get("is_active", "")
            # Cross-period diff
            matched_email = r.get("matched_email", "")
            if matched_email and prev_cache and s2_ad_df is not None:
                matched_rows = s2_ad_df[s2_ad_df["email"].str.strip().str.lower() == matched_email]
                if not matched_rows.empty:
                    diff_series = compute_diff(matched_rows.head(1), prev_cache)
                    row["Change_Since_Last"] = diff_series.iloc[0] if len(diff_series) > 0 else ""
            rows.append(row)

        out_df = pd.DataFrame(rows)
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        fname = f"validated_{ts}.xlsx"
        path = safe_excel_path(os.path.join(STAGE2_DIR, fname))
        out_df.to_excel(path, index=False)
        if OPENPYXL_AVAILABLE:
            format_export_excel(path)
        s2_status.value = f"<span style='color:green'>✅ Saved: {os.path.basename(path)}</span>"
        logger(f"Stage 2 output saved: {path}")
    except Exception as e:
        s2_status.value = f"<span style='color:red'>❌ Save error: {e}</span>"

s2_btn_save.on_click(on_s2_save)


# ============================================
# UI
# ============================================

stage2_ui = widgets.VBox([
    widgets.HTML("""
        <div style='background: linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%);
            padding: 20px; border-radius: 8px; color: white; margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
            <h2 style='margin: 0 0 10px 0;'>🔍 Stage 2: Email/User Validation</h2>
            <p style='margin: 0; opacity: 0.95;'>
                Validate uploaded user list against AD cache. Supports encoding detection,
                fuzzy matching, and cross-period change tracking.
            </p>
        </div>
    """),
    s2_upload,
    widgets.HBox([s2_btn_validate, s2_btn_save]),
    s2_status,
    s2_output,
])

clear_output()
display(stage2_ui)
