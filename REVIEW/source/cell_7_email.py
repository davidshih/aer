# === CELL 7: Stage 7 — Email Notification Center ===
# Send review reminders to reviewers. Uses AD cache for email lookup (not per-reviewer Graph API).
# Configurable template footer. Batch checkpoint to avoid double-send.

# ============================================
# EMAIL HELPERS
# ============================================

EMAIL_CHECKPOINT_FILE = os.path.join(CHECKPOINT_DIR, "email_sent.json")

def _email_lookup_from_ad(reviewer_name, ad_email_set=None, ad_name_map=None):
    """Resolve reviewer name to email using AD cache (no Graph API call)."""
    if ad_email_set is None or ad_name_map is None:
        ad_df, _, _ = load_ad_cache()
        if ad_df is not None:
            ad_email_set, ad_name_map = build_identity_index(ad_df)
        else:
            return ""
    ok, email, _ = resolve_identity(reviewer_name, ad_email_set, ad_name_map)
    return email if ok else ""

def _fmt_date_long(iso_str):
    if not iso_str or pd.isna(iso_str):
        return "Unknown Date"
    try:
        dt_str = str(iso_str).replace("Z", "").split(".")[0]
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%B %d, %Y")
    except Exception:
        return str(iso_str)

def _calc_due_date(iso_str, days=14):
    if not iso_str or pd.isna(iso_str):
        return "ASAP"
    try:
        dt_str = str(iso_str).replace("Z", "").split(".")[0]
        dt = datetime.fromisoformat(dt_str)
        return (dt + timedelta(days=days)).strftime("%B %d, %Y")
    except Exception:
        return "ASAP"

def _infer_section(file_date_raw):
    if not file_date_raw or pd.isna(file_date_raw):
        return "followup"
    try:
        dt_str = str(file_date_raw).replace("Z", "").split(".")[0]
        sent_dt = datetime.fromisoformat(dt_str)
        return "new" if (sent_dt + timedelta(days=14)) >= datetime.now() else "followup"
    except Exception:
        return "followup"

def _build_section_table(rows):
    table = "<table border='1' style='border-collapse:collapse; width:100%; font-size:12px; border:1px solid #ddd'>"
    table += "<tr style='background:#f3f3f3'><th>App Name</th><th>Sent Date</th><th>Due Date</th><th>Missing</th><th>Link</th></tr>"
    for row in rows:
        table += (
            "<tr>"
            f"<td style='padding:5px'>{row['App_Name']}</td>"
            f"<td style='padding:5px'>{row['sent_date']}</td>"
            f"<td style='padding:5px'>{row['due_date']}</td>"
            f"<td style='padding:5px; text-align:center'>{row['missing']}</td>"
            f"<td style='padding:5px'><a href='{row['folder_url']}'>Open</a></td>"
            "</tr>"
        )
    table += "</table>"
    return table

def _build_email_html(reviewer_name, new_rows, followup_rows):
    parts = [
        f"Hi {reviewer_name},<br><br>",
    ]
    if new_rows:
        parts.append("<b>1) New Applications to Review</b><br>")
        parts.append(_build_section_table(new_rows))
        parts.append("<br><br>")
    if followup_rows:
        parts.append("<b>2) Follow-up on Remaining Reviews</b><br>")
        parts.append(_build_section_table(followup_rows))
        parts.append("<br><br>")
    if not new_rows and not followup_rows:
        parts.append("No applications are selected for this update.<br><br>")
    parts.append("Please complete these reviews as soon as possible. Your prompt assistance is appreciated.<br><br>")
    # Configurable footer
    footer_html = AER_EMAIL_TEMPLATE_FOOTER.replace("\n", "<br>")
    parts.append(footer_html)
    return "".join(parts)


# ============================================
# DATA PREP
# ============================================

s7_status = widgets.HTML(value="<i>Preparing email data...</i>")
s7_output = widgets.Output()

s7_container = widgets.VBox()
s7_row_store = {}

s7_subject = widgets.Text(
    value=f"REMINDER - {AER_REVIEW_YEAR} Entitlement Review Update",
    description="<b>Subject:</b>",
    layout=widgets.Layout(width="98%"),
)
s7_cc = widgets.Textarea(
    value="", description="<b>Global CC:</b>",
    placeholder="manager@company.com, team@company.com",
    layout=widgets.Layout(width="98%", height="50px"),
)
s7_reply_to = widgets.Text(
    value="", description="<b>Reply-To:</b>",
    placeholder="security-team@company.com",
    layout=widgets.Layout(width="98%"),
)
s7_btn_refresh = widgets.Button(description="🔄 Refresh", button_style="info",
                                 layout=widgets.Layout(width="120px"))
s7_btn_send_all = widgets.Button(description="🔥 Send All (Batch)", button_style="danger",
                                  layout=widgets.Layout(width="200px"))


def _parse_email_list(raw):
    if not raw:
        return []
    return [p.strip() for p in re.split(r"[,\n;]+", str(raw)) if p and p.strip()]


def _render_email_rows(b=None):
    global s7_row_store
    s7_row_store = {}
    s7_container.children = (widgets.Label("Loading..."),)

    df = globals().get("r6_df")
    if df is None or df.empty:
        s7_container.children = (widgets.HTML("<h4>⚠️ No scan data. Run Stage 6 first.</h4>"),)
        return

    pending = df[df["is_missing"] == True].copy()
    if pending.empty:
        s7_container.children = (widgets.HTML("<h3>✅ No pending emails!</h3>"),)
        return

    targets = pending.groupby(["Category", "App_Name", "reviewer", "folder_url"]).agg(
        missing_count=("is_missing", "count"),
        file_date_raw=("File_Created_Date", "min"),
    ).reset_index()

    # Resolve emails using AD cache (not Graph API per reviewer!)
    ad_df, _, _ = load_ad_cache()
    ad_es, ad_nm = build_identity_index(ad_df) if ad_df is not None else (set(), {})
    email_cache = {}
    sent_log = load_json_safe(EMAIL_CHECKPOINT_FILE)

    raw_list = []
    for _, r in targets.iterrows():
        rev = r["reviewer"]
        if rev not in email_cache:
            email_cache[rev] = _email_lookup_from_ad(rev, ad_es, ad_nm)
        raw_list.append({
            "App_Name": r["App_Name"], "reviewer": rev,
            "missing": int(r["missing_count"]),
            "folder_url": r["folder_url"],
            "sent_date": _fmt_date_long(r["file_date_raw"]),
            "due_date": _calc_due_date(r["file_date_raw"]),
            "file_date_raw": r["file_date_raw"],
            "email": email_cache[rev],
        })

    df_raw = pd.DataFrame(raw_list).sort_values(["reviewer", "App_Name"]).reset_index(drop=True)
    ui_items = []

    for idx, ((reviewer, email), group) in enumerate(df_raw.groupby(["reviewer", "email"], dropna=False)):
        key = f"{reviewer}_{idx}"

        # Check if already sent
        already_sent = sent_log.get(key, {}).get("sent", False)

        email_color = "#0078d4" if email else "red"
        w_chk = widgets.Checkbox(value=not already_sent, layout=widgets.Layout(width="30px"))
        w_info = widgets.HTML(
            f"<b>👤 {reviewer}</b><br><span style='color:{email_color}'>{email or '(No Email)'}</span>"
            + (" ✅ Sent" if already_sent else ""),
            layout=widgets.Layout(width="260px"),
        )
        w_email = widgets.Text(value=email or "", placeholder="Email", layout=widgets.Layout(width="98%"))
        w_btn = widgets.Button(description="🚀 Send", button_style="warning" if not already_sent else "success",
                               layout=widgets.Layout(width="90px"))

        app_data = []
        for _, app_row in group.iterrows():
            section = _infer_section(app_row["file_date_raw"])
            app_data.append({
                "App_Name": app_row["App_Name"], "missing": int(app_row["missing"]),
                "folder_url": app_row["folder_url"], "sent_date": app_row["sent_date"],
                "due_date": app_row["due_date"], "section": section,
            })

        s7_row_store[key] = {
            "reviewer": reviewer, "w_chk": w_chk, "w_email": w_email, "w_btn": w_btn,
            "apps": app_data,
        }

        # Summary text
        new_count = sum(1 for a in app_data if a["section"] == "new")
        followup_count = len(app_data) - new_count
        summary = widgets.HTML(
            f"<span style='color:#0b6'>New: {new_count}</span> | "
            f"<span style='color:#b36b00'>Follow-up: {followup_count}</span>"
        )

        def make_sender(k):
            def _send(_):
                state = s7_row_store[k]
                to_email = state["w_email"].value.strip()
                if not to_email:
                    state["w_btn"].description = "No Email"
                    return
                state["w_btn"].disabled = True
                state["w_btn"].description = "..."
                try:
                    new_rows = [a for a in state["apps"] if a["section"] == "new"]
                    fu_rows = [a for a in state["apps"] if a["section"] == "followup"]
                    body = _build_email_html(state["reviewer"], new_rows, fu_rows)
                    subj = s7_subject.value

                    headers = token_mgr.get_headers("graph")
                    url = f"https://graph.microsoft.com/v1.0/users/{SENDER_EMAIL}/sendMail"
                    to_list = [{"emailAddress": {"address": to_email}}]
                    cc = [{"emailAddress": {"address": e}} for e in _parse_email_list(s7_cc.value)]
                    reply_to = [{"emailAddress": {"address": e}} for e in _parse_email_list(s7_reply_to.value)]
                    msg = {"subject": subj, "body": {"contentType": "HTML", "content": body}, "toRecipients": to_list}
                    if cc:
                        msg["ccRecipients"] = cc
                    if reply_to:
                        msg["replyTo"] = reply_to

                    resp = graph_post(url, headers, json_payload={"message": msg})
                    if resp.status_code == 202:
                        state["w_btn"].button_style = "success"
                        state["w_btn"].description = "Sent"
                        state["w_chk"].value = False
                        # Checkpoint
                        sl = load_json_safe(EMAIL_CHECKPOINT_FILE)
                        sl[k] = {"sent": True, "ts": datetime.now().isoformat(), "email": to_email}
                        atomic_json_save(EMAIL_CHECKPOINT_FILE, sl)
                    else:
                        state["w_btn"].button_style = "danger"
                        state["w_btn"].description = "Fail"
                        with s7_output:
                            print(f"Send failed for {state['reviewer']}: {resp.text[:200]}")
                except Exception as e:
                    state["w_btn"].button_style = "danger"
                    state["w_btn"].description = "Err"
                    with s7_output:
                        print(f"Error: {e}")
                finally:
                    if state["w_btn"].description != "Sent":
                        state["w_btn"].disabled = False
            return _send

        w_btn.on_click(make_sender(key))

        ui_items.append(widgets.VBox([
            widgets.HBox([w_chk, w_info, summary, w_email, w_btn],
                         layout=widgets.Layout(align_items="center")),
        ], layout=widgets.Layout(border="1px solid #ccc", margin="4px 0", padding="6px")))

    s7_container.children = tuple(ui_items)
    s7_status.value = f"<span style='color:green'>✅ {len(ui_items)} reviewers with pending items</span>"


def on_s7_send_all(_):
    s7_btn_send_all.disabled = True
    s7_btn_send_all.description = "Sending..."
    count = 0
    for k, state in s7_row_store.items():
        if state["w_chk"].value and state["w_btn"].description != "Sent":
            # Trigger individual send
            state["w_btn"].click()
            count += 1
            time.sleep(0.5)  # Small delay between sends
    s7_btn_send_all.disabled = False
    s7_btn_send_all.description = f"🔥 Done ({count})"

s7_btn_refresh.on_click(_render_email_rows)
s7_btn_send_all.on_click(on_s7_send_all)

_render_email_rows()


stage7_ui = widgets.VBox([
    widgets.HTML(f"""
        <div style='background: linear-gradient(135deg, #ff9a9e 0%, #fad0c4 100%);
            padding: 20px; border-radius: 8px; color: #333; margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
            <h2 style='margin: 0 0 10px 0;'>📧 Stage 7: Email Notification Center</h2>
            <p style='margin: 0; opacity: 0.85;'>
                Email lookup via AD cache (no per-reviewer API calls).
                Year: {AER_REVIEW_YEAR}. Checkpoint prevents double-send.
            </p>
        </div>
    """),
    s7_subject,
    s7_cc,
    s7_reply_to,
    widgets.HBox([s7_btn_refresh, s7_btn_send_all]),
    s7_status,
    s7_output,
    s7_container,
])

clear_output()
display(stage7_ui)
