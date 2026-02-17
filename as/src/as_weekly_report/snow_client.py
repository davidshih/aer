"""ServiceNow correlation stubs for future implementation."""

from __future__ import annotations

import pandas as pd

SNOW_COLUMNS = [
    "ticket_number",
    "ticket_owner",
    "ticket_status",
    "ticket_last_update_datetime",
    "ticket_last_update_content",
]

JOIN_KEY = "alert_id"


def fetch_related_tickets(
    summary_df: pd.DataFrame,
    lookback_days: int,
) -> pd.DataFrame:
    """Stub implementation for ServiceNow enrichment."""
    _ = summary_df
    _ = lookback_days
    return pd.DataFrame(columns=[JOIN_KEY, *SNOW_COLUMNS])


def merge_snow_columns(
    summary_df: pd.DataFrame,
    snow_df: pd.DataFrame | None,
) -> pd.DataFrame:
    """Merge ServiceNow columns into the summary table."""
    result = summary_df.copy()
    for column in SNOW_COLUMNS:
        if column not in result.columns:
            result[column] = None

    if snow_df is None or snow_df.empty:
        return result
    if JOIN_KEY not in snow_df.columns:
        return result

    selected_columns = [JOIN_KEY] + [
        col for col in SNOW_COLUMNS if col in snow_df.columns
    ]
    merged = result.drop(columns=SNOW_COLUMNS, errors="ignore").merge(
        snow_df[selected_columns].drop_duplicates(subset=[JOIN_KEY], keep="last"),
        on=JOIN_KEY,
        how="left",
    )

    for column in SNOW_COLUMNS:
        if column not in merged.columns:
            merged[column] = None

    return merged
