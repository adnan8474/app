# POCTIFY Usage Intelligence Streamlit App

"""
POCTIFY Usage Intelligence
==========================

A Streamlit dashboard for auditing point-of-care testing (POCT) usage.
This application analyses middleware logs to surface suspicious activity
such as barcode sharing, rapid repeated testing, device hopping, and
violations of expected working patterns.

This file is intentionally verbose with comments and docstrings so that
it can act as both documentation and example code. The target size is
more than 400 lines of well-structured and readable Python that follows
Streamlit best practices. The supporting modules referenced below are
assumed to be available in the `usage_intelligence` package.
"""

from __future__ import annotations

import base64
import io
import uuid
import datetime as dt
from typing import Dict, List

import pandas as pd
import numpy as np
import altair as alt
import streamlit as st

# ---------------------------------------------------------------------------
# Placeholder imports from other modules. In a real implementation these would
# come from separate files within the usage_intelligence package. They are
# defined as simple functions/classes further below so that this single file
# is self-contained for demonstration purposes.
# ---------------------------------------------------------------------------
try:  # pragma: no cover - placeholder behaviour for this example
    from usage_intelligence.analysis import apply_rules, compute_suspicion_scores
    from usage_intelligence.visualization import (
        show_timeline,
        show_distribution_charts,
        show_heatmap,
        show_flag_pie,
    )
    from usage_intelligence.rules import DEFAULT_THRESHOLDS
except Exception:  # pragma: no cover - fallback definitions
    DEFAULT_THRESHOLDS = {
        "rapid_seconds": 60,
        "device_hop_minutes": 5,
        "hourly_max": 8,
    }

    def apply_rules(df: pd.DataFrame, thresholds: Dict[str, int]) -> pd.DataFrame:
        """Apply simple flagging rules to the dataframe.

        Parameters
        ----------
        df: pd.DataFrame
            Parsed event log.
        thresholds: Dict[str, int]
            Dict with configuration thresholds.

        Returns
        -------
        pd.DataFrame
            DataFrame with boolean columns for each flag.
        """
        df = df.sort_values("Timestamp").copy()
        df["RAPID"] = False
        df["LOC_CONFLICT"] = False
        df["DEVICE_HOP"] = False
        df["SHIFT_VIOL"] = False
        df["HOURLY_SPIKE"] = False
        df["COLOC"] = False

        # Pre-calculate differences for efficient rule checks
        df["Prev_Timestamp"] = df.groupby("Operator_ID")["Timestamp"].shift(1)
        df["Prev_Location"] = df.groupby("Operator_ID")["Location"].shift(1)
        df["Prev_Device"] = df.groupby("Operator_ID")["Device_ID"].shift(1)

        rapid_sec = thresholds.get("rapid_seconds", 60)
        hop_min = thresholds.get("device_hop_minutes", 5)
        hourly_max = thresholds.get("hourly_max", 8)

        # Flag 1: Rapid succession
        df.loc[
            (df["Prev_Timestamp"].notna())
            & ((df["Timestamp"] - df["Prev_Timestamp"]).dt.total_seconds() < rapid_sec),
            "RAPID",
        ] = True

        # Flag 2: Location conflict within 5 minutes
        df.loc[
            (df["Prev_Timestamp"].notna())
            & (df["Prev_Location"] != df["Location"])
            & ((df["Timestamp"] - df["Prev_Timestamp"]).dt.total_seconds() < 300),
            "LOC_CONFLICT",
        ] = True

        # Flag 3: Device hopping within configured window
        df.loc[
            (df["Prev_Device"].notna())
            & (df["Prev_Device"] != df["Device_ID"])
            & ((df["Timestamp"] - df["Prev_Timestamp"]).dt.total_seconds() < hop_min * 60),
            "DEVICE_HOP",
        ] = True

        # Flag 4: Shift violation - tests between 02:00 and 05:00
        df.loc[
            df["Timestamp"].dt.hour.between(2, 4),
            "SHIFT_VIOL",
        ] = True

        # Flag 5: Hourly spike per operator
        counts = (
            df.groupby(["Operator_ID", df["Timestamp"].dt.floor("1H")])["Event_ID"].transform("count")
        )
        df.loc[counts > hourly_max, "HOURLY_SPIKE"] = True

        # Flag 6: Same device and timestamp used by multiple operators
        combo = df["Timestamp"].astype(str) + df["Device_ID"]
        dup_combo = combo.duplicated(keep=False)
        device_dup = df[dup_combo]
        if not device_dup.empty:
            grouped = device_dup.groupby(["Timestamp", "Device_ID"])
            multi_operator = grouped["Operator_ID"].transform("nunique") > 1
            df.loc[device_dup.index[multi_operator], "COLOC"] = True

        df.drop(columns=["Prev_Timestamp", "Prev_Location", "Prev_Device"], inplace=True)
        return df

    def compute_suspicion_scores(df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate flags into operator-level suspicion scores."""
        flag_cols = [
            "RAPID",
            "LOC_CONFLICT",
            "DEVICE_HOP",
            "SHIFT_VIOL",
            "HOURLY_SPIKE",
            "COLOC",
        ]
        weight = 1
        scores = (
            df.groupby("Operator_ID")[flag_cols]
            .sum()
            .assign(Suspicion_Score=lambda x: x.sum(axis=1) * weight)
        )
        conditions = [
            scores["Suspicion_Score"] < 2,
            scores["Suspicion_Score"].between(2, 4),
            scores["Suspicion_Score"] >= 5,
        ]
        levels = ["Low", "Medium", "High"]
        scores["Risk_Level"] = np.select(conditions, levels, default="Low")
        return scores.reset_index()

    def show_timeline(df: pd.DataFrame) -> None:
        """Placeholder timeline visualisation using Altair."""
        if df.empty:
            st.info("No data to display timeline.")
            return
        chart = (
            alt.Chart(df)
            .mark_circle(size=60)
            .encode(
                x="Timestamp:T",
                y=alt.Y("Operator_ID:N", title="Operator"),
                color="Risk_Level:N",
                tooltip=["Location", "Device_ID", "Test_Type"],
            )
            .interactive()
        )
        st.altair_chart(chart, use_container_width=True)

    def show_distribution_charts(df: pd.DataFrame) -> None:
        """Show hourly and daily distribution of tests."""
        if df.empty:
            st.info("No data for distribution charts.")
            return
        hourly = (
            df.assign(Hour=df["Timestamp"].dt.hour)
            .groupby("Hour")
            .size()
            .reset_index(name="Tests")
        )
        daily = (
            df.assign(Day=df["Timestamp"].dt.date)
            .groupby("Day")
            .size()
            .reset_index(name="Tests")
        )
        chart_h = (
            alt.Chart(hourly)
            .mark_bar()
            .encode(x="Hour:O", y="Tests:Q")
            .properties(title="Tests per Hour")
        )
        chart_d = (
            alt.Chart(daily)
            .mark_bar()
            .encode(x="Day:T", y="Tests:Q")
            .properties(title="Tests per Day")
        )
        st.altair_chart(chart_h | chart_d, use_container_width=True)

    def show_heatmap(df: pd.DataFrame) -> None:
        """Show simple device usage heatmap."""
        if df.empty:
            st.info("No data for heatmap.")
            return
        heat = (
            df.assign(Hour=df["Timestamp"].dt.hour)
            .groupby(["Device_ID", "Hour"])
            .size()
            .reset_index(name="Tests")
        )
        chart = (
            alt.Chart(heat)
            .mark_rect()
            .encode(
                x="Hour:O",
                y="Device_ID:N",
                color="Tests:Q",
            )
            .properties(title="Device Usage Heatmap")
        )
        st.altair_chart(chart, use_container_width=True)

    def show_flag_pie(df: pd.DataFrame) -> None:
        """Show breakdown of flag occurrences as a pie chart."""
        flag_cols = [
            "RAPID",
            "LOC_CONFLICT",
            "DEVICE_HOP",
            "SHIFT_VIOL",
            "HOURLY_SPIKE",
            "COLOC",
        ]
        counts = df[flag_cols].sum().reset_index()
        counts.columns = ["Flag", "Count"]
        if counts["Count"].sum() == 0:
            st.info("No flagged events to display.")
            return
        chart = (
            alt.Chart(counts)
            .mark_arc()
            .encode(theta="Count", color="Flag")
            .properties(title="Flag Breakdown")
        )
        st.altair_chart(chart, use_container_width=True)

# ---------------------------------------------------------------------------
# Utility functions specific to this Streamlit application
# ---------------------------------------------------------------------------

REQUIRED_COLUMNS = ["Timestamp", "Operator_ID", "Location", "Device_ID", "Test_Type"]


def load_file(upload) -> pd.DataFrame:
    """Load uploaded CSV or Excel file and validate columns.

    Parameters
    ----------
    upload : UploadedFile
        File object from Streamlit file uploader.

    Returns
    -------
    pd.DataFrame
        Parsed dataframe with timestamps converted and Event_ID assigned.
    """
    if upload is None:
        return pd.DataFrame()

    try:
        if upload.name.lower().endswith(".csv"):
            df = pd.read_csv(upload)
        elif upload.name.lower().endswith((".xls", ".xlsx")):
            df = pd.read_excel(upload)
        else:
            st.error("Unsupported file type. Please upload CSV or XLSX.")
            return pd.DataFrame()
    except Exception as exc:  # pragma: no cover - user errors handled with message
        st.error(f"Error reading file: {exc}")
        return pd.DataFrame()

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
        return pd.DataFrame()

    # Parse timestamps
    try:
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], dayfirst=True, errors="coerce")
    except Exception:
        st.error("Failed to parse timestamps. Ensure format is DD/MM/YYYY HH:MM.")
        return pd.DataFrame()

    bad_rows = df[df["Timestamp"].isna()].index.tolist()
    if bad_rows:
        st.error(
            f"Timestamps could not be parsed for rows: {', '.join(str(i + 2) for i in bad_rows)}"
        )
        return pd.DataFrame()

    df["Event_ID"] = [uuid.uuid4().hex for _ in range(len(df))]
    df.sort_values("Timestamp", inplace=True)
    return df


def filter_dataframe(df: pd.DataFrame, filters: Dict[str, List[str]], date_range) -> pd.DataFrame:
    """Apply sidebar filters to dataframe."""
    if df.empty:
        return df

    if filters.get("Operator_ID"):
        df = df[df["Operator_ID"].isin(filters["Operator_ID"])]
    if filters.get("Location"):
        df = df[df["Location"].isin(filters["Location"])]
    if filters.get("Device_ID"):
        df = df[df["Device_ID"].isin(filters["Device_ID"])]
    if filters.get("Test_Type"):
        df = df[df["Test_Type"].isin(filters["Test_Type"])]
    if date_range:
        start, end = date_range
        df = df[(df["Timestamp"] >= start) & (df["Timestamp"] <= end)]
    return df


def dataframe_to_csv(df: pd.DataFrame) -> str:
    """Convert dataframe to CSV and encode to base64 for download."""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f"data:text/csv;base64,{b64}"
    return href


def build_sidebar() -> Dict[str, int]:
    """Render sidebar controls and return threshold configuration."""
    st.sidebar.image(
        "POCTIFY Logo.png",
        width=100,
    )
    st.sidebar.title("POCTIFY Settings")

    st.sidebar.markdown(
        "Upload anonymised POCT middleware logs. Only non-patient data is allowed."
    )

    upload = st.sidebar.file_uploader(
        "Upload CSV or XLSX", type=["csv", "xls", "xlsx"], key="uploader"
    )

    with st.sidebar.expander("Thresholds"):
        rapid = st.slider(
            "Rapid succession (seconds)", min_value=10, max_value=300, value=60, step=5
        )
        hop = st.slider(
            "Device hopping window (minutes)", min_value=1, max_value=30, value=5, step=1
        )
        hourly = st.slider(
            "Max hourly test count", min_value=1, max_value=20, value=8, step=1
        )
        min_score = st.slider(
            "Minimum suspicion score", min_value=0, max_value=20, value=0, step=1
        )

    with st.sidebar.expander("Instructions"):
        st.markdown(
            """
            1. Upload an anonymised log file containing the required columns.
            2. Adjust thresholds for what constitutes suspicious behaviour.
            3. Use the filters to narrow down results.
            4. Review flagged events and export if necessary.
            """
        )

    with st.sidebar.expander("Privacy"):
        st.write(
            "This tool is for auditing purposes only. Do not upload any data containing patient identifiers."  # noqa: E501
        )

    st.sidebar.download_button(
        label="Download Template",
        data="Timestamp,Operator_ID,Location,Device_ID,Test_Type\n",
        file_name="poct_template.csv",
        mime="text/csv",
    )

    thresholds = {
        "rapid_seconds": rapid,
        "device_hop_minutes": hop,
        "hourly_max": hourly,
        "min_score": min_score,
    }
    return upload, thresholds, filters, date_range


def update_filter_options(df: pd.DataFrame) -> None:
    """Populate filter multiselect options once data is loaded."""
    if df.empty:
        return
    st.sidebar.multiselect(
        "Operator", options=sorted(df["Operator_ID"].unique()), key="Operator_ID"
    )
    st.sidebar.multiselect(
        "Location", options=sorted(df["Location"].unique()), key="Location"
    )
    st.sidebar.multiselect(
        "Device", options=sorted(df["Device_ID"].unique()), key="Device_ID"
    )
    st.sidebar.multiselect(
        "Test Type", options=sorted(df["Test_Type"].unique()), key="Test_Type"
    )


# ---------------------------------------------------------------------------
# Streamlit App Layout and Logic
# ---------------------------------------------------------------------------

st.set_page_config(page_title="POCTIFY Usage Intelligence", layout="wide")

st.title("POCTIFY Usage Intelligence")

upload, thresholds, filters, date_range = build_sidebar()

# Load data if available
raw_df = load_file(upload)
if not raw_df.empty:
    update_filter_options(raw_df)

# Apply filters to raw data
filtered_df = filter_dataframe(raw_df, {
    k: st.session_state.get(k, []) for k in ["Operator_ID", "Location", "Device_ID", "Test_Type"]
}, date_range)

# Apply detection rules
flagged_df = pd.DataFrame()
summary_df = pd.DataFrame()
if not filtered_df.empty:
    flagged_df = apply_rules(filtered_df, thresholds)
    summary_df = compute_suspicion_scores(flagged_df)
    summary_df = summary_df[summary_df["Suspicion_Score"] >= thresholds["min_score"]]

# ---------------------------------------------------------------------------
# Main page displays
# ---------------------------------------------------------------------------

st.header("Data Preview")
if raw_df.empty:
    st.info("Upload data to begin analysis.")
else:
    st.dataframe(raw_df.head(10))

if not flagged_df.empty:
    st.header("Suspicious Operators")
    st.dataframe(summary_df)
    st.markdown("Export flagged events:")
    href = dataframe_to_csv(flagged_df)
    st.download_button("Download CSV", href, "flagged_events.csv")

    st.header("Timeline of Events")
    show_timeline(flagged_df)

    st.header("Distributions")
    show_distribution_charts(flagged_df)

    st.header("Device Usage Heatmap")
    show_heatmap(flagged_df)

    st.header("Flag Breakdown")
    show_flag_pie(flagged_df)

    st.text_area("Notes", "", key="notes", help="Local notes (not uploaded)")
else:
    if not raw_df.empty:
        st.warning("No events matched the filters or thresholds.")

st.markdown(
    """
    ---
    **Disclaimer**: This tool assists NHS POCT audit teams in reviewing middleware
    logs for potential policy breaches. It does not store uploaded files and should
    only be used with anonymised data in compliance with data protection guidelines.
    """
)

