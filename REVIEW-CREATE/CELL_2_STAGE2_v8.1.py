#!/usr/bin/env python3
"""
Stage 2: Email/User Validation with Compact Review UI (Jupyter Cell) v8.1

Short Description:
Compact non-100% match review table designed for 30+ manual updates.

Modified:
2026-02-12 11:36 -0500

Key Rules:
1. 100% perfect matches stay folded with summary only (no record list).
2. All non-100% records are displayed in one compact review table.
3. Candidate preselect is allowed only when top score >= 90.
4. Dropdown options include candidate AD status and last update status.
5. Unselected rows are still included in output as unresolved.

Copy and paste this entire cell into Jupyter notebook and run.
"""

import os
import sys
import re
import io
import glob
import unicodedata
from typing import Dict, List, Tuple
from datetime import datetime
import pandas as pd
import ipywidgets as widgets
from IPython.display import display, HTML, clear_output

# Try import fuzzy matching
try:
    from rapidfuzz import fuzz, process
    FUZZY_AVAILABLE = True
except ImportError:
    try:
        from fuzzywuzzy import fuzz, process
        FUZZY_AVAILABLE = True
    except ImportError:
        FUZZY_AVAILABLE = False
        print("⚠️ Fuzzy matching unavailable. Install: pip install rapidfuzz")

# ============================================
# Setup Paths
# ============================================

today_str = datetime.now().strftime('%Y-%m-%d')
BASE_DIR = os.path.join("output", today_str)
OUTPUT_AD_CACHE_DIR = os.path.join(BASE_DIR, "ad_cache")
INPUT_AD_CACHE_DIR = os.path.join("input", "ad_cache")
STAGE2_DIR = os.path.join(BASE_DIR, "stage2_validated")
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(STAGE2_DIR, exist_ok=True)

# ============================================
# Validation Status Enum
# ============================================

class ValidationStatus:
    """Validation status categories"""
    VALID_PERFECT = "valid_perfect"
    WARN_NAME_MISMATCH = "warn_name_mismatch"
    INFO_FUZZY_UNIQUE = "info_fuzzy_unique"
    ERR_FUZZY_MULTIPLE = "err_fuzzy_multiple"
    ERR_NOT_FOUND = "err_not_found"
    ERR_EMAIL_INVALID = "err_email_invalid"
    ERR_MISSING_DATA = "err_missing_data"

    @staticmethod
    def get_display_text(status: str) -> str:
        status_map = {
            ValidationStatus.VALID_PERFECT: "✅ Verified (Email & Name Match)",
            ValidationStatus.WARN_NAME_MISMATCH: "⚠️ Email Valid - Name Mismatch",
            ValidationStatus.INFO_FUZZY_UNIQUE: "🔵 Auto-Matched by Name (Single Match)",
            ValidationStatus.ERR_FUZZY_MULTIPLE: "🟠 Manual Selection Required (Multiple Matches)",
            ValidationStatus.ERR_NOT_FOUND: "❌ User Not Found in AD",
            ValidationStatus.ERR_EMAIL_INVALID: "❌ Email Not in AD",
            ValidationStatus.ERR_MISSING_DATA: "⚪ Insufficient Data"
        }
        return status_map.get(status, "Unknown Status")

# ============================================
# Global State
# ============================================

stage2_ad_cache = {}
stage2_name_index = {}
stage2_input_df = None
stage2_input_filename = ""
stage2_categorized = {}
stage2_ui_rows = {}

# ============================================
# Helper Functions
# ============================================

def is_email_valid(email) -> bool:
    """Check if email is valid"""
    if pd.isna(email):
        return False
    email_str = str(email).strip().lower()
    if email_str in ['', 'nan', 'none', 'n/a', 'na', '#n/a']:
        return False
    if '@' not in email_str or '.' not in email_str:
        return False
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email_str):
        return False
    return True


def normalize_name(name) -> str:
    """Normalize name for fuzzy matching"""
    if not name or pd.isna(name):
        return ""
    name = str(name).lower()
    name = unicodedata.normalize('NFKC', name)
    name = re.sub(r'[^a-z0-9\s]', ' ', name)
    name = ' '.join(name.split())
    return name.strip()


def fuzzy_match_name(target_name: str, name_index: Dict, ad_cache: Dict, top_n: int = 5) -> List[Dict]:
    """Find best email matches for a name"""
    if not FUZZY_AVAILABLE or not name_index:
        return []

    norm_target = normalize_name(target_name)
    if not norm_target:
        return []

    # Exact match check
    if norm_target in name_index:
        email = name_index[norm_target]
        user = ad_cache[email]
        return [{
            'email': email,
            'name': user['name'],
            'dept': user['dept'],
            'score': 100,
            'match_type': 'exact'
        }]

    # Fuzzy search
    try:
        candidates = list(name_index.keys())
        matches = process.extract(
            norm_target,
            candidates,
            scorer=fuzz.token_sort_ratio,
            limit=top_n * 2
        )

        results = []
        seen = set()

        for match_name, score, _ in matches:
            if score < 70:
                continue

            email = name_index[match_name]
            if email in seen:
                continue

            seen.add(email)
            user = ad_cache[email]

            results.append({
                'email': email,
                'name': user['name'],
                'dept': user['dept'],
                'score': int(score),
                'match_type': 'high' if score >= 90 else 'medium'
            })

            if len(results) >= top_n:
                break

        return results
    except:
        return []


def load_ad_cache():
    """Load AD cache from Stage 1"""
    global stage2_ad_cache, stage2_name_index

    try:
        cache_files = glob.glob(os.path.join(INPUT_AD_CACHE_DIR, "ad_users_*.csv"))
        if not cache_files:
            cache_files = glob.glob(os.path.join(OUTPUT_AD_CACHE_DIR, "ad_users_*.csv"))
        if not cache_files:
            return False, "No AD cache found. Please run Stage 1 first."

        latest_cache = max(cache_files, key=os.path.getmtime)
        df = pd.read_csv(latest_cache)

        # Build cache
        for _, row in df.iterrows():
            email = str(row['email']).lower().strip()
            if not email or email == 'nan':
                continue

            active_raw = row.get('accountEnabled', False)
            if isinstance(active_raw, str):
                active_raw = active_raw.strip().lower() in ['true', '1', 'yes', 'y']

            last_update = row.get('activeIn3Months', row.get('signInAgeRange', row.get('lastSignInDateTime', 'N/A')))
            if pd.isna(last_update):
                last_update = 'N/A'

            stage2_ad_cache[email] = {
                'email': email,
                'name': row.get('displayName', ''),
                'dept': row.get('department', ''),
                'active': bool(active_raw),
                'last_update_status': str(last_update)
            }

            # Build name index
            norm_name = normalize_name(row['displayName'])
            if norm_name:
                stage2_name_index[norm_name] = email

                # Add reversed name
                parts = norm_name.split()
                if len(parts) == 2:
                    reversed_name = f"{parts[1]} {parts[0]}"
                    stage2_name_index[reversed_name] = email

        return True, f"Loaded {len(stage2_ad_cache)} users from {os.path.basename(latest_cache)}"

    except Exception as e:
        return False, f"Error loading AD cache: {str(e)}"


def categorize_user(row: pd.Series, ad_cache: Dict, name_index: Dict) -> Tuple[str, Dict]:
    """Categorize a user record"""
    user_email = row.get('Email') if 'Email' in row.index else row.iloc[0]
    user_name = row.get('User Name') if 'User Name' in row.index else row.iloc[1] if len(row) > 1 else ''

    metadata = {
        'original_email': user_email,
        'original_name': user_name,
        'ad_user': None,
        'fuzzy_matches': [],
        'validation_message': '',
        'final_email': '',
        'final_name': ''
    }

    email_valid = is_email_valid(user_email)

    # Case 1: Both missing
    if not email_valid and (not user_name or pd.isna(user_name) or str(user_name).strip() == ''):
        metadata['validation_message'] = 'Insufficient data'
        return ValidationStatus.ERR_MISSING_DATA, metadata

    # Case 2: Email valid
    if email_valid:
        email_clean = str(user_email).strip().lower()

        if email_clean not in ad_cache:
            metadata['validation_message'] = f'Email not in AD'
            return ValidationStatus.ERR_EMAIL_INVALID, metadata

        ad_user = ad_cache[email_clean]
        metadata['ad_user'] = ad_user
        metadata['final_email'] = email_clean
        metadata['final_name'] = ad_user['name']

        # Check name match
        ad_name_norm = normalize_name(ad_user['name'])
        input_name_norm = normalize_name(user_name)

        if input_name_norm and ad_name_norm == input_name_norm:
            metadata['validation_message'] = 'Perfect match'
            return ValidationStatus.VALID_PERFECT, metadata
        else:
            metadata['validation_message'] = f"Name differs"
            return ValidationStatus.WARN_NAME_MISMATCH, metadata

    # Case 3: Email missing, try fuzzy match
    if not user_name or pd.isna(user_name) or str(user_name).strip() == '':
        metadata['validation_message'] = 'No name provided'
        return ValidationStatus.ERR_MISSING_DATA, metadata

    fuzzy_matches = fuzzy_match_name(user_name, name_index, ad_cache, top_n=5)

    if not fuzzy_matches:
        metadata['validation_message'] = 'No match found'
        return ValidationStatus.ERR_NOT_FOUND, metadata

    metadata['fuzzy_matches'] = fuzzy_matches

    if len(fuzzy_matches) == 1:
        match = fuzzy_matches[0]
        if match['score'] >= 80:
            # High confidence — auto-populate
            metadata['final_email'] = match['email']
            metadata['final_name'] = match['name']
            metadata['validation_message'] = f'Single match: {match["score"]}%'
            return ValidationStatus.INFO_FUZZY_UNIQUE, metadata
        else:
            # Low confidence — require manual selection
            metadata['validation_message'] = f'Low confidence: {match["score"]}%'
            return ValidationStatus.ERR_FUZZY_MULTIPLE, metadata
    else:
        metadata['validation_message'] = f'{len(fuzzy_matches)} matches found'
        return ValidationStatus.ERR_FUZZY_MULTIPLE, metadata


# ============================================
# UI Components
# ============================================

def _candidate_option_label(match: Dict) -> str:
    """Build compact dropdown label with AD status and last update."""
    ad = stage2_ad_cache.get(match['email'], {})
    ad_status = 'Active' if ad.get('active') else 'Disabled'
    last_update = ad.get('last_update_status', 'N/A')
    return (
        f"{match['name']} | {match['email']} | {match['dept']} | "
        f"Score {match['score']}% | AD:{ad_status} | Last:{last_update}"
    )


def create_compact_review_row(item: Dict, status: str) -> Dict:
    """Create a compact row for all non-100% review actions."""
    metadata = item['metadata']
    input_name = str(metadata.get('original_name', '') or '').strip() or '(blank)'
    input_email = str(metadata.get('original_email', '') or '').strip() or '(blank)'

    input_html = widgets.HTML(
        value=(
            "<div style='width:240px; line-height:1.3;'>"
            f"<div style='font-weight:600;'>{input_name}</div>"
            f"<div style='font-size:12px; color:#666;'>{input_email}</div>"
            "</div>"
        )
    )

    if status in [ValidationStatus.INFO_FUZZY_UNIQUE, ValidationStatus.ERR_FUZZY_MULTIPLE]:
        fuzzy_matches = metadata.get('fuzzy_matches', [])
        top_score = fuzzy_matches[0]['score'] if fuzzy_matches else 0

        options = [('-- Select Candidate --', '')]
        for match in fuzzy_matches:
            options.append((_candidate_option_label(match), match['email']))
        options.append(('-- Manual Entry --', 'MANUAL'))

        default_value = fuzzy_matches[0]['email'] if fuzzy_matches and top_score >= 90 else ''

        dropdown = widgets.Dropdown(
            options=options,
            value=default_value,
            layout=widgets.Layout(width='760px', height='36px')
        )

        txt_manual = widgets.Text(
            placeholder='Enter email manually',
            layout=widgets.Layout(width='300px', height='36px'),
            disabled=True
        )

        status_text = (
            f"Top {top_score}% | {'Preselected' if default_value else 'Manual Select'}"
            if fuzzy_matches else 'No candidate'
        )
        status_html = widgets.HTML(
            value=f"<div style='width:180px; font-size:12px; line-height:1.3; color:#b26a00;'>{status_text}</div>"
        )

        def on_dropdown_change(change):
            if change['new'] == 'MANUAL':
                txt_manual.disabled = False
            else:
                txt_manual.disabled = True
                txt_manual.value = ''

        dropdown.observe(on_dropdown_change, names='value')

        btn_delete = widgets.Button(
            description='✕',
            button_style='danger',
            layout=widgets.Layout(width='34px', height='32px'),
            tooltip='Remove this record'
        )

        row_widget = widgets.HBox([
            input_html,
            status_html,
            dropdown,
            txt_manual,
            btn_delete
        ], layout=widgets.Layout(align_items='center', min_height='48px', padding='4px 0'))

        result = {
            'row_type': 'candidate',
            'source_status': status,
            'item': item,
            'metadata': metadata,
            'dropdown': dropdown,
            'manual_input': txt_manual,
            'row': row_widget,
            'deleted': False
        }

    elif status == ValidationStatus.WARN_NAME_MISMATCH:
        ad_user = metadata.get('ad_user', {})
        ad_name = ad_user.get('name', '(N/A)')
        ad_email = metadata.get('final_email', '(N/A)')

        decision = widgets.Dropdown(
            options=[
                ('Use AD Name', 'AD_NAME'),
                ('Keep Input Name', 'INPUT_NAME')
            ],
            value='AD_NAME',
            layout=widgets.Layout(width='360px', height='36px')
        )

        status_html = widgets.HTML(
            value=(
                "<div style='width:180px; font-size:12px; color:#b26a00;'>"
                "Email verified, name mismatch"
                "</div>"
            )
        )

        info_html = widgets.HTML(
            value=(
                "<div style='width:680px; font-size:12px; line-height:1.3;'>"
                f"AD: <b>{ad_name}</b> ({ad_email})"
                "</div>"
            )
        )

        btn_delete = widgets.Button(
            description='✕',
            button_style='danger',
            layout=widgets.Layout(width='34px', height='32px'),
            tooltip='Remove this record'
        )

        row_widget = widgets.HBox([
            input_html,
            status_html,
            decision,
            info_html,
            btn_delete
        ], layout=widgets.Layout(align_items='center', min_height='48px', padding='4px 0'))

        result = {
            'row_type': 'mismatch',
            'source_status': status,
            'item': item,
            'metadata': metadata,
            'decision': decision,
            'row': row_widget,
            'deleted': False
        }

    else:
        raise ValueError(f'Unsupported review row status: {status}')

    def on_delete(_):
        result['deleted'] = True
        result['row'].layout.display = 'none'

    btn_delete.on_click(on_delete)
    return result


def build_compact_review_section(review_rows: List[Dict]) -> widgets.VBox:
    """Build compact scrollable section for all non-100% review rows."""
    header = widgets.HTML(
        value=(
            "<div style='display:flex; gap:10px; font-weight:700; padding:6px 8px; "
            "background:#f5f6f8; border:1px solid #ddd; border-bottom:none;'>"
            "<div style='width:240px;'>Input</div>"
            "<div style='width:180px;'>Review Hint</div>"
            "<div style='width:760px;'>Selection (preselect only if >=90)</div>"
            "<div style='width:300px;'>Manual / Note</div>"
            "<div style='width:34px;'>Del</div>"
            "</div>"
        )
    )

    rows_box = widgets.VBox(
        [r['row'] for r in review_rows],
        layout=widgets.Layout(
            border='1px solid #ddd',
            max_height='560px',
            overflow='auto',
            padding='6px'
        )
    )

    return widgets.VBox([header, rows_box])


# ============================================
# Main Validation Function
# ============================================

def do_validation(b):
    """Validate uploaded file and build compact review UI."""
    global stage2_input_df, stage2_input_filename, stage2_categorized, stage2_ui_rows

    s2_output.clear_output()

    if not s2_upload.value:
        with s2_output:
            print("❌ Please upload a file")
        return

    b.disabled = True

    try:
        with s2_output:
            print()
            print("=" * 60)
            print("🔍 Stage 2: Email/User Validation")
            print("=" * 60)
            print()

        f_item = s2_upload.value[0]
        stage2_input_filename = f_item['name']

        if stage2_input_filename.endswith('.csv'):
            stage2_input_df = pd.read_csv(io.BytesIO(f_item['content']))
        else:
            stage2_input_df = pd.read_excel(io.BytesIO(f_item['content']))

        with s2_output:
            print(f"📄 Loaded: {stage2_input_filename}")
            print(f"   Rows: {len(stage2_input_df)}")
            print(f"   Columns: {list(stage2_input_df.columns)}")
            print()

        stage2_categorized = {}
        total_rows = len(stage2_input_df)
        progress = widgets.IntProgress(
            value=0,
            min=0,
            max=max(total_rows, 1),
            description='Processing:',
            bar_style='info',
            layout=widgets.Layout(width='680px')
        )
        progress_text = widgets.HTML(
            value=f"<span style='font-size:12px; color:#555;'>0 / {total_rows} (0%)</span>"
        )
        started_at = datetime.now()

        with s2_output:
            display(widgets.VBox([progress, progress_text]))

        update_every = 20 if total_rows >= 1000 else 10 if total_rows >= 300 else 5

        for i, (idx, row) in enumerate(stage2_input_df.iterrows(), start=1):
            status, metadata = categorize_user(row, stage2_ad_cache, stage2_name_index)
            stage2_categorized.setdefault(status, []).append({
                'index': idx,
                'row': row,
                'metadata': metadata,
                'status': status
            })

            if i == 1 or i == total_rows or i % update_every == 0:
                progress.value = i
                pct = int((i / total_rows) * 100) if total_rows else 100
                progress_text.value = (
                    f"<span style='font-size:12px; color:#555;'>"
                    f"{i} / {total_rows} ({pct}%)"
                    f"</span>"
                )

        elapsed_sec = (datetime.now() - started_at).total_seconds()
        progress.value = total_rows if total_rows else 1
        progress.bar_style = 'success'
        progress.description = 'Done:'
        done_pct = 100 if total_rows else 0
        progress_text.value = (
            f"<span style='font-size:12px; color:#1b5e20;'>"
            f"{total_rows} / {total_rows} ({done_pct}%) - Completed in {elapsed_sec:.1f}s"
            f"</span>"
        )

        stats = {status: len(stage2_categorized.get(status, [])) for status in [
            ValidationStatus.VALID_PERFECT,
            ValidationStatus.WARN_NAME_MISMATCH,
            ValidationStatus.INFO_FUZZY_UNIQUE,
            ValidationStatus.ERR_FUZZY_MULTIPLE,
            ValidationStatus.ERR_NOT_FOUND,
            ValidationStatus.ERR_EMAIL_INVALID,
            ValidationStatus.ERR_MISSING_DATA
        ]}

        candidate_items = (
            stage2_categorized.get(ValidationStatus.INFO_FUZZY_UNIQUE, []) +
            stage2_categorized.get(ValidationStatus.ERR_FUZZY_MULTIPLE, [])
        )
        preselect_90 = sum(
            1 for it in candidate_items
            if it['metadata'].get('fuzzy_matches') and it['metadata']['fuzzy_matches'][0].get('score', 0) >= 90
        )

        group_counts = {
            'G0_AUTO_100': stats[ValidationStatus.VALID_PERFECT],
            'G1_REVIEW_90_PLUS': preselect_90,
            'G2_REVIEW_70_89': max(0, len(candidate_items) - preselect_90),
            'G3_REVIEW_NAME_MISMATCH': stats[ValidationStatus.WARN_NAME_MISMATCH],
            'G4_REVIEW_NO_MATCH': stats[ValidationStatus.ERR_NOT_FOUND] + stats[ValidationStatus.ERR_EMAIL_INVALID],
            'G5_REVIEW_MISSING_INPUT': stats[ValidationStatus.ERR_MISSING_DATA],
        }

        with s2_output:
            print("📊 Group Summary:")
            for key, val in group_counts.items():
                print(f"   {key}: {val}")
            print(f"   TOTAL: {len(stage2_input_df)}")
            print()

        ui_sections = []
        stage2_ui_rows = {'review_rows': []}

        summary_html = f"""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 16px; border-radius: 8px; color: white; margin-bottom: 16px;'>
            <h2 style='margin: 0 0 8px 0;'>🔍 Validation Groups (Compact Mode)</h2>
            <div style='display:grid; grid-template-columns:repeat(3, 1fr); gap:10px; font-size:13px;'>
                <div>G0 Auto 100%: <b>{group_counts['G0_AUTO_100']}</b></div>
                <div>G1 Review 90%+: <b>{group_counts['G1_REVIEW_90_PLUS']}</b></div>
                <div>G2 Review 70-89%: <b>{group_counts['G2_REVIEW_70_89']}</b></div>
                <div>G3 Name Mismatch: <b>{group_counts['G3_REVIEW_NAME_MISMATCH']}</b></div>
                <div>G4 No Match: <b>{group_counts['G4_REVIEW_NO_MATCH']}</b></div>
                <div>G5 Missing Input: <b>{group_counts['G5_REVIEW_MISSING_INPUT']}</b></div>
            </div>
        </div>
        """
        ui_sections.append(widgets.HTML(value=summary_html))

        if group_counts['G0_AUTO_100'] > 0:
            summary_only_html = (
                "<div style='padding:10px 12px; font-size:13px; color:#2e7d32; "
                "background:#f1f8e9; border:1px solid #c8e6c9; border-radius:6px;'>"
                f"✅ {group_counts['G0_AUTO_100']} perfect-match records are auto-resolved and hidden."
                "<br>These records are still included in the final output file."
                "</div>"
            )
            acc = widgets.Accordion(children=[widgets.HTML(value=summary_only_html)])
            acc.set_title(0, f"✅ Perfect Match ({group_counts['G0_AUTO_100']} records — hidden)")
            acc.selected_index = None
            ui_sections.append(acc)

        for status in [
            ValidationStatus.INFO_FUZZY_UNIQUE,
            ValidationStatus.ERR_FUZZY_MULTIPLE,
            ValidationStatus.WARN_NAME_MISMATCH,
        ]:
            for item in stage2_categorized.get(status, []):
                stage2_ui_rows['review_rows'].append(create_compact_review_row(item, status))

        if stage2_ui_rows['review_rows']:
            ui_sections.append(widgets.HTML(value="""
                <h3 style='margin:16px 0 8px 0; color:#333;'>🧩 Non-100% Review Table (Compact)</h3>
                <div style='font-size:12px; color:#666; margin-bottom:8px;'>
                    Preselect policy: only top score >= 90. Unselected rows will still be exported as unresolved.
                </div>
            """))
            ui_sections.append(build_compact_review_section(stage2_ui_rows['review_rows']))

        info_html = f"""
        <div style='margin-top:16px; font-size:13px; color:#444;'>
            <b>Auto-export unresolved buckets:</b>
            Not Found={stats[ValidationStatus.ERR_NOT_FOUND]},
            Email Invalid={stats[ValidationStatus.ERR_EMAIL_INVALID]},
            Missing Data={stats[ValidationStatus.ERR_MISSING_DATA]}
        </div>
        """
        ui_sections.append(widgets.HTML(value=info_html))

        ui_sections.append(widgets.HTML(value="<hr style='margin: 20px 0;'>"))
        ui_sections.append(widgets.HBox([s2_btn_save]))

        with s2_output:
            display(widgets.VBox(ui_sections))

        s2_btn_save.disabled = False
        s2_status.value = "<span style='color:green;'>✅ Validation complete</span>"

    except Exception as e:
        with s2_output:
            print()
            print(f"❌ Error: {str(e)}")
        s2_status.value = f"<span style='color:red;'>❌ Error: {str(e)}</span>"
    finally:
        b.disabled = False


# ============================================
# Save Function
# ============================================

def do_save(b):
    """Save validated file with unresolved rows included."""
    if stage2_input_df is None:
        print("❌ No data to save")
        return

    b.disabled = True

    try:
        print()
        print("💾 Saving validated file...")

        validated_rows = []
        skipped_count = 0
        deleted_count = 0

        def _ad_fields(email_key):
            if email_key and email_key in stage2_ad_cache:
                ad = stage2_ad_cache[email_key]
                return ad.get('dept', ''), 'Yes' if ad.get('active') else 'No'
            return '', ''

        for item in stage2_categorized.get(ValidationStatus.VALID_PERFECT, []):
            row_data = item['row'].to_dict()
            metadata = item['metadata']
            row_data['Email'] = metadata['final_email']
            row_data['User Name'] = metadata['final_name']
            row_data['Department'], row_data['is_AD_active'] = _ad_fields(metadata['final_email'])
            row_data['Validation Status'] = ValidationStatus.get_display_text(ValidationStatus.VALID_PERFECT)
            validated_rows.append(row_data)

        for row_ui in stage2_ui_rows.get('review_rows', []):
            if row_ui.get('deleted'):
                deleted_count += 1
                continue

            item = row_ui['item']
            row_data = item['row'].to_dict()
            metadata = row_ui['metadata']

            if row_ui['row_type'] == 'candidate':
                selected = row_ui['dropdown'].value
                is_manual = (selected == 'MANUAL')

                if is_manual:
                    selected_email = row_ui['manual_input'].value.strip().lower()
                else:
                    selected_email = str(selected or '').strip().lower()

                if selected_email:
                    matched = None
                    for m in metadata.get('fuzzy_matches', []):
                        if m['email'] == selected_email:
                            matched = m
                            break

                    row_data['Email'] = selected_email

                    if matched:
                        row_data['User Name'] = matched['name']
                    elif selected_email in stage2_ad_cache:
                        row_data['User Name'] = stage2_ad_cache[selected_email]['name']

                    row_data['Department'], row_data['is_AD_active'] = _ad_fields(selected_email)

                    if is_manual:
                        row_data['Validation Status'] = "🔧 Manually Resolved"
                    else:
                        if row_ui['source_status'] == ValidationStatus.INFO_FUZZY_UNIQUE:
                            row_data['Validation Status'] = "✅ Candidate Selected (90% preselect policy)"
                        else:
                            row_data['Validation Status'] = ValidationStatus.get_display_text(ValidationStatus.ERR_FUZZY_MULTIPLE)
                else:
                    row_data['Department'] = ''
                    row_data['is_AD_active'] = ''
                    row_data['Validation Status'] = "⚠️ Unresolved (No Selection Made)"
                    skipped_count += 1

                validated_rows.append(row_data)

            elif row_ui['row_type'] == 'mismatch':
                decision = row_ui['decision'].value
                row_data['Email'] = metadata['final_email']

                if decision == 'AD_NAME':
                    row_data['User Name'] = metadata['final_name']
                    row_data['Validation Status'] = "✅ Name Mismatch Resolved (AD Name)"
                else:
                    row_data['User Name'] = metadata['original_name']
                    row_data['Validation Status'] = "⚠️ Name Mismatch (Kept Original)"

                row_data['Department'], row_data['is_AD_active'] = _ad_fields(metadata['final_email'])
                validated_rows.append(row_data)

        for status in [ValidationStatus.ERR_NOT_FOUND, ValidationStatus.ERR_EMAIL_INVALID, ValidationStatus.ERR_MISSING_DATA]:
            for item in stage2_categorized.get(status, []):
                row_data = item['row'].to_dict()
                row_data['Department'] = ''
                row_data['is_AD_active'] = ''
                row_data['Validation Status'] = ValidationStatus.get_display_text(status)
                validated_rows.append(row_data)

        if skipped_count > 0:
            print(f"⚠️  {skipped_count} rows had no selection — marked as unresolved")
        if deleted_count > 0:
            print(f"🗑️  {deleted_count} rows deleted by user — excluded from output")

        output_df = pd.DataFrame(validated_rows)
        priority_cols = ['Validation Status', 'Email', 'User Name', 'Department', 'is_AD_active']
        other_cols = [c for c in output_df.columns if c not in priority_cols]
        cols = [c for c in priority_cols + other_cols if c in output_df.columns]
        output_df = output_df[cols]

        base_name = stage2_input_filename.replace('.csv', '').replace('.xlsx', '')
        date_str = datetime.now().strftime('%Y%m%d')
        output_filename = f"{base_name}_validated_{date_str}.xlsx"
        output_path = os.path.join(STAGE2_DIR, output_filename)

        output_df.to_excel(output_path, index=False, sheet_name='Validated')

        print()
        print(f"✅ Saved: {output_path}")
        print(f"   Rows: {len(output_df)}")
        print(f"   Columns: {list(output_df.columns)}")

        s2_status.value = f"<span style='color:blue;'>✅ Saved: {output_filename}</span>"

    except Exception as e:
        print()
        print(f"❌ Save error: {str(e)}")
        s2_status.value = f"<span style='color:red;'>❌ Error: {str(e)}</span>"
    finally:
        b.disabled = False


# ============================================
# UI Setup
# ============================================

s2_upload = widgets.FileUpload(
    accept='.xlsx, .csv',
    description="Upload File",
    button_style='info'
)
s2_upload_status = widgets.HTML(value="<i>No file selected</i>")
s2_btn_validate = widgets.Button(
    description="🔍 Validate",
    button_style='warning',
    layout=widgets.Layout(width='140px', height='40px'),
    disabled=True
)
s2_btn_save = widgets.Button(
    description="💾 Save",
    button_style='success',
    layout=widgets.Layout(width='140px', height='40px'),
    disabled=True
)
s2_status = widgets.HTML(value="<i>Loading AD cache...</i>")
s2_output = widgets.Output()

# Event handlers
def on_upload_change(change):
    if s2_upload.value:
        fname = s2_upload.value[0]['name']
        s2_upload_status.value = f"<b style='color:green;'>✅ {fname}</b>"
        s2_btn_validate.disabled = False

s2_upload.observe(on_upload_change, 'value')
s2_btn_validate.on_click(do_validation)
s2_btn_save.on_click(do_save)

# Initialize
success, msg = load_ad_cache()
if success:
    s2_status.value = f"<span style='color:green;'>✅ {msg}</span>"
else:
    s2_status.value = f"<span style='color:red;'>⚠️ {msg}</span>"

# Main UI
stage2_ui = widgets.VBox([
    widgets.HTML("""
        <div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                    padding: 20px; border-radius: 8px; color: white; margin-bottom: 20px;'>
            <h2 style='margin: 0 0 10px 0;'>🔍 Stage 2: Email/User Validation</h2>
            <p style='margin: 0;'>Upload user list, validate against AD, resolve mismatches</p>
        </div>
    """),
    widgets.HBox([s2_upload, s2_upload_status]),
    widgets.HBox([s2_btn_validate, s2_btn_save]),
    s2_status,
    s2_output
])

clear_output()
display(stage2_ui)

print("="*60)
print("Stage 2 UI Ready")
print("="*60)
