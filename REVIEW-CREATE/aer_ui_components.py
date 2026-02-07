"""
AER UI Components - Improved UI/UX for Access Review System

This module provides three core UI components:
1. UILogger - Dual-layer message display (UI + log file)
2. ManualReviewUI - Batch operations for manual review
3. OrgTreeUI - Enhanced organization tree visualization
"""

import html
import logging
from typing import Optional, List, Dict
import pandas as pd
import ipywidgets as widgets
from IPython.display import display, HTML, clear_output


class UILogger:
    """
    Dual-layer output system: UI displays only key updates,
    detailed logs go to file.

    Usage:
        ui_log = UILogger(output_widget, status_widget, file_logger)
        ui_log.update_status("Processing...", 'info')
        ui_log.show_progress(1, 100, "Loading data")
        ui_log.log_detail("Detailed info for log file")
    """

    def __init__(self, output_widget: widgets.Output,
                 status_widget: widgets.HTML,
                 file_logger: logging.Logger):
        """
        Initialize UILogger with widgets and file logger.

        Args:
            output_widget: widgets.Output() for main content
            status_widget: widgets.HTML() for status bar
            file_logger: logging.Logger for file logging
        """
        self.output = output_widget
        self.status = status_widget
        self.logger = file_logger

    def update_status(self, message: str, style: str = 'info'):
        """
        Update status bar - one line only (replaces previous).

        Args:
            message: Status message to display
            style: 'info' | 'success' | 'error' | 'warning'
        """
        colors = {
            'info': 'blue',
            'success': 'green',
            'error': 'red',
            'warning': 'orange'
        }
        color = colors.get(style, 'blue')

        # Escape HTML to prevent XSS
        safe_message = html.escape(message)
        self.status.value = f"<span style='color:{color};'>{safe_message}</span>"
        self.logger.info(f"[STATUS] {message}")

    def show_progress(self, current: int, total: int, message: str):
        """
        Show progress - overwrites previous (no accumulation).

        Args:
            current: Current progress count
            total: Total count
            message: Progress message
        """
        # 1. Division-by-zero protection
        percentage = int((current / total) * 100) if total > 0 else 0

        # 2. XSS protection for message only (current/total are ints, safe)
        safe_message = html.escape(message)

        # 3. Clear and display (use global clear_output, NOT self.output.clear_output)
        with self.output:
            clear_output(wait=True)  # Global function from IPython.display
            display(HTML(f"<b>{safe_message}</b> ({current}/{total} - {percentage}%)"))

        # 4. Log to file
        self.logger.info(f"[PROGRESS] {current}/{total} - {message}")

    def log_detail(self, message: str):
        """File-only logging (not shown in UI)."""
        self.logger.info(message)


class ManualReviewUI:
    """
    Batch operations UI for manual review of ~20 records.

    Automatically groups records by issue type:
    - No Record: Users not found in AD
    - Inactive: Account disabled in AD
    - Fuzzy Match: Potential matches requiring approval
    """

    def __init__(self, df_review: pd.DataFrame):
        """
        Initialize ManualReviewUI with review DataFrame.

        Args:
            df_review: DataFrame with columns:
                - name, department, email
                - ad_status: 'Not Found' | 'Inactive' | 'Active'
                - fuzzy_match: suggested email (optional)
        """
        self.df = df_review
        self.groups = self._categorize_records()
        self.checkboxes = {}  # {index: checkbox_widget}
        self.selection_count = widgets.HTML(value="Selected: 0")

    def _categorize_records(self) -> Dict[str, pd.DataFrame]:
        """
        Auto-group by issue type.

        Returns:
            Dict with keys: 'no_record', 'inactive', 'fuzzy'
        """
        groups = {
            'no_record': self.df[self.df['ad_status'] == 'Not Found'],
            'inactive': self.df[self.df['ad_status'] == 'Inactive'],
            'fuzzy': self.df[self.df['fuzzy_match'].notna()]
        }
        return groups

    def select_all(self):
        """Select all checkboxes."""
        for cb in self.checkboxes.values():
            cb.value = True
        self._update_count()

    def deselect_all(self):
        """Deselect all checkboxes."""
        for cb in self.checkboxes.values():
            cb.value = False
        self._update_count()

    def select_group(self, group_name: str):
        """
        Select all checkboxes in specified group.

        Args:
            group_name: 'no_record' | 'inactive' | 'fuzzy'
        """
        if group_name not in self.groups:
            return

        group_df = self.groups[group_name]
        for idx in group_df.index:
            if idx in self.checkboxes:
                self.checkboxes[idx].value = True
        self._update_count()

    def _update_count(self):
        """Update selection counter display."""
        selected = sum(1 for cb in self.checkboxes.values() if cb.value)
        total = len(self.checkboxes)
        self.selection_count.value = f"Selected: {selected} / {total}"

    def render(self) -> widgets.VBox:
        """
        Render the complete Manual Review UI.

        Returns:
            widgets.VBox containing the complete UI
        """
        # Apple-style colors
        COLORS = {
            'primary': '#007AFF',
            'success': '#34C759',
            'warning': '#FF9500',
            'danger': '#FF3B30',
        }

        # Header
        header = widgets.HTML(
            value="<h2 style='margin-bottom:16px;'>Manual Review Required</h2>"
        )

        # Quick Actions Buttons
        btn_select_all = widgets.Button(
            description='Select All',
            button_style='',
            layout=widgets.Layout(width='120px', height='32px')
        )
        btn_deselect_all = widgets.Button(
            description='Deselect All',
            button_style='',
            layout=widgets.Layout(width='120px', height='32px')
        )

        btn_select_no_record = widgets.Button(
            description=f'Select: No Record ({len(self.groups["no_record"])})',
            button_style='info',
            layout=widgets.Layout(width='auto', height='32px')
        )
        btn_select_inactive = widgets.Button(
            description=f'Select: Inactive ({len(self.groups["inactive"])})',
            button_style='warning',
            layout=widgets.Layout(width='auto', height='32px')
        )
        btn_select_fuzzy = widgets.Button(
            description=f'Select: Fuzzy Match ({len(self.groups["fuzzy"])})',
            button_style='primary',
            layout=widgets.Layout(width='auto', height='32px')
        )

        # Bind events
        btn_select_all.on_click(lambda b: self.select_all())
        btn_deselect_all.on_click(lambda b: self.deselect_all())
        btn_select_no_record.on_click(lambda b: self.select_group('no_record'))
        btn_select_inactive.on_click(lambda b: self.select_group('inactive'))
        btn_select_fuzzy.on_click(lambda b: self.select_group('fuzzy'))

        quick_actions = widgets.VBox([
            widgets.HTML("<h3 style='margin-bottom:8px;'>Quick Actions</h3>"),
            widgets.HBox([btn_select_all, btn_deselect_all]),
            widgets.HBox([btn_select_no_record, btn_select_inactive, btn_select_fuzzy])
        ])

        # Groups
        groups_ui = []
        for group_name, group_df in self.groups.items():
            if len(group_df) > 0:
                groups_ui.append(self._render_group(group_name, group_df))

        # Bottom Actions
        btn_approve = widgets.Button(
            description='✓ Approve Selected',
            button_style='success',
            layout=widgets.Layout(width='180px', height='40px')
        )
        btn_skip = widgets.Button(
            description='✗ Skip Selected',
            button_style='danger',
            layout=widgets.Layout(width='180px', height='40px')
        )

        # Main layout
        return widgets.VBox([
            header,
            quick_actions,
            widgets.HTML("<hr>"),
            *groups_ui,
            widgets.HTML("<hr>"),
            self.selection_count,
            widgets.HBox([btn_approve, btn_skip])
        ])

    def _render_group(self, group_name: str, group_df: pd.DataFrame) -> widgets.VBox:
        """
        Render a single group of records.

        Args:
            group_name: 'no_record' | 'inactive' | 'fuzzy'
            group_df: DataFrame of records in this group

        Returns:
            widgets.VBox containing the group UI
        """
        group_titles = {
            'no_record': 'No Record',
            'inactive': 'Inactive Users',
            'fuzzy': 'Fuzzy Match'
        }

        title = widgets.HTML(
            value=f"<h3 style='margin-top:16px;'>{group_titles[group_name]} ({len(group_df)})</h3>"
        )

        rows = []
        for idx, row in group_df.iterrows():
            cb = widgets.Checkbox(
                value=False,
                description=f"{row['name']} | {row['department']} | {row['ad_status']}",
                indent=False,
                layout=widgets.Layout(width='600px')
            )
            cb.observe(lambda change: self._update_count(), 'value')
            self.checkboxes[idx] = cb
            rows.append(cb)

        return widgets.VBox([title, *rows])

    def get_selected(self) -> List[int]:
        """
        Get list of selected record indices.

        Returns:
            List of DataFrame indices that are selected
        """
        return [idx for idx, cb in self.checkboxes.items() if cb.value]


class OrgTreeUI:
    """
    Enhanced organization tree visualization for dept head selection.

    Features:
    - Default expand all (no manual clicking)
    - Filter to show only dept heads
    - Toggle visibility of non-dept-heads
    - Visual markers (⭐) for dept head candidates
    """

    def __init__(self, df_ad: pd.DataFrame):
        """
        Initialize OrgTreeUI with Active Directory data.

        Args:
            df_ad: DataFrame with columns:
                - mail, displayName, jobTitle, department
                - manager_mail: email of manager
        """
        self.df = df_ad.copy()
        self.dept_heads = self._identify_dept_heads()
        self.show_heads_only = True   # Default: only show dept heads
        self.expand_all = True         # Default: expand all nodes
        self.checkboxes = {}
        self.tree_output = widgets.Output()
        self.selection_count = widgets.HTML(value="Selected: 0 department heads")

    def _identify_dept_heads(self) -> pd.DataFrame:
        """
        Auto-detect department heads based on job title.

        Returns:
            DataFrame of identified department heads
        """
        dept_keywords = [
            'director', 'manager', 'head', 'chief',
            'ceo', 'cfo', 'cto', 'cmo',
            'vp', 'vice president', 'lead', 'supervisor'
        ]

        def is_dept_head(title):
            if pd.isna(title):
                return False
            title_lower = str(title).lower()
            return any(kw in title_lower for kw in dept_keywords)

        self.df['is_dept_head'] = self.df['jobTitle'].apply(is_dept_head)
        return self.df[self.df['is_dept_head'] == True]

    def _find_root(self) -> str:
        """
        Find root node (person with no manager).

        Returns:
            Email of root person (typically CEO)
        """
        root_person = self.df[self.df['manager_mail'].isna()]
        if len(root_person) == 0:
            # No explicit root, pick first person
            return self.df.iloc[0]['mail']
        return root_person.iloc[0]['mail']

    def render(self) -> widgets.VBox:
        """
        Render the organization tree UI.

        Returns:
            VBox widget containing tree visualization and controls
        """
        # Filter controls
        filter_checkbox = widgets.Checkbox(
            value=self.show_heads_only,
            description='Show dept heads only',
            style={'description_width': 'initial'}
        )
        filter_checkbox.observe(self._on_filter_change, names='value')

        # Expand/collapse control
        expand_checkbox = widgets.Checkbox(
            value=self.expand_all,
            description='Expand all',
            style={'description_width': 'initial'}
        )
        expand_checkbox.observe(self._on_expand_change, names='value')

        # Selection count display
        self._update_selection_count()

        # Initial tree render
        self._render_tree()

        # Assemble UI
        controls = widgets.HBox([filter_checkbox, expand_checkbox, self.selection_count])
        return widgets.VBox([controls, self.tree_output])

    def _render_tree(self):
        """
        Render the organization tree with ASCII art.
        """
        self.tree_output.clear_output(wait=True)

        with self.tree_output:
            root_email = self._find_root()
            self._render_node(root_email, prefix='', is_last=True, depth=0)

    def _render_node(self, email: str, prefix: str, is_last: bool, depth: int):
        """
        Recursively render a tree node.

        Args:
            email: Email of person to render
            prefix: ASCII art prefix for tree structure
            is_last: Whether this is the last child
            depth: Current tree depth (for indentation)
        """
        person = self.df[self.df['mail'] == email]
        if len(person) == 0:
            return

        person = person.iloc[0]

        # Skip non-dept-heads if filter is active
        if self.show_heads_only and not person['is_dept_head']:
            # But still render children if they might be dept heads
            children = self.df[self.df['manager_mail'] == email]
            for idx, child in children.iterrows():
                self._render_node(child['mail'], prefix, is_last, depth)
            return

        # Determine tree branch characters
        branch = '└─ ' if is_last else '├─ '
        next_prefix = prefix + ('   ' if is_last else '│  ')

        # Render checkbox and person info
        is_dept_head = person['is_dept_head']
        marker = '⭐ ' if is_dept_head else ''
        label = f"{marker}{person['displayName']} - {person['jobTitle']} ({person['department']})"

        # Create checkbox
        checkbox = widgets.Checkbox(
            value=False,
            description=label,
            indent=False,
            layout=widgets.Layout(width='auto')
        )
        checkbox.observe(lambda change: self._update_selection_count(), names='value')
        self.checkboxes[email] = checkbox

        # Display with tree structure
        tree_prefix_html = HTML(f'<pre style="display:inline;margin:0">{prefix}{branch}</pre>')
        display(widgets.HBox([tree_prefix_html, checkbox]))

        # Render children if expanded
        if self.expand_all or depth < 2:  # Always show at least 2 levels
            children = self.df[self.df['manager_mail'] == email]
            children_list = children.to_dict('records')

            for i, child in enumerate(children_list):
                is_last_child = (i == len(children_list) - 1)
                self._render_node(child['mail'], next_prefix, is_last_child, depth + 1)

    def _on_filter_change(self, change):
        """
        Handle filter toggle (show dept heads only).

        Args:
            change: Widget change event
        """
        self.show_heads_only = change['new']
        self.checkboxes.clear()
        self._render_tree()

    def _on_expand_change(self, change):
        """
        Handle expand/collapse toggle.

        Args:
            change: Widget change event
        """
        self.expand_all = change['new']
        self.checkboxes.clear()
        self._render_tree()

    def _update_selection_count(self):
        """
        Update the selection count display.
        """
        selected_count = sum(1 for cb in self.checkboxes.values() if cb.value)
        self.selection_count.value = f"Selected: {selected_count} department heads"

    def get_selected_heads(self) -> List[str]:
        """
        Get list of selected department head emails.

        Returns:
            List of email addresses for selected dept heads
        """
        selected = []
        for email, checkbox in self.checkboxes.items():
            if checkbox.value:
                selected.append(email)
        return selected
