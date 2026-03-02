# === CELL 1.5: Stage 1.5 — Org Tree Builder for Dept Heads ===
# Builds org tree, identifies department heads, manages mapping with version control.

# ============================================
# ORG TREE LOGIC
# ============================================

SERVICE_ACCOUNT_PATTERNS = [
    r"^svc[_.]", r"^admin[_.]", r"^noreply", r"^test[_.]",
    r"shared[-_]?mailbox", r"^conference", r"^room[-_.]",
]
SERVICE_TITLE_KEYWORDS = ["bot", "service account", "shared mailbox", "conference room"]

def _is_service_account(email, display_name="", title=""):
    email_lower = str(email or "").strip().lower()
    for pat in SERVICE_ACCOUNT_PATTERNS:
        if re.search(pat, email_lower):
            return True
    title_lower = str(title or "").strip().lower()
    for kw in SERVICE_TITLE_KEYWORDS:
        if kw in title_lower:
            return True
    return False

HEAD_TITLE_KEYWORDS = ["ceo", "cfo", "coo", "cto", "cio", "president",
                        "evp", "svp", "vp", "vice president",
                        "director", "head of", "chief"]

def _is_head_title(title):
    t = str(title or "").strip().lower()
    return any(kw in t for kw in HEAD_TITLE_KEYWORDS)


def build_org_tree(df, root_person=None, max_depth=None):
    root_person = root_person or AER_ROOT_PERSON
    max_depth = max_depth or AER_ORG_DEPTH
    if df is None or df.empty:
        return {}, []

    # Build email -> user map
    user_map = {}
    for _, row in df.iterrows():
        email = str(row.get("email", "")).strip().lower()
        if not email or email == "nan":
            continue
        if _is_service_account(email, row.get("displayName", ""), row.get("jobTitle", "")):
            continue
        user_map[email] = {
            "email": email,
            "displayName": str(row.get("displayName", "")).strip(),
            "department": str(row.get("department", "")).strip(),
            "jobTitle": str(row.get("jobTitle", "")).strip(),
            "managerEmail": str(row.get("managerEmail", "")).strip().lower(),
            "accountEnabled": row.get("accountEnabled", True),
        }

    # Find root
    root_email = None
    root_name_lower = root_person.strip().lower()
    for email, user in user_map.items():
        if user["displayName"].lower() == root_name_lower:
            root_email = email
            break
    if not root_email:
        logger(f"⚠️ Root person '{root_person}' not found in AD cache", "warning")
        return {}, []

    # Build children map
    children_of = {}
    for email, user in user_map.items():
        mgr = user["managerEmail"]
        if mgr and mgr in user_map:
            children_of.setdefault(mgr, []).append(email)

    # BFS to find dept heads (boundary detection)
    dept_heads = []
    visited = set()

    def traverse(email, depth, parent_dept):
        if depth > max_depth or email in visited:
            return
        visited.add(email)
        user = user_map.get(email)
        if not user:
            return
        curr_dept = user["department"]

        # Boundary: department changed from parent
        if parent_dept and curr_dept and curr_dept.lower() != parent_dept.lower():
            if _is_head_title(user["jobTitle"]):
                dept_heads.append({
                    "email": email,
                    "displayName": user["displayName"],
                    "department": curr_dept,
                    "jobTitle": user["jobTitle"],
                    "managerEmail": user["managerEmail"],
                    "depth": depth,
                })

        for child_email in sorted(children_of.get(email, [])):
            traverse(child_email, depth + 1, curr_dept)

    root_user = user_map.get(root_email, {})
    traverse(root_email, 0, root_user.get("department", ""))

    # Build dept -> head mapping
    dept_mapping = {}
    for head in dept_heads:
        dept = head["department"]
        if dept not in dept_mapping:
            dept_mapping[dept] = head

    return dept_mapping, dept_heads


# ============================================
# MAPPING VERSION CONTROL
# ============================================

MAPPING_AUDIT_FILE = os.path.join(INPUT_MAPPING_DIR, "mapping_audit.json")

def save_mapping_with_version(mapping_df, prefix="org_mapping"):
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    # Find next version number
    existing = glob.glob(os.path.join(INPUT_MAPPING_DIR, f"{prefix}_*.csv"))
    version = len(existing) + 1
    fname = f"{prefix}_{ts}_v{version}.csv"
    path = os.path.join(INPUT_MAPPING_DIR, fname)
    mapping_df.to_csv(path, index=False, encoding="utf-8-sig")

    # Record in audit log
    audit = load_json_safe(MAPPING_AUDIT_FILE)
    audit_key = f"v{version}_{ts}"
    audit[audit_key] = {
        "file": fname,
        "timestamp": datetime.now().isoformat(),
        "record_count": len(mapping_df),
    }
    atomic_json_save(MAPPING_AUDIT_FILE, audit)
    logger(f"💾 Mapping saved: {fname} (v{version}, {len(mapping_df)} records)")
    return path

def load_latest_mapping():
    csv_files = glob.glob(os.path.join(INPUT_MAPPING_DIR, "org_mapping_*.csv"))
    if not csv_files:
        return None, ""
    latest = max(csv_files, key=os.path.getmtime)
    try:
        return pd.read_csv(latest), latest
    except Exception:
        return None, latest


# ============================================
# UI
# ============================================

s15_status = widgets.HTML(value="<i>Ready. Load AD cache to build org tree.</i>")
s15_output = widgets.Output()

s15_btn_build = widgets.Button(description="🌳 Build Org Tree", button_style="success",
                                layout=widgets.Layout(width="180px", height="40px"))
s15_btn_save = widgets.Button(description="💾 Save Mapping", button_style="info",
                               layout=widgets.Layout(width="180px", height="40px"), disabled=True)


def on_s15_build(_):
    s15_output.clear_output()
    s15_btn_build.disabled = True
    try:
        ad_df = globals().get("ad_users_df")
        if ad_df is None:
            cached_df, _, err = load_ad_cache()
            if cached_df is None:
                s15_status.value = f"<span style='color:red'>❌ {err}</span>"
                return
            ad_df = cached_df

        dept_mapping, dept_heads = build_org_tree(ad_df)
        globals()["s15_dept_mapping"] = dept_mapping
        globals()["s15_dept_heads"] = dept_heads

        with s15_output:
            print(f"Found {len(dept_heads)} department heads across {len(dept_mapping)} departments")
            print()
            for dept, head in sorted(dept_mapping.items()):
                print(f"  📁 {dept}")
                print(f"     Head: {head['displayName']} ({head['email']})")
                print(f"     Title: {head['jobTitle']}")
                print()

        s15_status.value = f"<span style='color:green'>✅ Org tree built: {len(dept_heads)} heads, {len(dept_mapping)} departments</span>"
        s15_btn_save.disabled = False
        logger(f"Stage 1.5: {len(dept_heads)} dept heads identified")
    except Exception as e:
        s15_status.value = f"<span style='color:red'>❌ {e}</span>"
        logger(f"Stage 1.5 error: {e}", "error")
    finally:
        s15_btn_build.disabled = False

s15_btn_build.on_click(on_s15_build)


def on_s15_save(_):
    dept_mapping = globals().get("s15_dept_mapping", {})
    if not dept_mapping:
        s15_status.value = "<span style='color:red'>❌ No mapping to save. Build tree first.</span>"
        return
    rows = []
    for dept, head in dept_mapping.items():
        rows.append({
            "department": dept,
            "head_email": head["email"],
            "head_name": head["displayName"],
            "head_title": head["jobTitle"],
            "reviewer_email": head.get("managerEmail", head["email"]),
        })
    mapping_df = pd.DataFrame(rows)
    save_mapping_with_version(mapping_df)
    s15_status.value = f"<span style='color:green'>✅ Mapping saved with version control</span>"

s15_btn_save.on_click(on_s15_save)


stage15_ui = widgets.VBox([
    widgets.HTML("""
        <div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            padding: 20px; border-radius: 8px; color: white; margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
            <h2 style='margin: 0 0 10px 0;'>🌳 Stage 1.5: Org Tree Builder</h2>
            <p style='margin: 0; opacity: 0.95;'>
                Build organizational tree, identify department heads, save mapping with version control.
            </p>
        </div>
    """),
    widgets.HBox([s15_btn_build, s15_btn_save]),
    s15_status,
    s15_output,
])

clear_output()
display(stage15_ui)
