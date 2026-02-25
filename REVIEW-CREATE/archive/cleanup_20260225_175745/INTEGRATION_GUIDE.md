# AER UI Components Integration Guide

## Overview

This guide explains how to integrate the three new UI components into the existing AER notebook:
- **UILogger** - Dual-layer messaging system
- **ManualReviewUI** - Batch operations for manual review
- **OrgTreeUI** - Enhanced organization tree visualization

## Prerequisites

Ensure `aer_ui_components.py` is in the same directory as your notebook.

---

## Stage 1: Integrate UILogger (Cell 2)

### Import Component

Add at the top of Cell 2:
```python
from aer_ui_components import UILogger
```

### Replace Status Updates

**Before:**
```python
s1_status.value = "<span style='color:green;'>✅ Authentication Successful</span>"
logger_s1.info("Stage 1: Authentication successful")
```

**After:**
```python
ui_log_s1 = UILogger(s1_output, s1_status, logger_s1)
ui_log_s1.update_status("✅ Authentication Successful", 'success')
```

### Replace Progress Displays

**Before:**
```python
with s1_output:
    clear_output(wait=True)
    print(f"Processing {i+1}/{total} users")
```

**After:**
```python
ui_log_s1.show_progress(i+1, total, "Processing users")
```

### Replace Detailed Logging

**Before:**
```python
logger_s1.info(f"Detailed info: {user_email}")  # Shows in UI
```

**After:**
```python
ui_log_s1.log_detail(f"Detailed info: {user_email}")  # Log file only
```

---

## Stage 1.5: Integrate OrgTreeUI (Cell 3)

### Import Component

Add at the top of Cell 3:
```python
from aer_ui_components import OrgTreeUI
```

### Replace Org Tree Display

**Before:**
```python
# Manual tree building code (~50-100 lines)
for person in df_ad.iterrows():
    # Create widgets manually
    # Build tree structure manually
    ...
```

**After:**
```python
# Initialize OrgTreeUI
org_tree_ui = OrgTreeUI(df_ad)

# Render and display
org_tree_widget = org_tree_ui.render()
display(org_tree_widget)

# Get selected department heads
selected_heads = org_tree_ui.get_selected_heads()
print(f"Selected {len(selected_heads)} department heads")
```

### Features Available

- **Default expanded**: All nodes visible by default
- **Filter toggle**: Show only department heads (default)
- **Visual markers**: ⭐ for dept head candidates
- **Selection tracking**: Real-time counter

---

## Stage 2: Integrate ManualReviewUI (Cell 4)

### Import Component

Add at the top of Cell 4:
```python
from aer_ui_components import ManualReviewUI
```

### Prepare Review DataFrame

Ensure your DataFrame has these columns:
```python
df_review = pd.DataFrame({
    'name': [...],
    'department': [...],
    'email': [...],
    'ad_status': [...],  # 'Active' | 'Inactive' | 'Not Found'
    'fuzzy_match': [...]  # Optional suggested email
})
```

### Replace Manual Review UI

**Before:**
```python
# Manual checkbox creation (~30-50 lines)
for idx, row in df_review.iterrows():
    cb = widgets.Checkbox(...)
    # Manual grouping logic
    ...
```

**After:**
```python
# Initialize ManualReviewUI
review_ui = ManualReviewUI(df_review)

# Render and display
review_widget = review_ui.render()
display(review_widget)

# Get selected records for processing
selected_indices = review_ui.get_selected()
df_approved = df_review.loc[selected_indices]
print(f"Processing {len(df_approved)} approved records")
```

### Features Available

- **Auto-grouping**: No Record / Inactive / Fuzzy Match
- **Batch operations**: Select All, Deselect All, Select by Group
- **Real-time counter**: Shows selection count
- **Apple-style UI**: Clean, intuitive interface

---

## Integration Checklist

### Stage 1 (UILogger)
- [ ] Import `UILogger` at top of Cell 2
- [ ] Replace all `s1_status.value =` with `ui_log_s1.update_status()`
- [ ] Replace all progress prints with `ui_log_s1.show_progress()`
- [ ] Move detailed logs to `ui_log_s1.log_detail()`
- [ ] Test: Verify no message duplication

### Stage 1.5 (OrgTreeUI)
- [ ] Import `OrgTreeUI` at top of Cell 3
- [ ] Initialize with `df_ad` DataFrame
- [ ] Replace manual tree code with `org_tree_ui.render()`
- [ ] Use `get_selected_heads()` to retrieve selections
- [ ] Test: Verify default expanded, filter works

### Stage 2 (ManualReviewUI)
- [ ] Import `ManualReviewUI` at top of Cell 4
- [ ] Ensure DataFrame has required columns
- [ ] Initialize with `df_review` DataFrame
- [ ] Replace manual review code with `review_ui.render()`
- [ ] Use `get_selected()` to retrieve selections
- [ ] Test: Verify batch operations work

---

## Testing

After integration, test each stage:

1. **Run Stage 1**: Verify no duplicate messages, progress updates cleanly
2. **Run Stage 1.5**: Verify tree displays correctly, filter/expand work
3. **Run Stage 2**: Verify grouping, batch selection, counter all work
4. **End-to-end**: Run full workflow from authentication to completion

---

## Troubleshooting

### Import Error
```
ImportError: cannot import name 'UILogger' from 'aer_ui_components'
```
**Solution**: Ensure `aer_ui_components.py` is in the same directory as the notebook.

### DataFrame Column Missing
```
KeyError: 'ad_status'
```
**Solution**: Ensure your DataFrame has all required columns. For ManualReviewUI:
- `name`, `department`, `email`, `ad_status`, `fuzzy_match`

### Widget Not Displaying
**Solution**: Ensure you're calling `display(widget)` after `render()`.

---

## Rollback

If integration causes issues, you can revert to the original notebook:
```bash
cp access_review_create_01-30_c.json access_review_create_v7.5_improved.ipynb
```

---

## Support

For issues or questions:
1. Check `docs/plans/2026-02-02-aer-ui-improvements.md` for design details
2. Review `tests/test_aer_ui_components.py` for usage examples
3. Examine `aer_ui_components.py` docstrings for API documentation

---

**Version**: 1.0
**Last Updated**: 2026-02-03
**Status**: Ready for Integration
