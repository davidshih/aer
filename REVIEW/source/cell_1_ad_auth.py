# === CELL 1: Stage 1 — AD Authentication & User Download ===
# Authenticates with Azure AD, downloads all users, caches to CSV.
# Uses TokenManager for auto-refresh and graph_get() for retry.

# ============================================
# GRAPH SCOPES
# ============================================

GRAPH_SCOPES = ["User.Read.All", "Mail.Send", "Mail.Read", "Files.ReadWrite", "Sites.Read.All"]
GRAPH_SCOPES_WITH_AUDIT = GRAPH_SCOPES + ["AuditLog.Read.All"]

SPO_SCOPES_TEMPLATE = "https://{host}/AllSites.FullControl"

# ============================================
# UI WIDGETS
# ============================================

s1_status = widgets.HTML(value="<i>Ready. Click Login to begin.</i>")
s1_output = widgets.Output()

s1_chk_signin = widgets.Checkbox(value=False, description="Include Sign-In Activity", indent=False)
s1_chk_cache = widgets.Checkbox(value=True, description="Use Cached Data (if available)", indent=False)
s1_progress = widgets.IntProgress(value=0, min=0, max=1, description="Progress:", bar_style="info",
                                   layout=widgets.Layout(width="60%"))

s1_btn_login = widgets.Button(description="🔐 Login", button_style="warning",
                               layout=widgets.Layout(width="150px", height="40px"))
s1_btn_download = widgets.Button(description="⬇️ Download Users", button_style="success",
                                  layout=widgets.Layout(width="180px", height="40px"), disabled=True)
s1_btn_refresh = widgets.Button(description="🔄 Refresh", button_style="info",
                                 layout=widgets.Layout(width="120px", height="40px"), disabled=True)


# ============================================
# LOGIN HANDLER
# ============================================

def on_s1_login(_):
    s1_output.clear_output()
    s1_btn_login.disabled = True
    try:
        scopes = GRAPH_SCOPES_WITH_AUDIT if s1_chk_signin.value else GRAPH_SCOPES
        token_mgr.login_interactive(scopes, scope_key="graph")

        # Attempt SPO login if SHAREPOINT_HOST is set
        spo_host = normalize_sp_host(SHAREPOINT_HOST)
        if spo_host:
            try:
                spo_scopes = [SPO_SCOPES_TEMPLATE.format(host=spo_host)]
                token_mgr.login_interactive(spo_scopes, scope_key="spo")
                s1_status.value = "<span style='color:green'>✅ Graph + SharePoint login successful</span>"
            except Exception as e:
                logger(f"SPO login skipped: {e}", "warning")
                s1_status.value = "<span style='color:green'>✅ Graph login OK</span> | <span style='color:orange'>⚠️ SPO login skipped</span>"
        else:
            s1_status.value = "<span style='color:green'>✅ Graph login successful</span>"

        s1_btn_download.disabled = False
        s1_btn_refresh.disabled = False
    except Exception as e:
        s1_status.value = f"<span style='color:red'>❌ Login failed: {e}</span>"
        logger(f"Login failed: {e}", "error")
    finally:
        s1_btn_login.disabled = False

s1_btn_login.on_click(on_s1_login)


# ============================================
# USER DOWNLOAD
# ============================================

def _download_ad_users(include_signin=False):
    headers = token_mgr.get_headers("graph")
    select_fields = "id,displayName,mail,userPrincipalName,department,jobTitle,accountEnabled,employeeType"
    expand = "$expand=manager($select=displayName,mail,department,jobTitle)"

    if include_signin:
        url = f"https://graph.microsoft.com/v1.0/users?$select={select_fields},signInActivity&{expand}&$top=100"
    else:
        url = f"https://graph.microsoft.com/v1.0/users?$select={select_fields}&{expand}&$top=100"

    all_users = []
    page = 0
    s1_progress.value = 0
    s1_progress.max = 1
    s1_progress.bar_style = "info"

    while url:
        page += 1
        headers = token_mgr.get_headers("graph")  # refresh check each page
        resp = graph_get(url, headers)
        if resp.status_code >= 400:
            raise RuntimeError(f"User download failed ({resp.status_code}): {resp.text[:300]}")
        data = resp.json()
        users = data.get("value", [])
        all_users.extend(users)

        # Dynamic progress
        if page == 1 and "@odata.nextLink" in data:
            s1_progress.max = max(page + 10, 20)
        s1_progress.value = min(page, s1_progress.max)
        s1_status.value = f"<span style='color:blue'>⬇️ Downloading... Page {page} ({len(all_users)} users)</span>"

        url = data.get("@odata.nextLink")

    s1_progress.value = s1_progress.max
    s1_progress.bar_style = "success"
    return all_users


def _process_users_to_df(raw_users, include_signin=False):
    records = []
    for u in raw_users:
        email = (u.get("mail") or u.get("userPrincipalName") or "").strip().lower()
        mgr = u.get("manager") or {}
        rec = {
            "email": email,
            "displayName": (u.get("displayName") or "").strip(),
            "department": (u.get("department") or "").strip(),
            "jobTitle": (u.get("jobTitle") or "").strip(),
            "accountEnabled": u.get("accountEnabled"),
            "employeeType": (u.get("employeeType") or "").strip(),
            "managerName": (mgr.get("displayName") or "").strip(),
            "managerEmail": (mgr.get("mail") or "").strip().lower(),
            "managerDepartment": (mgr.get("department") or "").strip(),
            "managerJobTitle": (mgr.get("jobTitle") or "").strip(),
        }
        if include_signin:
            sia = u.get("signInActivity") or {}
            last_signin = sia.get("lastSignInDateTime") or ""
            rec["lastSignIn"] = last_signin
            if last_signin:
                try:
                    dt = datetime.fromisoformat(last_signin.replace("Z", "+00:00"))
                    age_days = (datetime.now(dt.tzinfo) - dt).days
                    if age_days <= 30:
                        rec["signInAgeRange"] = "0-1 month"
                    elif age_days <= 90:
                        rec["signInAgeRange"] = "1-3 months"
                    elif age_days <= 180:
                        rec["signInAgeRange"] = "3-6 months"
                    else:
                        rec["signInAgeRange"] = "6+ months"
                    rec["activeIn3Months"] = "Yes" if age_days <= 90 else "No"
                except Exception:
                    rec["signInAgeRange"] = "Unknown"
                    rec["activeIn3Months"] = "Unknown"
            else:
                rec["signInAgeRange"] = "Never"
                rec["activeIn3Months"] = "No"
        records.append(rec)
    return pd.DataFrame(records)


def on_s1_download(_):
    s1_output.clear_output()
    s1_btn_download.disabled = True
    try:
        if s1_chk_cache.value:
            cached_df, cached_path, _ = load_ad_cache()
            if cached_df is not None:
                s1_status.value = f"<span style='color:green'>✅ Loaded from cache: {os.path.basename(cached_path)} ({len(cached_df)} users)</span>"
                s1_progress.value = s1_progress.max = 1
                s1_progress.bar_style = "success"
                globals()["ad_users_df"] = cached_df
                logger(f"AD cache loaded: {cached_path} ({len(cached_df)} records)")
                return

        include_signin = s1_chk_signin.value
        raw_users = _download_ad_users(include_signin)
        df = _process_users_to_df(raw_users, include_signin)
        fname = save_ad_cache(df)
        globals()["ad_users_df"] = df

        s1_status.value = f"<span style='color:green'>✅ Downloaded {len(df)} users, saved as {fname}</span>"
        logger(f"Stage 1 complete: {len(df)} users downloaded")
    except Exception as e:
        s1_status.value = f"<span style='color:red'>❌ Download failed: {e}</span>"
        logger(f"Stage 1 error: {e}", "error")
    finally:
        s1_btn_download.disabled = False

s1_btn_download.on_click(on_s1_download)


def on_s1_refresh(_):
    s1_chk_cache.value = False
    on_s1_download(None)

s1_btn_refresh.on_click(on_s1_refresh)


# ============================================
# UI LAYOUT
# ============================================

stage1_ui = widgets.VBox([
    widgets.HTML("""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px; border-radius: 8px; color: white; margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
            <h2 style='margin: 0 0 10px 0;'>🔐 Stage 1: AD Authentication & User Download</h2>
            <p style='margin: 0; opacity: 0.95;'>
                Authenticate with Azure AD, download all users, and cache locally.
                Token auto-refreshes before expiry.
            </p>
        </div>
    """),
    widgets.HBox([s1_chk_signin, s1_chk_cache]),
    widgets.HBox([s1_btn_login, s1_btn_download, s1_btn_refresh]),
    s1_progress,
    s1_status,
    s1_output,
])

clear_output()
display(stage1_ui)
