#!/usr/bin/env python3
"""
Stage 2: Email/User Validation with Enhanced UI (Jupyter Cell)

Complete Jupyter notebook cell with:
1. Load AD cache from Stage 1
2. Upload user list file
3. Validate with comprehensive status tracking
4. Interactive UI (hide 100% matches, color-code others)
5. Save validated file with status column

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
AD_CACHE_DIR = os.path.join(BASE_DIR, "ad_cache")
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
        cache_files = glob.glob(os.path.join(AD_CACHE_DIR, "ad_users_*.csv"))
        if not cache_files:
            return False, "No AD cache found. Please run Stage 1 first."

        latest_cache = max(cache_files, key=os.path.getmtime)
        df = pd.read_csv(latest_cache)

        # Build cache
        for _, row in df.iterrows():
            email = str(row['email']).lower().strip()
            if not email or email == 'nan':
                continue

            stage2_ad_cache[email] = {
                'email': email,
                'name': row['displayName'],
                'dept': row['department'],
                'active': row['accountEnabled']
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
        metadata['final_email'] = match['email']
        metadata['final_name'] = match['name']
        metadata['validation_message'] = f'Single match: {match["score"]}%'
        return ValidationStatus.INFO_FUZZY_UNIQUE, metadata
    else:
        metadata['validation_message'] = f'{len(fuzzy_matches)} matches found'
        return ValidationStatus.ERR_FUZZY_MULTIPLE, metadata


# ============================================
# UI Components
# ============================================

def create_fuzzy_unique_row(idx: int, row: pd.Series, metadata: Dict):
    """Green row for single fuzzy match"""
    original_name = str(metadata['original_name'])
    match = metadata['fuzzy_matches'][0]

    name_html = f"""
    <div style='width:220px; padding:5px;'>
        <b style='color:#34c759;'>✓ {original_name}</b>
        <br><small style='color:#34c759;'>Match: {match['score']}%</small>
    </div>
    """

    info_html = f"""
    <div style='padding:5px; border:1px solid #34c759; background:#e8f5e9; border-radius:4px; width:500px;'>
        <b style='color:#34c759;'>✅ Single Match</b><br>
        <b>{match['name']}</b> ({match['email']})<br>
        Dept: {match['dept']} | Confidence: {match['score']}%
    </div>
    """

    return {
        'index': idx,
        'row': widgets.HBox([
            widgets.HTML(value=name_html),
            widgets.HTML(value=info_html)
        ]),
        'selected_email': match['email'],
        'selected_name': match['name']
    }


def create_fuzzy_multiple_row(idx: int, row: pd.Series, metadata: Dict):
    """Orange row for multiple fuzzy matches"""
    original_name = str(metadata['original_name'])
    fuzzy_matches = metadata['fuzzy_matches']

    name_html = f"""
    <div style='width:220px; padding:5px;'>
        <b style='color:#ff9500;'>⚠️ {original_name}</b>
        <br><small style='color:#ff9500;'>{len(fuzzy_matches)} matches</small>
    </div>
    """

    options = [('-- Select --', '')]
    for match in fuzzy_matches:
        label = f"{match['name']} ({match['email']}) - {match['dept']} [{match['score']}%]"
        options.append((label, match['email']))
    options.append(('-- Manual Entry --', 'MANUAL'))

    dropdown = widgets.Dropdown(
        options=options,
        value=fuzzy_matches[0]['email'],
        description='',
        layout=widgets.Layout(width='550px')
    )

    txt_manual = widgets.Text(
        placeholder='Enter email manually',
        layout=widgets.Layout(width='300px'),
        disabled=True
    )

    def on_dropdown_change(change):
        if change['new'] == 'MANUAL':
            txt_manual.disabled = False
        else:
            txt_manual.disabled = True
            txt_manual.value = ''

    dropdown.observe(on_dropdown_change, names='value')

    return {
        'index': idx,
        'dropdown': dropdown,
        'manual_input': txt_manual,
        'metadata': metadata,
        'row': widgets.HBox([
            widgets.HTML(value=name_html),
            dropdown,
            txt_manual
        ])
    }


def create_mismatch_row(idx: int, row: pd.Series, metadata: Dict):
    """Yellow row for name mismatch"""
    original_email = metadata['original_email']
    original_name = metadata['original_name']
    ad_user = metadata['ad_user']

    chk_accept = widgets.Checkbox(
        value=True,
        description='Accept AD Name',
        indent=False
    )

    info_html = f"""
    <div style='padding:5px; border:1px solid #ff9800; background:#fff3e0; border-radius:4px;'>
        <b style='color:#ff9800;'>⚠️ Name Mismatch</b><br>
        Input: {original_name}<br>
        AD: {ad_user['name']}<br>
        Email: {original_email} ✅
    </div>
    """

    return {
        'index': idx,
        'accept_checkbox': chk_accept,
        'metadata': metadata,
        'row': widgets.HBox([
            chk_accept,
            widgets.HTML(value=info_html)
        ])
    }


# ============================================
# Main Validation Function
# ============================================

def do_validation(b):
    """Validate uploaded file"""
    global stage2_input_df, stage2_input_filename, stage2_categorized, stage2_ui_rows

    s2_output.clear_output()

    if not s2_upload.value:
        with s2_output:
            print("❌ Please upload a file")
        return

    b.disabled = True

    try:
        with s2_output:
            print("\n" + "="*60)
            print("🔍 Stage 2: Email/User Validation")
            print("="*60 + "\n")

        # Load file
        f_item = s2_upload.value[0]
        stage2_input_filename = f_item['name']

        if stage2_input_filename.endswith('.csv'):
            stage2_input_df = pd.read_csv(io.BytesIO(f_item['content']))
        else:
            stage2_input_df = pd.read_excel(io.BytesIO(f_item['content']))

        with s2_output:
            print(f"📄 Loaded: {stage2_input_filename}")
            print(f"   Rows: {len(stage2_input_df)}")
            print(f"   Columns: {list(stage2_input_df.columns)}\n")

        # Categorize users
        print("🔍 Categorizing users...")
        stage2_categorized = {}

        for idx, row in stage2_input_df.iterrows():
            status, metadata = categorize_user(row, stage2_ad_cache, stage2_name_index)

            if status not in stage2_categorized:
                stage2_categorized[status] = []

            stage2_categorized[status].append({
                'index': idx,
                'row': row,
                'metadata': metadata,
                'status': status
            })

        # Statistics
        stats = {status: len(stage2_categorized.get(status, [])) for status in [
            ValidationStatus.VALID_PERFECT,
            ValidationStatus.WARN_NAME_MISMATCH,
            ValidationStatus.INFO_FUZZY_UNIQUE,
            ValidationStatus.ERR_FUZZY_MULTIPLE,
            ValidationStatus.ERR_NOT_FOUND,
            ValidationStatus.ERR_EMAIL_INVALID,
            ValidationStatus.ERR_MISSING_DATA
        ]}

        with s2_output:
            print(f"\n📊 Validation Statistics:")
            print(f"   ✅ Perfect Match (hidden):     {stats[ValidationStatus.VALID_PERFECT]}")
            print(f"   🔵 Single Fuzzy:               {stats[ValidationStatus.INFO_FUZZY_UNIQUE]}")
            print(f"   ⚠️  Name Mismatch:              {stats[ValidationStatus.WARN_NAME_MISMATCH]}")
            print(f"   🟠 Multiple Matches:           {stats[ValidationStatus.ERR_FUZZY_MULTIPLE]}")
            print(f"   ❌ Not Found (hidden):         {stats[ValidationStatus.ERR_NOT_FOUND]}")
            print(f"   ❌ Email Invalid (hidden):     {stats[ValidationStatus.ERR_EMAIL_INVALID]}")
            print(f"   ⚪ Missing Data (hidden):      {stats[ValidationStatus.ERR_MISSING_DATA]}")
            print(f"   📌 Total:                      {len(stage2_input_df)}\n")

        # Build UI
        ui_sections = []
        stage2_ui_rows = {
            'fuzzy_unique': [],
            'fuzzy_multiple': [],
            'mismatch': []
        }

        # Summary
        summary_html = f"""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 20px; border-radius: 8px; color: white; margin-bottom: 20px;'>
            <h2 style='margin: 0 0 10px 0;'>🔍 Validation Results</h2>
            <div style='display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px;'>
                <div style='background: rgba(255,255,255,0.2); padding: 10px; border-radius: 5px; text-align: center;'>
                    <div style='font-size: 24px; font-weight: bold;'>{stats[ValidationStatus.VALID_PERFECT]}</div>
                    <div>✅ Perfect (Auto)</div>
                </div>
                <div style='background: rgba(52,199,89,0.3); padding: 10px; border-radius: 5px; text-align: center;'>
                    <div style='font-size: 24px; font-weight: bold;'>{stats[ValidationStatus.INFO_FUZZY_UNIQUE]}</div>
                    <div>🔵 Single</div>
                </div>
                <div style='background: rgba(255,149,0,0.3); padding: 10px; border-radius: 5px; text-align: center;'>
                    <div style='font-size: 24px; font-weight: bold;'>{stats[ValidationStatus.ERR_FUZZY_MULTIPLE]}</div>
                    <div>🟠 Multiple</div>
                </div>
                <div style='background: rgba(255,152,0,0.3); padding: 10px; border-radius: 5px; text-align: center;'>
                    <div style='font-size: 24px; font-weight: bold;'>{stats[ValidationStatus.WARN_NAME_MISMATCH]}</div>
                    <div>⚠️ Mismatch</div>
                </div>
            </div>
        </div>
        """
        ui_sections.append(widgets.HTML(value=summary_html))

        # Single fuzzy matches
        if stats[ValidationStatus.INFO_FUZZY_UNIQUE] > 0:
            ui_sections.append(widgets.HTML(value="""
                <h3 style='color: #34c759; border-bottom: 2px solid #34c759; padding-bottom: 5px;'>
                    🔵 Single Match (Auto-Selected)
                </h3>
            """))

            for item in stage2_categorized.get(ValidationStatus.INFO_FUZZY_UNIQUE, []):
                row_ui = create_fuzzy_unique_row(item['index'], item['row'], item['metadata'])
                stage2_ui_rows['fuzzy_unique'].append(row_ui)
                ui_sections.append(row_ui['row'])

        # Multiple fuzzy matches
        if stats[ValidationStatus.ERR_FUZZY_MULTIPLE] > 0:
            ui_sections.append(widgets.HTML(value="""
                <h3 style='color: #ff9500; border-bottom: 2px solid #ff9500; padding-bottom: 5px; margin-top: 30px;'>
                    🟠 Multiple Matches - Select One
                </h3>
            """))

            for item in stage2_categorized.get(ValidationStatus.ERR_FUZZY_MULTIPLE, []):
                row_ui = create_fuzzy_multiple_row(item['index'], item['row'], item['metadata'])
                stage2_ui_rows['fuzzy_multiple'].append(row_ui)
                ui_sections.append(row_ui['row'])

        # Name mismatches
        if stats[ValidationStatus.WARN_NAME_MISMATCH] > 0:
            ui_sections.append(widgets.HTML(value="""
                <h3 style='color: #ff9800; border-bottom: 2px solid #ff9800; padding-bottom: 5px; margin-top: 30px;'>
                    ⚠️ Name Mismatch - Review
                </h3>
            """))

            for item in stage2_categorized.get(ValidationStatus.WARN_NAME_MISMATCH, []):
                row_ui = create_mismatch_row(item['index'], item['row'], item['metadata'])
                stage2_ui_rows['mismatch'].append(row_ui)
                ui_sections.append(row_ui['row'])

        # Save button
        ui_sections.append(widgets.HTML(value="<hr style='margin: 30px 0;'>"))
        ui_sections.append(widgets.HBox([s2_btn_save]))

        # Display UI
        with s2_output:
            display(widgets.VBox(ui_sections))

        s2_btn_save.disabled = False
        s2_status.value = f"<span style='color:green;'>✅ Validation complete</span>"

    except Exception as e:
        with s2_output:
            print(f"\n❌ Error: {str(e)}")
        s2_status.value = f"<span style='color:red;'>❌ Error: {str(e)}</span>"
    finally:
        b.disabled = False


# ============================================
# Save Function
# ============================================

def do_save(b):
    """Save validated file"""
    if stage2_input_df is None:
        print("❌ No data to save")
        return

    b.disabled = True

    try:
        print("\n💾 Saving validated file...")

        validated_rows = []

        # 1. Perfect matches (hidden)
        for item in stage2_categorized.get(ValidationStatus.VALID_PERFECT, []):
            row_data = item['row'].to_dict()
            metadata = item['metadata']
            row_data['Email'] = metadata['final_email']
            row_data['User Name'] = metadata['final_name']
            row_data['Validation Status'] = ValidationStatus.get_display_text(ValidationStatus.VALID_PERFECT)
            validated_rows.append(row_data)

        # 2. Single fuzzy matches
        for row_ui in stage2_ui_rows['fuzzy_unique']:
            item = stage2_categorized[ValidationStatus.INFO_FUZZY_UNIQUE][stage2_ui_rows['fuzzy_unique'].index(row_ui)]
            row_data = item['row'].to_dict()
            row_data['Email'] = row_ui['selected_email']
            row_data['User Name'] = row_ui['selected_name']
            row_data['Validation Status'] = ValidationStatus.get_display_text(ValidationStatus.INFO_FUZZY_UNIQUE)
            validated_rows.append(row_data)

        # 3. Multiple fuzzy matches
        for row_ui in stage2_ui_rows['fuzzy_multiple']:
            item = stage2_categorized[ValidationStatus.ERR_FUZZY_MULTIPLE][stage2_ui_rows['fuzzy_multiple'].index(row_ui)]
            row_data = item['row'].to_dict()

            selected = row_ui['dropdown'].value
            is_manual = (selected == 'MANUAL')

            if is_manual:
                selected = row_ui['manual_input'].value.strip().lower()

            if selected:
                found = False
                for match in row_ui['metadata']['fuzzy_matches']:
                    if match['email'] == selected:
                        row_data['Email'] = match['email']
                        row_data['User Name'] = match['name']
                        found = True
                        break

                if is_manual and not found:
                    row_data['Email'] = selected
                    if selected in stage2_ad_cache:
                        row_data['User Name'] = stage2_ad_cache[selected]['name']

                row_data['Validation Status'] = "🔧 Manually Resolved" if is_manual else ValidationStatus.get_display_text(ValidationStatus.ERR_FUZZY_MULTIPLE)
                validated_rows.append(row_data)

        # 4. Name mismatches
        for row_ui in stage2_ui_rows['mismatch']:
            item = stage2_categorized[ValidationStatus.WARN_NAME_MISMATCH][stage2_ui_rows['mismatch'].index(row_ui)]
            row_data = item['row'].to_dict()
            metadata = row_ui['metadata']

            if row_ui['accept_checkbox'].value:
                row_data['Email'] = metadata['final_email']
                row_data['User Name'] = metadata['final_name']
                row_data['Validation Status'] = "✅ Name Mismatch Resolved (AD Name)"
            else:
                row_data['Email'] = metadata['final_email']
                row_data['User Name'] = metadata['original_name']
                row_data['Validation Status'] = "⚠️ Name Mismatch (Kept Original)"

            validated_rows.append(row_data)

        # 5. Errors (hidden but included)
        for status in [ValidationStatus.ERR_NOT_FOUND, ValidationStatus.ERR_EMAIL_INVALID, ValidationStatus.ERR_MISSING_DATA]:
            for item in stage2_categorized.get(status, []):
                row_data = item['row'].to_dict()
                row_data['Validation Status'] = ValidationStatus.get_display_text(status)
                validated_rows.append(row_data)

        # Create output
        output_df = pd.DataFrame(validated_rows)
        cols = ['Validation Status'] + [c for c in output_df.columns if c != 'Validation Status']
        output_df = output_df[cols]

        # Save
        base_name = stage2_input_filename.replace('.csv', '').replace('.xlsx', '')
        date_str = datetime.now().strftime('%Y%m%d')
        output_filename = f"{base_name}_validated_{date_str}.xlsx"
        output_path = os.path.join(STAGE2_DIR, output_filename)

        output_df.to_excel(output_path, index=False, sheet_name='Validated')

        print(f"\n✅ Saved: {output_path}")
        print(f"   Rows: {len(output_df)}")
        print(f"   Columns: {list(output_df.columns)}")

        s2_status.value = f"<span style='color:blue;'>✅ Saved: {output_filename}</span>"

    except Exception as e:
        print(f"\n❌ Save error: {str(e)}")
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
