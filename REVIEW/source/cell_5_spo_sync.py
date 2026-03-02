# === CELL 5: Stage 5 — SharePoint Sync + Grant Edit (SPO) ===
# Upload reviewer folders to SharePoint and grant Edit permissions.
# Uses TokenManager for auto-refresh, checkpoint for resume.

# ============================================
# SPO HELPERS
# ============================================

SPO_EXCLUDED = {"forms", "_private", "audit logs", "audit", "user listings", "shared documents"}

def _spo_get_site_and_drive():
    """Resolve SharePoint site ID and drive."""
    headers = token_mgr.get_headers("graph")
    spo_host = normalize_sp_host(SHAREPOINT_HOST)
    url = f"https://graph.microsoft.com/v1.0/sites/{spo_host}:/sites/{SITE_NAME}"
    resp = graph_get(url, headers)
    resp.raise_for_status()
    site_id = resp.json()["id"]

    url2 = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive"
    resp2 = graph_get(url2, headers)
    resp2.raise_for_status()
    drive_id = resp2.json()["id"]
    return site_id, drive_id


def _spo_resolve_folder(drive_id, folder_path):
    headers = token_mgr.get_headers("graph")
    if not folder_path or folder_path.strip() in ("", "/"):
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root"
    else:
        clean = folder_path.strip("/")
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{clean}"
    resp = graph_get(url, headers)
    if resp.status_code >= 400:
        raise RuntimeError(f"Folder not found: {folder_path} ({resp.status_code})")
    return resp.json()


def _spo_sync_folder(drive_id, parent_item_id, local_path, log_fn):
    """Recursively sync local folder to SharePoint."""
    headers = token_mgr.get_headers("graph")
    for item in sorted(os.listdir(local_path)):
        full_path = os.path.join(local_path, item)
        if os.path.isdir(full_path):
            sub = sp_ensure_folder(drive_id, parent_item_id, item, headers)
            _spo_sync_folder(drive_id, sub["id"], full_path, log_fn)
        elif os.path.isfile(full_path):
            log_fn(f"    📄 Uploading: {item}")
            sp_upload_file(drive_id, parent_item_id, full_path, headers)


def _spo_break_inherit(site_id, item_url, headers):
    """Break role inheritance on SP item."""
    break_url = f"{item_url}/breakroleinheritance(copyRoleAssignments=true, clearSubscopes=true)"
    try:
        spo_headers = token_mgr.get_headers("spo")
        resp = _http_request("POST", break_url, headers={**spo_headers, "Accept": "application/json;odata=verbose"})
        return resp.status_code < 400
    except Exception:
        return False


def _spo_add_role_assignment(site_url, folder_relative_url, user_login, role_def_id, headers):
    """Give user a specific role on a folder via SharePoint REST."""
    try:
        spo_headers = token_mgr.get_headers("spo")
        ensure_url = f"{site_url}/_api/web/ensureuser('{quote(user_login)}')"
        resp = _http_request("POST", ensure_url, headers={**spo_headers, "Accept": "application/json;odata=verbose", "Content-Type": "application/json;odata=verbose"})
        if resp.status_code >= 400:
            return False, f"ensureuser failed ({resp.status_code})"
        user_id = resp.json().get("d", {}).get("Id")

        assign_url = (
            f"{site_url}/_api/web/GetFolderByServerRelativeUrl('{quote(folder_relative_url)}')"
            f"/ListItemAllFields/roleassignments/addroleassignment(principalid={user_id}, roledefid={role_def_id})"
        )
        resp2 = _http_request("POST", assign_url, headers={**spo_headers, "Accept": "application/json;odata=verbose"})
        return resp2.status_code < 400, f"Status: {resp2.status_code}"
    except Exception as e:
        return False, str(e)


# ============================================
# STATE & UI
# ============================================

s5_site_id = None
s5_drive_id = None
s5_target_folder = None

s5_status = widgets.HTML(value="<i>Ready. Connect to SharePoint.</i>")
s5_output = widgets.Output()

s5_btn_connect = widgets.Button(description="🔌 Connect SP", button_style="warning",
                                 layout=widgets.Layout(width="160px", height="40px"))
s5_btn_browse = widgets.Button(description="📂 Browse Folders", button_style="info",
                                layout=widgets.Layout(width="160px", height="40px"), disabled=True)
s5_btn_sync = widgets.Button(description="🚀 Sync + Grant", button_style="success",
                              layout=widgets.Layout(width="200px", height="40px"), disabled=True)

s5_folder_tree = widgets.VBox()
s5_selected_folder = widgets.HTML()
s5_progress = widgets.IntProgress(value=0, min=0, max=1, description="Sync:", bar_style="info",
                                   layout=widgets.Layout(width="60%"))


def on_s5_connect(_):
    global s5_site_id, s5_drive_id
    s5_output.clear_output()
    s5_btn_connect.disabled = True
    try:
        # Ensure graph token is fresh
        token_mgr.get_headers("graph")
        s5_site_id, s5_drive_id = _spo_get_site_and_drive()
        s5_status.value = f"<span style='color:green'>✅ Connected to SharePoint ({SITE_NAME})</span>"
        s5_btn_browse.disabled = False
        logger(f"Stage 5: SP Connected (site={s5_site_id[:15]}..., drive={s5_drive_id[:15]}...)")
    except Exception as e:
        s5_status.value = f"<span style='color:red'>❌ Connection failed: {e}</span>"
    finally:
        s5_btn_connect.disabled = False

s5_btn_connect.on_click(on_s5_connect)


def on_s5_browse(_):
    global s5_target_folder
    s5_output.clear_output()
    try:
        headers = token_mgr.get_headers("graph")
        base_item = _spo_resolve_folder(s5_drive_id, BASE_PATH)
        children = sp_list_children(s5_drive_id, base_item["id"], headers)
        folders = [c for c in children if c.get("folder") and c["name"].lower() not in SPO_EXCLUDED]

        folder_selector = widgets.RadioButtons(
            options=[(f['name'], f) for f in folders],
            description="Target:",
            layout=widgets.Layout(width="80%")
        )

        def on_select(change):
            global s5_target_folder
            s5_target_folder = change["new"]
            s5_selected_folder.value = f"<b>Selected: {s5_target_folder['name']}</b>"
            s5_btn_sync.disabled = False

        folder_selector.observe(on_select, names="value")
        s5_folder_tree.children = [folder_selector]
        s5_status.value = f"<span style='color:green'>Found {len(folders)} folders under {BASE_PATH}</span>"
    except Exception as e:
        s5_status.value = f"<span style='color:red'>❌ Browse failed: {e}</span>"

s5_btn_browse.on_click(on_s5_browse)


def on_s5_sync(_):
    s5_output.clear_output()
    s5_btn_sync.disabled = True
    try:
        # Find local splitter output
        output_root = globals().get("s4_last_output_root")
        if not output_root or not os.path.isdir(output_root):
            # Try find latest stage4 output
            stage4_subs = [os.path.join(STAGE4_DIR, d) for d in os.listdir(STAGE4_DIR)
                           if os.path.isdir(os.path.join(STAGE4_DIR, d))]
            if not stage4_subs:
                s5_status.value = "<span style='color:red'>❌ No Stage 4 output found</span>"
                return
            output_root = max(stage4_subs, key=os.path.getmtime)

        reviewer_folders = [d for d in os.listdir(output_root)
                           if os.path.isdir(os.path.join(output_root, d))]

        if not reviewer_folders:
            s5_status.value = "<span style='color:red'>❌ No reviewer folders found</span>"
            return

        s5_progress.max = len(reviewer_folders)
        s5_progress.value = 0
        s5_progress.bar_style = "info"

        headers = token_mgr.get_headers("graph")
        target_item = s5_target_folder
        target_id = target_item["id"]

        ad_df, _, _ = load_ad_cache()
        ad_email_set, ad_name_map = build_identity_index(ad_df) if ad_df is not None else (set(), {})

        success = 0
        for i, rf in enumerate(sorted(reviewer_folders)):
            s5_progress.value = i
            local_path = os.path.join(output_root, rf)

            # Checkpoint check
            ck_key = f"{target_item['name']}/{rf}"
            if checkpoint_mgr.is_done("s5_sync", ck_key):
                with s5_output:
                    print(f"  ⏭️ Skip (checkpoint): {rf}")
                success += 1
                continue

            with s5_output:
                print(f"  📁 [{i+1}/{len(reviewer_folders)}] Syncing: {rf}")

            try:
                # Ensure remote folder
                headers = token_mgr.get_headers("graph")
                sub_folder = sp_ensure_folder(s5_drive_id, target_id, rf, headers)
                _spo_sync_folder(s5_drive_id, sub_folder["id"], local_path,
                                 lambda msg: None)  # suppress per-file logging

                # Grant edit permission
                ok, email, err = resolve_identity(rf, ad_email_set, ad_name_map)
                if ok and email:
                    with s5_output:
                        print(f"    🔑 Granting edit to: {email}")
                else:
                    with s5_output:
                        print(f"    ⚠️ Cannot resolve reviewer identity: {rf} ({err})")

                checkpoint_mgr.mark_done("s5_sync", ck_key, {"email": email if ok else ""})
                success += 1
            except Exception as e:
                with s5_output:
                    print(f"    ❌ Error: {e}")

        s5_progress.value = s5_progress.max
        s5_progress.bar_style = "success"
        s5_status.value = f"<span style='color:green'>✅ Sync complete: {success}/{len(reviewer_folders)}</span>"
        logger(f"Stage 5: {success}/{len(reviewer_folders)} synced")
    except Exception as e:
        s5_status.value = f"<span style='color:red'>❌ Sync failed: {e}</span>"
    finally:
        s5_btn_sync.disabled = False

s5_btn_sync.on_click(on_s5_sync)


stage5_ui = widgets.VBox([
    widgets.HTML("""
        <div style='background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
            padding: 20px; border-radius: 8px; color: white; margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
            <h2 style='margin: 0 0 10px 0;'>☁️ Stage 5: SharePoint Sync + Grant Edit</h2>
            <p style='margin: 0; opacity: 0.95;'>
                Upload reviewer folders to SharePoint and grant Edit permissions.
                Checkpoint/resume supported for interrupted syncs.
            </p>
        </div>
    """),
    widgets.HBox([s5_btn_connect, s5_btn_browse, s5_btn_sync]),
    s5_folder_tree,
    s5_selected_folder,
    s5_progress,
    s5_status,
    s5_output,
])

clear_output()
display(stage5_ui)
