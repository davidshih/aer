#!/usr/bin/env python3
"""
Stage 2: Email/User Validation with Enhanced Status Tracking (v3.0)

Improvements over v2.1:
1. ✅ Hide 100% exact matches (auto-validated, no UI needed)
2. ✅ Color-code single fuzzy matches (green for high confidence)
3. ✅ Add comprehensive Validation Status column to export
4. ✅ Handle all edge cases with clear status indicators

Validation Status Categories:
- VALID_PERFECT: Email + Name match (hidden, auto-pass)
- WARN_NAME_MISMATCH: Email valid but name differs (yellow warning)
- INFO_FUZZY_UNIQUE: Email missing, 1 fuzzy match (green, auto-select)
- ERR_FUZZY_MULTIPLE: Email missing, 2+ matches (orange, manual select)
- ERR_NOT_FOUND: Email missing, no match (hidden, mark as not found)
- ERR_EMAIL_INVALID: Email format valid but not in AD (hidden, mark as invalid)
- ERR_MISSING_DATA: Both email and name missing (hidden, mark as insufficient)

UI Display:
- Hide: VALID_PERFECT, ERR_NOT_FOUND, ERR_EMAIL_INVALID, ERR_MISSING_DATA
- Show: WARN_NAME_MISMATCH, INFO_FUZZY_UNIQUE, ERR_FUZZY_MULTIPLE

Color Coding:
- 🟢 Green: INFO_FUZZY_UNIQUE (single match, high confidence)
- 🟡 Yellow: WARN_NAME_MISMATCH (needs confirmation)
- 🟠 Orange: ERR_FUZZY_MULTIPLE (needs manual selection)
"""

import os
import sys
import re
import unicodedata
from typing import Dict, List, Tuple, Optional
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
# Validation Status Enum
# ============================================

class ValidationStatus:
    """Validation status categories"""
    VALID_PERFECT = "valid_perfect"                  # ✅ Email + Name match (hide)
    WARN_NAME_MISMATCH = "warn_name_mismatch"        # ⚠️ Email valid, name differs (show)
    INFO_FUZZY_UNIQUE = "info_fuzzy_unique"          # 🔵 Email missing, 1 match (show, green)
    ERR_FUZZY_MULTIPLE = "err_fuzzy_multiple"        # 🟠 Email missing, 2+ matches (show)
    ERR_NOT_FOUND = "err_not_found"                  # ❌ No match found (hide)
    ERR_EMAIL_INVALID = "err_email_invalid"          # ❌ Email not in AD (hide)
    ERR_MISSING_DATA = "err_missing_data"            # ⚪ Insufficient data (hide)

    @staticmethod
    def get_display_text(status: str) -> str:
        """Get human-readable status text for export"""
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

    @staticmethod
    def should_show_in_ui(status: str) -> bool:
        """Determine if this status should be shown in UI"""
        show_statuses = {
            ValidationStatus.WARN_NAME_MISMATCH,
            ValidationStatus.INFO_FUZZY_UNIQUE,
            ValidationStatus.ERR_FUZZY_MULTIPLE
        }
        return status in show_statuses


# ============================================
# Helper Functions
# ============================================

def is_email_valid(email) -> bool:
    """Check if email is valid (not empty and has @ symbol)"""
    if pd.isna(email):
        return False

    email_str = str(email).strip().lower()

    # Invalid values
    if email_str in ['', 'nan', 'none', 'n/a', 'na', '#n/a']:
        return False

    # Must have @ and . for basic validation
    if '@' not in email_str or '.' not in email_str:
        return False

    # Basic email regex
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


def fuzzy_match_name(target_name: str, name_index: Dict, ad_cache: Dict, top_n: int = 3) -> List[Dict]:
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


# ============================================
# Validation Categories
# ============================================

def categorize_user(row: pd.Series, ad_cache: Dict, name_index: Dict) -> Tuple[str, Dict]:
    """
    Categorize a user record with comprehensive status

    Returns:
        (status, metadata)

    Status categories:
    - VALID_PERFECT: Email + Name match (hide from UI)
    - WARN_NAME_MISMATCH: Email valid but name differs (show warning)
    - INFO_FUZZY_UNIQUE: Email missing, 1 fuzzy match (show, auto-select)
    - ERR_FUZZY_MULTIPLE: Email missing, 2+ fuzzy matches (show dropdown)
    - ERR_NOT_FOUND: Email missing, no match (hide, mark as error)
    - ERR_EMAIL_INVALID: Email valid format but not in AD (hide, mark as error)
    - ERR_MISSING_DATA: Both email and name missing (hide, mark as error)
    """
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

    # Check if email is valid
    email_valid = is_email_valid(user_email)

    # Case 1: Both email and name are missing
    if not email_valid and (not user_name or pd.isna(user_name) or str(user_name).strip() == ''):
        metadata['validation_message'] = 'Insufficient data: both email and name are missing'
        return ValidationStatus.ERR_MISSING_DATA, metadata

    # Case 2: Email is valid
    if email_valid:
        email_clean = str(user_email).strip().lower()

        # Check if email exists in AD
        if email_clean not in ad_cache:
            metadata['validation_message'] = f'Email {email_clean} not found in AD'
            return ValidationStatus.ERR_EMAIL_INVALID, metadata

        # Email exists in AD
        ad_user = ad_cache[email_clean]
        metadata['ad_user'] = ad_user
        metadata['final_email'] = email_clean
        metadata['final_name'] = ad_user['name']

        # Check if name matches
        ad_name_norm = normalize_name(ad_user['name'])
        input_name_norm = normalize_name(user_name)

        if input_name_norm and ad_name_norm == input_name_norm:
            # Perfect match
            metadata['validation_message'] = 'Email and name verified'
            return ValidationStatus.VALID_PERFECT, metadata
        else:
            # Name mismatch
            metadata['validation_message'] = f"Email valid but name differs: Input='{user_name}', AD='{ad_user['name']}'"
            return ValidationStatus.WARN_NAME_MISMATCH, metadata

    # Case 3: Email is invalid/missing, try fuzzy match by name
    if not user_name or pd.isna(user_name) or str(user_name).strip() == '':
        metadata['validation_message'] = 'Email missing and no name provided'
        return ValidationStatus.ERR_MISSING_DATA, metadata

    # Try fuzzy matching
    fuzzy_matches = fuzzy_match_name(user_name, name_index, ad_cache, top_n=5)

    if not fuzzy_matches:
        metadata['validation_message'] = f'No match found for name: {user_name}'
        return ValidationStatus.ERR_NOT_FOUND, metadata

    metadata['fuzzy_matches'] = fuzzy_matches

    if len(fuzzy_matches) == 1:
        # Single match found
        match = fuzzy_matches[0]
        metadata['final_email'] = match['email']
        metadata['final_name'] = match['name']
        metadata['validation_message'] = f'Single match found: {match["name"]} ({match["score"]}% confidence)'
        return ValidationStatus.INFO_FUZZY_UNIQUE, metadata
    else:
        # Multiple matches found
        metadata['validation_message'] = f'Found {len(fuzzy_matches)} possible matches'
        return ValidationStatus.ERR_FUZZY_MULTIPLE, metadata


# ============================================
# UI Components
# ============================================

def create_fuzzy_unique_row(idx: int, row: pd.Series, metadata: Dict):
    """Create row for single fuzzy match (auto-selected, green color)"""

    original_name = str(metadata['original_name'])
    match = metadata['fuzzy_matches'][0]

    # Green color for high confidence single match
    name_html = f"""
    <div style='width:220px; padding:5px;'>
        <b style='color:#34c759;'>✓ {original_name}</b>
        <br><small style='color:#34c759;'>Best match: {match['score']}%</small>
    </div>
    """

    # Info box
    info_html = f"""
    <div style='padding:5px; border:1px solid #34c759; background:#e8f5e9; border-radius:4px; width:500px;'>
        <b style='color:#34c759;'>✅ Single Match Found</b><br>
        <b>{match['name']}</b> ({match['email']})<br>
        Department: {match['dept']}<br>
        Confidence: {match['score']}%
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
    """Create row for multiple fuzzy matches (dropdown selection, orange color)"""

    original_name = str(metadata['original_name'])
    fuzzy_matches = metadata['fuzzy_matches']

    # Detect ambiguity
    is_ambiguous = len(fuzzy_matches) > 1

    # Orange color for ambiguous matches
    name_html = f"""
    <div style='width:220px; padding:5px;'>
        <b style='color:#ff9500;'>⚠️ {original_name}</b>
        <br><small style='color:#ff9500;'>Multiple matches found</small>
    </div>
    """

    # Dropdown options
    options = [('-- Select --', '')]
    for match in fuzzy_matches:
        label = f"{match['name']} ({match['email']}) - {match['dept']} [{match['score']}%]"
        options.append((label, match['email']))
    options.append(('-- Manual Entry --', 'MANUAL'))

    # Widgets
    dropdown = widgets.Dropdown(
        options=options,
        value=fuzzy_matches[0]['email'],  # Auto-select best match
        description='',
        layout=widgets.Layout(width='550px')
    )
    txt_manual = widgets.Text(
        placeholder='Enter email manually',
        layout=widgets.Layout(width='300px'),
        disabled=True
    )

    # Link dropdown to manual text
    def on_dropdown_change(change):
        if change['new'] == 'MANUAL':
            txt_manual.disabled = False
        else:
            txt_manual.disabled = True
            txt_manual.value = ''

    dropdown.observe(on_dropdown_change, names='value')

    return {
        'index': idx,
        'name_widget': widgets.HTML(value=name_html),
        'dropdown': dropdown,
        'manual_input': txt_manual,
        'row': widgets.HBox([
            widgets.HTML(value=name_html),
            dropdown,
            txt_manual
        ])
    }


def create_mismatch_row(idx: int, row: pd.Series, metadata: Dict):
    """Create row for email/name mismatch (yellow warning)"""

    original_email = metadata['original_email']
    original_name = metadata['original_name']
    ad_user = metadata['ad_user']

    # Checkbox for acceptance
    chk_accept = widgets.Checkbox(
        value=True,
        description='Accept AD Name',
        indent=False
    )

    # Yellow warning box
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
        'row': widgets.HBox([
            chk_accept,
            widgets.HTML(value=info_html)
        ])
    }


def create_stage2_ui(input_df: pd.DataFrame, ad_cache: Dict, name_index: Dict):
    """Create enhanced Stage 2 UI with status tracking"""

    # Categorize all users
    print("🔍 Categorizing users...")
    categorized = {}

    for idx, row in input_df.iterrows():
        status, metadata = categorize_user(row, ad_cache, name_index)

        if status not in categorized:
            categorized[status] = []

        categorized[status].append({
            'index': idx,
            'row': row,
            'metadata': metadata,
            'status': status
        })

    # Statistics
    stats = {status: len(categorized.get(status, [])) for status in [
        ValidationStatus.VALID_PERFECT,
        ValidationStatus.WARN_NAME_MISMATCH,
        ValidationStatus.INFO_FUZZY_UNIQUE,
        ValidationStatus.ERR_FUZZY_MULTIPLE,
        ValidationStatus.ERR_NOT_FOUND,
        ValidationStatus.ERR_EMAIL_INVALID,
        ValidationStatus.ERR_MISSING_DATA
    ]}

    print(f"\n📊 Validation Statistics:")
    print(f"   ✅ Perfect Match (hidden):     {stats[ValidationStatus.VALID_PERFECT]}")
    print(f"   🔵 Single Fuzzy Match:         {stats[ValidationStatus.INFO_FUZZY_UNIQUE]}")
    print(f"   ⚠️  Name Mismatch:              {stats[ValidationStatus.WARN_NAME_MISMATCH]}")
    print(f"   🟠 Multiple Matches:           {stats[ValidationStatus.ERR_FUZZY_MULTIPLE]}")
    print(f"   ❌ Not Found (hidden):         {stats[ValidationStatus.ERR_NOT_FOUND]}")
    print(f"   ❌ Email Invalid (hidden):     {stats[ValidationStatus.ERR_EMAIL_INVALID]}")
    print(f"   ⚪ Missing Data (hidden):      {stats[ValidationStatus.ERR_MISSING_DATA]}")
    print(f"   📌 Total:                      {len(input_df)}\n")

    # Create UI sections
    ui_sections = []
    ui_rows = {
        'fuzzy_unique': [],
        'fuzzy_multiple': [],
        'mismatch': []
    }

    # Summary
    summary_html = f"""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 20px; border-radius: 8px; color: white; margin-bottom: 20px;'>
        <h2 style='margin: 0 0 10px 0;'>🔍 Stage 2: Email/User Validation (Enhanced)</h2>
        <div style='display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px;'>
            <div style='background: rgba(255,255,255,0.2); padding: 10px; border-radius: 5px; text-align: center;'>
                <div style='font-size: 24px; font-weight: bold;'>{stats[ValidationStatus.VALID_PERFECT]}</div>
                <div>✅ Perfect (Auto)</div>
            </div>
            <div style='background: rgba(52,199,89,0.3); padding: 10px; border-radius: 5px; text-align: center;'>
                <div style='font-size: 24px; font-weight: bold;'>{stats[ValidationStatus.INFO_FUZZY_UNIQUE]}</div>
                <div>🔵 Single Match</div>
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
        <div style='margin-top: 15px; padding: 10px; background: rgba(255,255,255,0.1); border-radius: 5px;'>
            <b>Note:</b> Perfect matches, not found, and invalid emails are hidden from UI but included in export.
        </div>
    </div>
    """
    ui_sections.append(widgets.HTML(value=summary_html))

    # Section 1: Single Fuzzy Match (Green, Auto-selected)
    if stats[ValidationStatus.INFO_FUZZY_UNIQUE] > 0:
        section_title = widgets.HTML(value="""
            <h3 style='color: #34c759; border-bottom: 2px solid #34c759; padding-bottom: 5px;'>
                🔵 Single Match Found (Auto-Selected)
            </h3>
            <p style='color: #7f8c8d;'>
                These users have one clear match. The system has auto-selected them for you.
            </p>
        """)
        ui_sections.append(section_title)

        for item in categorized.get(ValidationStatus.INFO_FUZZY_UNIQUE, []):
            row_ui = create_fuzzy_unique_row(item['index'], item['row'], item['metadata'])
            ui_rows['fuzzy_unique'].append(row_ui)
            ui_sections.append(row_ui['row'])

    # Section 2: Multiple Fuzzy Matches (Orange, Manual Select)
    if stats[ValidationStatus.ERR_FUZZY_MULTIPLE] > 0:
        section_title = widgets.HTML(value="""
            <h3 style='color: #ff9500; border-bottom: 2px solid #ff9500; padding-bottom: 5px; margin-top: 30px;'>
                🟠 Multiple Matches - Select Correct One
            </h3>
            <p style='color: #7f8c8d;'>
                These users have multiple possible matches. Please select the correct one from the dropdown.
            </p>
        """)
        ui_sections.append(section_title)

        for item in categorized.get(ValidationStatus.ERR_FUZZY_MULTIPLE, []):
            row_ui = create_fuzzy_multiple_row(item['index'], item['row'], item['metadata'])
            ui_rows['fuzzy_multiple'].append(row_ui)
            ui_sections.append(row_ui['row'])

    # Section 3: Name Mismatch (Yellow Warning)
    if stats[ValidationStatus.WARN_NAME_MISMATCH] > 0:
        section_title = widgets.HTML(value="""
            <h3 style='color: #ff9800; border-bottom: 2px solid #ff9800; padding-bottom: 5px; margin-top: 30px;'>
                ⚠️ Email Valid but Name Differs
            </h3>
            <p style='color: #7f8c8d;'>
                These users have valid emails in AD, but the name doesn't match. Review and accept.
            </p>
        """)
        ui_sections.append(section_title)

        for item in categorized.get(ValidationStatus.WARN_NAME_MISMATCH, []):
            row_ui = create_mismatch_row(item['index'], item['row'], item['metadata'])
            ui_rows['mismatch'].append(row_ui)
            ui_sections.append(row_ui['row'])

    # Save button
    btn_save = widgets.Button(
        description='💾 Save Validated File',
        button_style='success',
        layout=widgets.Layout(width='200px', height='40px')
    )

    # Save function
    def on_save(b):
        print("💾 Saving validated file with status tracking...")

        # Build output dataframe
        validated_rows = []

        # 1. Add perfect matches (hidden from UI)
        for item in categorized.get(ValidationStatus.VALID_PERFECT, []):
            row_data = item['row'].to_dict()
            metadata = item['metadata']
            row_data['Email'] = metadata['final_email']
            row_data['User Name'] = metadata['final_name']
            row_data['Validation Status'] = ValidationStatus.get_display_text(ValidationStatus.VALID_PERFECT)
            validated_rows.append(row_data)

        # 2. Add single fuzzy matches
        for row_ui in ui_rows['fuzzy_unique']:
            item = categorized[ValidationStatus.INFO_FUZZY_UNIQUE][ui_rows['fuzzy_unique'].index(row_ui)]
            row_data = item['row'].to_dict()
            row_data['Email'] = row_ui['selected_email']
            row_data['User Name'] = row_ui['selected_name']
            row_data['Validation Status'] = ValidationStatus.get_display_text(ValidationStatus.INFO_FUZZY_UNIQUE)
            validated_rows.append(row_data)

        # 3. Add multiple fuzzy matches (from dropdown)
        for row_ui in ui_rows['fuzzy_multiple']:
            item = categorized[ValidationStatus.ERR_FUZZY_MULTIPLE][ui_rows['fuzzy_multiple'].index(row_ui)]
            row_data = item['row'].to_dict()

            selected = row_ui['dropdown'].value
            is_manual_entry = (selected == 'MANUAL')

            if is_manual_entry:
                selected = row_ui['manual_input'].value.strip().lower()

            if selected:
                # Try to find in fuzzy matches first
                found_in_matches = False
                for match in item['metadata']['fuzzy_matches']:
                    if match['email'] == selected:
                        row_data['Email'] = match['email']
                        row_data['User Name'] = match['name']
                        found_in_matches = True
                        break

                # If manual entry and not found in matches, use the manual value
                if is_manual_entry and not found_in_matches:
                    row_data['Email'] = selected
                    # Try to lookup name in AD cache if manual email is valid
                    if selected in ad_cache:
                        row_data['User Name'] = ad_cache[selected]['name']
                    # else keep original name

                row_data['Validation Status'] = "🔧 Manually Resolved" if is_manual_entry else ValidationStatus.get_display_text(ValidationStatus.ERR_FUZZY_MULTIPLE)
                validated_rows.append(row_data)

        # 4. Add name mismatches (both accepted and rejected)
        for row_ui in ui_rows['mismatch']:
            item = categorized[ValidationStatus.WARN_NAME_MISMATCH][ui_rows['mismatch'].index(row_ui)]
            row_data = item['row'].to_dict()
            metadata = item['metadata']

            if row_ui['accept_checkbox'].value:
                # User accepted AD name
                row_data['Email'] = metadata['final_email']
                row_data['User Name'] = metadata['final_name']  # Use AD name
                row_data['Validation Status'] = "✅ Name Mismatch Resolved (AD Name Accepted)"
            else:
                # User rejected AD name, keep original
                row_data['Email'] = metadata['final_email']  # Still use valid email
                row_data['User Name'] = metadata['original_name']  # Keep original name
                row_data['Validation Status'] = "⚠️ Name Mismatch (User Kept Original Name)"

            validated_rows.append(row_data)

        # 5. Add errors (hidden from UI but included in export)
        for status in [ValidationStatus.ERR_NOT_FOUND, ValidationStatus.ERR_EMAIL_INVALID, ValidationStatus.ERR_MISSING_DATA]:
            for item in categorized.get(status, []):
                row_data = item['row'].to_dict()
                row_data['Validation Status'] = ValidationStatus.get_display_text(status)
                validated_rows.append(row_data)

        # Create DataFrame
        output_df = pd.DataFrame(validated_rows)

        # Reorder columns: Validation Status first
        cols = ['Validation Status'] + [c for c in output_df.columns if c != 'Validation Status']
        output_df = output_df[cols]

        print(f"\n✅ Validated {len(output_df)} users")
        print(f"   Columns: {list(output_df.columns)}")
        print("\nReady to save! (Implementation pending)")

    btn_save.on_click(on_save)

    ui_sections.append(widgets.HTML(value="<hr style='margin: 30px 0;'>"))
    ui_sections.append(widgets.HBox([btn_save]))

    # Main UI container
    main_ui = widgets.VBox(ui_sections)

    return main_ui, categorized, ui_rows


# ============================================
# Main function (for testing)
# ============================================

if __name__ == "__main__":
    # Example test data
    ad_cache = {
        'john.doe@example.com': {'name': 'John Doe', 'dept': 'Finance', 'active': True},
        'jane.smith@example.com': {'name': 'Jane Smith', 'dept': 'Marketing', 'active': True},
        'bob.johnson@example.com': {'name': 'Robert Johnson', 'dept': 'IT', 'active': True},
    }

    name_index = {
        'john doe': 'john.doe@example.com',
        'jane smith': 'jane.smith@example.com',
        'robert johnson': 'bob.johnson@example.com',
        'bob johnson': 'bob.johnson@example.com',
    }

    test_data = pd.DataFrame({
        'Email': [
            'john.doe@example.com',  # Perfect match
            '',                       # Single fuzzy match
            'invalid',                # Multiple fuzzy matches (will find Bob)
            'unknown@example.com',    # Email not in AD
            'jane.smith@example.com'  # Name mismatch
        ],
        'User Name': [
            'John Doe',               # Perfect match
            'Bob Johnson',            # Single fuzzy match (no email)
            'Robert',                 # Partial name
            'David Brown',            # Not found
            'Jane Smithers'           # Name mismatch
        ]
    })

    print("="*60)
    print("🧪 Testing Stage 2 Enhanced UI")
    print("="*60 + "\n")

    ui, categorized, ui_rows = create_stage2_ui(test_data, ad_cache, name_index)

    print("\n✅ UI created successfully!")
    print(f"   Fuzzy unique rows: {len(ui_rows['fuzzy_unique'])}")
    print(f"   Fuzzy multiple rows: {len(ui_rows['fuzzy_multiple'])}")
    print(f"   Mismatch rows: {len(ui_rows['mismatch'])}")

    # In Jupyter, you would do: display(ui)
