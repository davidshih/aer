# === CELL 6: Stage 6 — Report Scanner & Dashboard ===
# Browse SP app folders, scan reviewer excels, build dashboard, export reports.
# Year from config (not hardcoded). Atomic cache writes.

# ============================================
# CONFIG
# ============================================

REPORT_CACHE_FILE = os.path.join(CACHE_DIR, "aer_cache.json")
REPORT_NOTES_FILE = os.path.join(CACHE_DIR, "aer_manual_notes.json")
CACHE_VERSION = 5.0
cache_updated_flag = False
EXCLUDED_FOLDERS = ["forms", "_private", "user listings", "audit logs", "audit"]

# ============================================
# HELPERS
# ============================================

def _r6_get_site_id():
    headers = token_mgr.get_headers("graph")
    spo_host = normalize_sp_host(SHAREPOINT_HOST)
    url = f"https://graph.microsoft.com/v1.0/sites/{spo_host}:/sites/{SITE_NAME}"
    resp = graph_get(url, headers)
    resp.raise_for_status()
    return resp.json()["id"]

def _r6_list_folders(site_id, path):
    headers = token_mgr.get_headers("graph")
    if not path or path.strip() == "":
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root/children"
    else:
        clean = path.strip("/")
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root:/{clean}:/children"
    resp = graph_get(url, headers)
    results = []
    for item in resp.json().get("value", []):
        if item.get("folder"):
            name_lower = item["name"].lower()
            if any(ex in name_lower for ex in EXCLUDED_FOLDERS):
                continue
            results.append({
                "name": item["name"],
                "webUrl": item.get("webUrl", ""),
                "count": item.get("folder", {}).get("childCount", 0),
            })
    return results

def _r6_list_excel_files(site_id, folder_path):
    headers = token_mgr.get_headers("graph")
    clean = folder_path.strip("/")
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root:/{clean}:/children"
    resp = graph_get(url, headers)
    files = []
    for item in resp.json().get("value", []):
        if item["name"].endswith(".xlsx"):
            files.append({
                "id": item["id"], "name": item["name"],
                "lastModifiedDateTime": item.get("lastModifiedDateTime"),
                "createdDateTime": item.get("createdDateTime"),
                "webUrl": item.get("webUrl"),
            })
    return sorted(files, key=lambda f: f.get("lastModifiedDateTime", ""), reverse=True)

def _r6_download_file(site_id, file_path):
    headers = token_mgr.get_headers("graph")
    clean = file_path.strip("/")
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root:/{clean}:/content"
    resp = graph_get(url, headers)
    resp.raise_for_status()
    return resp.content

def _r6_get_audit(site_id, file_id):
    headers = token_mgr.get_headers("graph")
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{file_id}/versions"
    resp = graph_get(url, headers)
    default = {"log": "N/A", "creator": "Unknown", "modifier": "Unknown", "created_ts": None}
    if resp.status_code != 200:
        return default
    versions = resp.json().get("value", [])
    if not versions:
        return default
    logs = []
    for v in versions:
        mod_time = v.get("lastModifiedDateTime", "")[:19].replace("T", " ")
        actor = v.get("lastModifiedBy", {}).get("user", {}).get("displayName") or "System"
        logs.append(f"{mod_time} - {actor}")
    return {
        "log": "\n".join(logs),
        "creator": versions[-1].get("lastModifiedBy", {}).get("user", {}).get("displayName") or "System",
        "modifier": versions[0].get("lastModifiedBy", {}).get("user", {}).get("displayName") or "System",
        "created_ts": versions[-1].get("lastModifiedDateTime"),
    }


# ============================================
# EXCEL PARSER
# ============================================

def _find_col(headers, keywords):
    for idx, h in enumerate(headers):
        if not h:
            continue
        h_str = str(h).strip().lower()
        if all(k in h_str for k in keywords):
            return idx
    return None

def _resolve_col_map(header, app_col_map=None):
    if app_col_map:
        return app_col_map, "app-locked"
    idx_rev = _find_col(header, ["reviewer"])
    idx_res = _find_col(header, ["response"])
    idx_det = _find_col(header, ["details", "change"])
    idx_user = None
    idx_email = None
    # Fix: separate reviewer from reviewer's response
    if idx_rev is not None:
        rev_hdr = str(header[idx_rev]).strip().lower() if header[idx_rev] else ""
        if "response" in rev_hdr:
            idx_rev = None
            for i, h in enumerate(header):
                h_str = str(h).strip().lower() if h else ""
                if "reviewer" in h_str and "response" not in h_str:
                    idx_rev = i
                    break
    for i, h in enumerate(header):
        h_str = str(h).strip().lower() if h else ""
        if idx_user is None and ("name" in h_str or "display" in h_str) and "reviewer" not in h_str and "manager" not in h_str:
            idx_user = i
        if idx_email is None and ("email" in h_str or h_str == "mail"):
            idx_email = i
    if idx_rev is None or idx_res is None:
        return None, "invalid"
    return {"idx_rev": idx_rev, "idx_res": idx_res, "idx_det": idx_det,
            "idx_user": idx_user, "idx_email": idx_email}, "detected"

def _read_excel_rows(excel_bytes, reviewer_name, file_name, folder_url, app_col_map=None):
    wb = load_workbook(io.BytesIO(excel_bytes), read_only=True)
    sheet_name = wb.sheetnames[0]
    for sn in wb.sheetnames:
        if "user listing" in sn.lower():
            sheet_name = sn
            break
    ws = wb[sheet_name]
    rows_iter = ws.iter_rows(values_only=True)
    try:
        header = next(rows_iter)
    except StopIteration:
        return [], None, "empty-sheet"
    col_map, src = _resolve_col_map(header, app_col_map=app_col_map)
    if not col_map:
        return [], None, src
    results = []
    for i, row in enumerate(rows_iter, start=2):
        def safe(idx):
            return row[idx] if idx is not None and idx < len(row) else None
        r_rev, r_res = safe(col_map["idx_rev"]), safe(col_map["idx_res"])
        r_det, r_user, r_email = safe(col_map["idx_det"]), safe(col_map["idx_user"]), safe(col_map["idx_email"])
        if str(r_rev).strip().lower() != reviewer_name.lower():
            continue
        val_res = str(r_res).strip() if r_res else ""
        val_det = str(r_det).strip() if r_det else ""
        results.append({
            "reviewer": reviewer_name,
            "user_name": str(r_user).strip() if r_user else "",
            "user_email": str(r_email).strip() if r_email else "",
            "response": val_res, "details": val_det,
            "is_missing": (val_res == ""),
            "row_number": i, "file_name": file_name, "folder_url": folder_url,
        })
    return results, col_map, src

def _row_stats(txt):
    txt = str(txt).lower().strip()
    kw_a = ['approv', 'retain', 'keep', 'confirm', 'yes', 'ok', 'active']
    kw_d = ['denied', 'deny', 'remove', 'delete', 'revok', 'reject', 'no']
    kw_c = ['change', 'modif', 'updat', 'correct', 'edit', 'adjust']
    return {
        "is_appr": 1 if any(k in txt for k in kw_a) else 0,
        "is_deny": 1 if any(k in txt for k in kw_d) else 0,
        "is_chg": 1 if any(k in txt for k in kw_c) else 0,
    }


# ============================================
# APP SELECTOR UI
# ============================================

R6_TARGET_APPS = []
R6_USE_CACHE = True

s6_status = widgets.HTML(value="<i>Connect and select apps to scan.</i>")
s6_output = widgets.Output()

s6_btn_connect = widgets.Button(description="🔌 Connect", button_style="warning",
                                 layout=widgets.Layout(width="120px"))
s6_btn_scan = widgets.Button(description="🔍 Scan Now", button_style="success",
                              layout=widgets.Layout(width="160px", height="40px"), disabled=True)
s6_btn_export = widgets.Button(description="💾 Save Reports", button_style="info", disabled=True)
s6_btn_global = widgets.Button(description="📊 Global Report", button_style="primary", disabled=True)

s6_app_container = widgets.VBox()
s6_dashboard = widgets.VBox()
s6_chk_cache = widgets.Checkbox(value=True, description="⚡ Use Cache", indent=False)

_r6_site_id = None


def on_s6_connect(_):
    global _r6_site_id
    s6_btn_connect.disabled = True
    try:
        _r6_site_id = _r6_get_site_id()
        s6_status.value = f"<span style='color:green'>✅ Connected (site: {_r6_site_id[:15]}...)</span>"

        # Build app tree
        categories = _r6_list_folders(_r6_site_id, BASE_PATH)
        app_checks = []
        s6_rows = []
        for cat in categories:
            cat_label = widgets.HTML(f"<b>📁 {cat['name']}</b>")
            btn_exp = widgets.Button(description="➕", button_style="info",
                                      layout=widgets.Layout(width="50px"))
            app_box = widgets.VBox(layout=widgets.Layout(margin="0 0 0 30px", display="none"))

            def make_expand(cn, ab, bt):
                def _exp(b):
                    if bt.description == "➕":
                        bt.description = "⏳"
                        apps = _r6_list_folders(_r6_site_id, f"{BASE_PATH}/{cn}")
                        cbs = []
                        for app in apps:
                            cb = widgets.Checkbox(value=False, description=app["name"], indent=False,
                                                   layout=widgets.Layout(width="400px"))
                            cb._app_data = (cn, app["name"], f"{BASE_PATH}/{cn}/{app['name']}")
                            app_checks.append(cb)
                            cbs.append(cb)
                        ab.children = tuple(cbs) if cbs else (widgets.Label("(Empty)"),)
                        ab.layout.display = "block"
                        bt.description = "➖"
                    else:
                        ab.layout.display = "none" if ab.layout.display == "block" else "block"
                        bt.description = "➕" if ab.layout.display == "none" else "➖"
                return _exp
            btn_exp.on_click(make_expand(cat["name"], app_box, btn_exp))
            s6_rows.append(widgets.HBox([btn_exp, cat_label]))
            s6_rows.append(app_box)

        def on_confirm(_):
            global R6_TARGET_APPS, R6_USE_CACHE
            R6_TARGET_APPS = [c._app_data for c in app_checks if c.value]
            R6_USE_CACHE = s6_chk_cache.value
            if R6_TARGET_APPS:
                s6_status.value = f"<span style='color:green'>🎯 {len(R6_TARGET_APPS)} apps selected</span>"
                s6_btn_scan.disabled = False
            else:
                s6_status.value = "<span style='color:orange'>⚠️ No apps selected</span>"

        btn_conf = widgets.Button(description="✅ Confirm", button_style="success")
        btn_conf.on_click(on_confirm)
        s6_app_container.children = tuple(s6_rows + [s6_chk_cache, btn_conf])
    except Exception as e:
        s6_status.value = f"<span style='color:red'>❌ {e}</span>"
    finally:
        s6_btn_connect.disabled = False

s6_btn_connect.on_click(on_s6_connect)


# ============================================
# SCAN ENGINE
# ============================================

def on_s6_scan(_):
    global cache_updated_flag
    s6_output.clear_output()
    s6_btn_scan.disabled = True
    try:
        local_cache = load_json_safe(REPORT_CACHE_FILE)
        manual_notes = load_json_safe(REPORT_NOTES_FILE)
        all_responses = []
        errors = []
        app_col_store = {}

        for category, app_name, app_path in R6_TARGET_APPS:
            try:
                reviewers_raw = _r6_list_folders(_r6_site_id, app_path)
                reviewers = [r for r in reviewers_raw if r["name"].lower() not in EXCLUDED_FOLDERS]
                total = len(reviewers)
                logger(f"📂 App: {app_name} | Reviewers: {total}")
                schema_key = f"{category}|{app_name}"
                app_col = app_col_store.get(schema_key)

                for idx, folder in enumerate(reviewers, 1):
                    rev_name = folder["name"]
                    folder_url = folder["webUrl"]
                    folder_path = f"{app_path}/{rev_name}"
                    cache_key = f"{category}|{app_name}|{rev_name}"

                    try:
                        files = _r6_list_excel_files(_r6_site_id, folder_path)
                        match_cands = [f for f in files if rev_name.lower() in f["name"].lower()]
                        target = match_cands[0] if match_cands else (files[0] if files else None)
                        if not target:
                            continue

                        remote_mod = target.get("lastModifiedDateTime")
                        cached = local_cache.get(cache_key)
                        is_hit = False

                        if (R6_USE_CACHE and cached and cached.get("v") == CACHE_VERSION
                                and cached.get("last_mod") == remote_mod
                                and "rows" in cached and len(cached["rows"]) > 0):
                            pending = any(r.get("is_missing") for r in cached.get("rows", []))
                            if not pending:
                                is_hit = True

                        if is_hit:
                            audit_snap = cached.get("audit", {})
                            for r in cached["rows"]:
                                rc = r.copy()
                                st = _row_stats(r["response"])
                                rc.update({
                                    "Category": category, "App_Name": app_name,
                                    "Last_Modified": remote_mod,
                                    "File_Created_Date": audit_snap.get("created_ts"),
                                    "Audit_Log": audit_snap.get("log"),
                                    "File_Creator": audit_snap.get("creator"),
                                    "File_Modifier": audit_snap.get("modifier"),
                                    "stats_appr": st["is_appr"], "stats_deny": st["is_deny"],
                                    "stats_chg": st["is_chg"], "source_is_cache": True,
                                })
                                all_responses.append(rc)
                            continue

                        content = _r6_download_file(_r6_site_id, f"{folder_path}/{target['name']}")
                        audit = _r6_get_audit(_r6_site_id, target["id"])
                        rows, det_map, src = _read_excel_rows(content, rev_name, target["name"], folder_url, app_col)

                        if det_map and not app_col:
                            app_col = det_map
                            app_col_store[schema_key] = det_map

                        s_a, s_d, s_c, miss = 0, 0, 0, 0
                        clean_rows = []
                        for r in rows:
                            st = _row_stats(r["response"])
                            s_a += st["is_appr"]; s_d += st["is_deny"]; s_c += st["is_chg"]
                            if r["is_missing"]:
                                miss += 1
                            clean_rows.append({
                                "reviewer": r["reviewer"], "user_name": r.get("user_name", ""),
                                "user_email": r.get("user_email", ""),
                                "response": r["response"], "details": r["details"],
                                "is_missing": r["is_missing"], "row_number": r["row_number"],
                                "file_name": r["file_name"], "folder_url": r["folder_url"],
                            })
                            final_created = audit.get("created_ts") or target.get("createdDateTime")
                            r.update({
                                "Category": category, "App_Name": app_name,
                                "Last_Modified": remote_mod, "File_Created_Date": final_created,
                                "Audit_Log": audit["log"], "File_Creator": audit["creator"],
                                "File_Modifier": audit["modifier"],
                                "stats_appr": st["is_appr"], "stats_deny": st["is_deny"],
                                "stats_chg": st["is_chg"], "source_is_cache": False,
                            })
                        all_responses.extend(rows)

                        if rows:
                            local_cache[cache_key] = {
                                "v": CACHE_VERSION, "last_mod": remote_mod,
                                "stats": {"Appr": s_a, "Deny": s_d, "Chg": s_c},
                                "audit": audit, "rows": clean_rows,
                            }
                            cache_updated_flag = True

                        with s6_output:
                            src_lbl = "Cache" if is_hit else "Live"
                            print(f"  [{idx}/{total}] {rev_name} ({src_lbl}) A:{s_a} D:{s_d} C:{s_c} Miss:{miss}")

                    except Exception as e:
                        errors.append({"app": app_name, "reviewer": rev_name, "error": str(e)})
            except Exception as e:
                logger(f"App error ({app_name}): {e}", "error")

        if cache_updated_flag:
            atomic_json_save(REPORT_CACHE_FILE, local_cache)
            logger(f"💾 Cache saved (v{CACHE_VERSION})")

        # Build dashboard
        globals()["r6_df"] = pd.DataFrame(all_responses)
        globals()["r6_notes"] = manual_notes
        _build_r6_dashboard()
        s6_btn_export.disabled = False
        s6_btn_global.disabled = False
        s6_status.value = f"<span style='color:green'>✅ Scan complete: {len(all_responses)} rows from {len(R6_TARGET_APPS)} apps</span>"
        logger(f"Stage 6: {len(all_responses)} rows scanned")
    except Exception as e:
        s6_status.value = f"<span style='color:red'>❌ {e}</span>"
    finally:
        s6_btn_scan.disabled = False

s6_btn_scan.on_click(on_s6_scan)


# ============================================
# DASHBOARD
# ============================================

_r6_widget_store = {}

def _r6_compute_overall_progress(stats_df, raw_df):
    folder_map = raw_df.groupby(["Category", "App_Name", "reviewer"]).agg(
        folder_url=("folder_url", "first"),
    ).reset_index()

    merged = stats_df.merge(folder_map, on=["Category", "App_Name", "reviewer"], how="left")

    total_app_reviewers = int(len(merged))
    pending_app_reviewers = int((merged["missing"] > 0).sum()) if total_app_reviewers else 0
    done_app_reviewers = total_app_reviewers - pending_app_reviewers
    progress_pct = round(done_app_reviewers / total_app_reviewers * 100, 1) if total_app_reviewers else 0.0
    distinct_reviewers_to_notify = int(merged.loc[merged["missing"] > 0, "reviewer"].nunique()) if total_app_reviewers else 0

    remaining = merged[merged["missing"] > 0].copy()
    if not remaining.empty:
        denom = remaining["total_rows"].replace(0, pd.NA)
        remaining["Completion %"] = (((remaining["total_rows"] - remaining["missing"]) / denom) * 100).round(1).fillna(0.0)
        remaining = remaining.rename(columns={
            "App_Name": "App Name",
            "reviewer": "Reviewer",
            "missing": "Missing",
            "total_rows": "Total Rows",
            "folder_url": "Folder URL",
        })
        remaining = remaining[["Category", "App Name", "Reviewer", "Missing", "Total Rows", "Completion %", "Folder URL"]]
        remaining = remaining.sort_values(["Missing", "Category", "App Name", "Reviewer"], ascending=[False, True, True, True])
    else:
        remaining = pd.DataFrame(columns=["Category", "App Name", "Reviewer", "Missing", "Total Rows", "Completion %", "Folder URL"])

    overview_df = pd.DataFrame([
        {"Metric": "Total app-reviewers", "Value": total_app_reviewers},
        {"Metric": "Pending app-reviewers", "Value": pending_app_reviewers},
        {"Metric": "Done app-reviewers", "Value": done_app_reviewers},
        {"Metric": "Overall progress (%)", "Value": progress_pct},
        {"Metric": "Distinct reviewers to notify", "Value": distinct_reviewers_to_notify},
    ])

    return {
        "total_app_reviewers": total_app_reviewers,
        "pending_app_reviewers": pending_app_reviewers,
        "done_app_reviewers": done_app_reviewers,
        "progress_pct": progress_pct,
        "distinct_reviewers_to_notify": distinct_reviewers_to_notify,
        "overview_df": overview_df,
        "remaining_work_df": remaining,
    }

def _r6_remaining_work_html(remaining_df):
    if remaining_df is None or remaining_df.empty:
        return "<i>✅ No pending app-reviewers. All done.</i>"

    cell_style = "padding:6px; overflow-wrap:anywhere; word-break:break-word; white-space:normal; vertical-align:middle"
    table = (
        "<div style='width:100%; overflow:auto'>"
        "<table border='1' style='margin:0 auto; border-collapse:collapse; width:96%; font-size:12px; "
        "border:1px solid #d8dde6; table-layout:fixed'>"
    )
    table += (
        "<tr style='background:#eef3f8; font-weight:bold'>"
        "<th style='padding:6px; width:18%; vertical-align:middle'>Quarter</th>"
        "<th style='padding:6px; width:24%; vertical-align:middle'>App Name</th>"
        "<th style='padding:6px; width:20%; vertical-align:middle'>Reviewer</th>"
        "<th style='padding:6px; width:10%; vertical-align:middle'>Missing</th>"
        "<th style='padding:6px; width:10%; vertical-align:middle'>Total</th>"
        "<th style='padding:6px; width:10%; vertical-align:middle'>Completion %</th>"
        "<th style='padding:6px; width:8%; vertical-align:middle'>Link</th>"
        "</tr>"
    )
    for _, r in remaining_df.iterrows():
        url = r.get("Folder URL") or "#"
        link_html = (
            f"<a href='{url}' target='_blank' rel='noopener noreferrer' "
            "style='background:#0078d4;color:#fff;padding:6px 10px;border-radius:6px;"
            "text-decoration:none;display:inline-block;white-space:nowrap'>Open Folder</a>"
        )
        table += (
            "<tr>"
            f"<td style='{cell_style}'>{r.get('Category', '')}</td>"
            f"<td style='{cell_style}'>{r.get('App Name', '')}</td>"
            f"<td style='{cell_style}'>{r.get('Reviewer', '')}</td>"
            f"<td style='padding:6px; text-align:center; vertical-align:middle'>{int(r.get('Missing', 0))}</td>"
            f"<td style='padding:6px; text-align:center; vertical-align:middle'>{int(r.get('Total Rows', 0))}</td>"
            f"<td style='padding:6px; text-align:center; vertical-align:middle'>{r.get('Completion %', 0)}</td>"
            f"<td style='padding:6px; text-align:center; vertical-align:middle'>{link_html}</td>"
            "</tr>"
        )
    table += "</table></div>"
    return table

def _build_r6_dashboard():
    df = globals().get("r6_df")
    if df is None or df.empty:
        s6_dashboard.children = [widgets.HTML("<h4>No data found</h4>")]
        return
    stats = df.groupby(["Category", "App_Name", "reviewer"]).agg(
        total_rows=("reviewer", "size"),
        missing=("is_missing", "sum"),
        approved=("stats_appr", "sum"), denied=("stats_deny", "sum"),
        changed=("stats_chg", "sum"),
        is_cached=("source_is_cache", "all"),
    ).reset_index()

    prog = _r6_compute_overall_progress(stats, df)
    total_app_reviewers = prog["total_app_reviewers"]
    pending_app_reviewers = prog["pending_app_reviewers"]
    done_app_reviewers = prog["done_app_reviewers"]
    progress_pct = prog["progress_pct"]
    distinct_reviewers_to_notify = prog["distinct_reviewers_to_notify"]

    w_metrics = widgets.HTML(
        f"Total app-reviewers: {total_app_reviewers} &nbsp; "
        f"Pending: {pending_app_reviewers} &nbsp; "
        f"Done: {done_app_reviewers} &nbsp; "
        f"Progress: {progress_pct}% &nbsp; "
        f"Distinct reviewers to notify: {distinct_reviewers_to_notify}"
    )
    w_bar = widgets.IntProgress(
        value=done_app_reviewers,
        min=0,
        max=max(1, total_app_reviewers),
        bar_style="success" if pending_app_reviewers == 0 else "info",
        layout=widgets.Layout(width="420px"),
    )
    w_bar_lbl = widgets.HTML(
        f"{done_app_reviewers}/{total_app_reviewers} completed",
        layout=widgets.Layout(width="180px"),
    )

    overview_box = widgets.VBox([
        widgets.HTML("<h4>📈 Progress Overview</h4>"),
        w_metrics,
        widgets.HBox([w_bar, w_bar_lbl], layout=widgets.Layout(align_items="center")),
        widgets.HTML("<h4>🧾 Remaining Work (Pending App-Reviewers)</h4>"),
        widgets.HTML(_r6_remaining_work_html(prog["remaining_work_df"])),
    ], layout=widgets.Layout(margin="8px 0 12px 0"))

    unified = {}
    for _, row in stats.iterrows():
        key = f"{row['Category']} > {row['App_Name']}"
        if key not in unified:
            unified[key] = {"Category": row["Category"], "App_Name": row["App_Name"],
                            "reviewers": {}, "stats": {"total": 0, "done": 0}}
        node = unified[key]
        node["stats"]["total"] += 1
        is_done = (row["missing"] == 0)
        if is_done:
            node["stats"]["done"] += 1
        d_style = "color:red;font-weight:bold" if row["denied"] > 0 else "color:#555"
        node["reviewers"][row["reviewer"]] = {
            "status": "✅ Completed" if is_done else f"❌ Pending: {int(row['missing'])}",
            "detail": f"Appr:{int(row['approved'])} | <span style='{d_style}'>Deny:{int(row['denied'])}</span> | Chg:{int(row['changed'])}",
        }

    items = []
    for app_key in sorted(unified.keys()):
        d = unified[app_key]
        pct = int(d["stats"]["done"] / d["stats"]["total"] * 100) if d["stats"]["total"] > 0 else 0
        lbl = widgets.HTML(f"<b>📂 {app_key}</b> &nbsp; <span style='background:#eee;padding:2px 5px;border-radius:4px'>{pct}% Done</span>")
        rev_lines = []
        for rn, rd in d["reviewers"].items():
            rev_lines.append(widgets.HBox([
                widgets.HTML(rn, layout=widgets.Layout(width="250px")),
                widgets.HTML(rd["status"], layout=widgets.Layout(width="200px")),
                widgets.HTML(rd["detail"]),
            ]))
        items.append(widgets.VBox([lbl, widgets.VBox(rev_lines, layout=widgets.Layout(margin="5px 0 10px 20px"))]))
    s6_dashboard.children = tuple([overview_box] + items)
    globals()["r6_unified"] = unified
    globals()["r6_progress"] = prog


# Export handlers
def on_s6_export(_):
    df = globals().get("r6_df")
    unified = globals().get("r6_unified", {})
    if df is None or df.empty:
        return
    saved = 0
    for app_key, d in unified.items():
        app_rows = df[(df["Category"] == d["Category"]) & (df["App_Name"] == d["App_Name"])].to_dict("records")
        final = [{
            "User Name": r.get("user_name", ""), "User Email": r.get("user_email", ""),
            "Reviewer": r["reviewer"], "File Name": r.get("file_name"),
            "Reviewer Response": r.get("response"), "Details of Access Change": r.get("details"),
            "Final Status": "Completed" if not r.get("is_missing") else "Pending",
            "Audit Log": r.get("Audit_Log"),
        } for r in app_rows]
        if final:
            safe_name = re.sub(r'[\\/*?:"<>|]', "", d["App_Name"])
            fpath = safe_excel_path(os.path.join(REPORT_DIR, f"{safe_name}_{TODAY_STR}.xlsx"))
            pd.DataFrame(final).to_excel(fpath, index=False)
            format_export_excel(fpath)
            saved += 1
    s6_status.value = f"<span style='color:green'>✅ Saved {saved} reports</span>"

def on_s6_global(_):
    df = globals().get("r6_df")
    if df is None or df.empty:
        return
    stats = df.groupby(["Category", "App_Name", "reviewer"]).agg(
        total_rows=("reviewer", "size"),
        missing=("is_missing", "sum"), approved=("stats_appr", "sum"),
        denied=("stats_deny", "sum"), changed=("stats_chg", "sum"),
    ).reset_index()
    prog = _r6_compute_overall_progress(stats, df)
    rows = [{"Category": r["Category"], "App Name": r["App_Name"], "Reviewer": r["reviewer"],
             "Status": "Completed" if r["missing"] == 0 else "Pending",
             "Approved": int(r["approved"]), "Denied": int(r["denied"]),
             "Changed": int(r["changed"])} for _, r in stats.iterrows()]
    fpath = safe_excel_path(os.path.join(REPORT_DIR, f"Summary_Report_{TODAY_STR}.xlsx"))

    summary_df = pd.DataFrame(rows)
    overview_df = prog["overview_df"]
    remaining_df = prog["remaining_work_df"]

    with pd.ExcelWriter(fpath, engine="openpyxl") as writer:
        summary_df.to_excel(writer, index=False, sheet_name="Sheet1")
        overview_df.to_excel(writer, index=False, sheet_name="Progress", startrow=0)
        start = len(overview_df) + 2
        remaining_df.to_excel(writer, index=False, sheet_name="Progress", startrow=start)

    format_export_excel(fpath)
    s6_status.value = f"<span style='color:green'>✅ Global report saved</span>"

s6_btn_export.on_click(on_s6_export)
s6_btn_global.on_click(on_s6_global)


stage6_ui = widgets.VBox([
    widgets.HTML(f"""
        <div style='background: linear-gradient(135deg, #0c3483 0%, #a2b6df 100%);
            padding: 20px; border-radius: 8px; color: white; margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
            <h2 style='margin: 0 0 10px 0;'>📊 Stage 6: Report Scanner & Dashboard</h2>
            <p style='margin: 0; opacity: 0.95;'>
                Scan reviewer Excel files from SharePoint. Year: {AER_REVIEW_YEAR}. Atomic cache writes.
            </p>
        </div>
    """),
    s6_btn_connect,
    s6_app_container,
    widgets.HBox([s6_btn_scan, s6_btn_export, s6_btn_global]),
    s6_status,
    s6_output,
    s6_dashboard,
])

clear_output()
display(stage6_ui)
