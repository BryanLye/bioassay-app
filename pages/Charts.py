# -*- coding: utf-8 -*-
"""
Charts page — view one chart at a time from the filtered bioassay data.
"""

import streamlit as st
import altair as alt
import pandas as pd

st.set_page_config(
    page_title="Charts – Bioassay Browser",
    layout="wide",
)

# ── Auth check ────────────────────────────────────────────────────────────────
if not st.session_state.get("authenticated", False):
    st.warning("Please log in on the main page first.")
    st.stop()

# ── Get filtered data from session state ──────────────────────────────────────
if "filtered" not in st.session_state or st.session_state.filtered is None:
    st.info("No data loaded yet. Go to the main page to load data and apply filters.")
    st.stop()

filtered = st.session_state.filtered

# ── Chart options ─────────────────────────────────────────────────────────────
CHART_OPTIONS = {
    "Study Categories": "Study_Categories",
    "Study Source": "Study_Source",
    "Tissue Origin": "Tissue_origin",
    "Detection Technology": "Detection_technology",
}

st.title("📊 Charts")
st.caption(f"Based on **{len(filtered)}** filtered assays")

selected_chart = st.selectbox(
    "Select a chart to display",
    options=list(CHART_OPTIONS.keys()),
    key="chart_selector",
)

data_col = CHART_OPTIONS[selected_chart]

# ── Build chart ───────────────────────────────────────────────────────────────
counts = filtered[data_col].value_counts().reset_index()
counts.columns = ["Category", "Count"]

if counts.empty or (len(counts) == 1 and counts.iloc[0]["Category"] == ""):
    st.write(f"**{selected_chart}** — no data for current filters")
else:
    # Remove empty-string rows
    counts = counts[counts["Category"] != ""]
    n_bars = len(counts)
    chart_height = max(250, n_bars * 28 + 60)

    chart = (
        alt.Chart(counts)
        .mark_bar(cornerRadiusEnd=4)
        .encode(
            x=alt.X("Count:Q", title="Count"),
            y=alt.Y("Category:N", sort="-x", title=None),
            color=alt.Color(
                "Count:Q",
                scale=alt.Scale(scheme="blues"),
                legend=None,
            ),
            tooltip=["Category", "Count"],
        )
        .properties(title=selected_chart, height=chart_height)
        .configure_axis(labelFontSize=14, titleFontSize=15)
        .configure_title(fontSize=17)
    )
    st.altair_chart(chart, use_container_width=True)
