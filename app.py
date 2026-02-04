# -*- coding: utf-8 -*-
"""
Interactive Bioassay Browser & Curation App
Streamlit app for filtering, visualising, and curating PubChem bioassay data.
Table-first layout with charts on a separate page.
"""

import re
import streamlit as st
import pandas as pd
from io import BytesIO
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
EXCEL_PATH = Path(__file__).parent / "PubChem_600Bioassays_Curated.xlsx"

st.set_page_config(
    page_title="Bioassay Browser",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Password gate ─────────────────────────────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 Bioassay Browser")
    pw = st.text_input("Enter password to continue:", type="password")
    if pw == st.secrets["APP_PASSWORD"]:
        st.session_state.authenticated = True
        st.rerun()
    elif pw:
        st.error("Incorrect password.")
    st.stop()

# ── Column definitions ────────────────────────────────────────────────────────
# Columns that get multiselect sidebar filters
FILTER_COLS = [
    "Study_Categories",
    "Study_Source",
    "Experimental_context",
    "Assay_system_type",
    "Experimental_host_species",
    "Cell_model_type",
    "Tissue_origin",
    "Mouse_strain",
    "Detection_technology",
    "Assay_outcome",
]

# Columns with constrained dropdown editing (SelectboxColumn)
CONSTRAINED_COLS = [
    "Study_Categories",
    "Study_Source",
    "Experimental_context",
    "Assay_system_type",
    "Experimental_host_species",
    "Cell_model_type",
    "Tissue_origin",
    "Mouse_strain",
    "Detection_technology",
    "Assay_outcome",
]

# Free-text columns (TextColumn)
TEXT_COLS = [
    "Study_Goal",
    "Cell_models_used",
    "Detection_assay_or_reagent",
    "Assay_readout",
]


# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data
def load_excel():
    """Read the Excel file once and cache it."""
    df = pd.read_excel(EXCEL_PATH, engine="openpyxl")
    df["AID"] = df["AID"].astype(int)
    # Fill NaN with empty string for text columns to avoid issues
    for col in df.columns:
        if col != "AID":
            df[col] = df[col].fillna("")
    return df


def init_state():
    """Initialise session state with a mutable copy of the data."""
    if "df" not in st.session_state:
        st.session_state.df = load_excel().copy()
    if "edit_count" not in st.session_state:
        st.session_state.edit_count = 0


init_state()
df_master = st.session_state.df  # mutable reference


# ── Helper: unique sorted options for a column ────────────────────────────────
def col_options(col):
    vals = df_master[col].dropna().unique().tolist()
    vals = [v for v in vals if v != ""]
    return sorted(vals, key=str)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filters")

    # AID filter (supports comma-separated, newline-separated, or single AID)
    aid_input = st.text_area(
        "Filter by AID(s)",
        placeholder="Paste AIDs here…\ne.g. 1, 3, 5 or one per line",
        height=80,
        key="aid_input",
    )

    # Text search on Study_Goal
    search_text = st.text_input(
        "Search Study_Goal",
        placeholder="Type to search...",
        key="search_text",
    )

    # Multiselect filters
    filter_selections = {}
    for col in FILTER_COLS:
        options = col_options(col)
        label = col.replace("_", " ")
        filter_selections[col] = st.multiselect(
            label, options=options, default=[], key=f"filter_{col}"
        )

    st.divider()

    # Reset Filters
    if st.button("Reset Filters", use_container_width=True):
        st.session_state.aid_input = ""
        st.session_state.search_text = ""
        for col in FILTER_COLS:
            st.session_state[f"filter_{col}"] = []
        st.rerun()

    # Revert all edits
    if st.button("Revert All Changes", type="secondary", use_container_width=True):
        st.cache_data.clear()
        st.session_state.df = load_excel().copy()
        st.session_state.edit_count = 0
        st.rerun()


# ── Parse AID input ──────────────────────────────────────────────────────────
def parse_aids(text):
    """Extract integer AIDs from free-text input (comma / newline / space separated)."""
    if not text or not text.strip():
        return []
    # Find all integer-like tokens
    tokens = re.findall(r"\d+", text)
    return [int(t) for t in tokens]


# ── Apply filters ─────────────────────────────────────────────────────────────
def apply_filters(df):
    mask = pd.Series(True, index=df.index)

    # AID filter
    aid_list = parse_aids(aid_input)
    if aid_list:
        mask &= df["AID"].isin(aid_list)

    # Text search (case-insensitive substring)
    if search_text:
        mask &= df["Study_Goal"].str.contains(search_text, case=False, na=False)

    # Multiselect filters (OR within column, AND across columns)
    for col, selected in filter_selections.items():
        if selected:
            mask &= df[col].isin(selected)

    return df[mask]


filtered = apply_filters(df_master)

# Store filtered data in session state so Charts page can access it
st.session_state.filtered = filtered

# ── Custom CSS for larger fonts ───────────────────────────────────────────────
st.markdown("""<style>
    .main .block-container { font-size: 16px; }
    [data-testid="stSidebar"] { font-size: 14px; }
    h1 { font-size: 2rem !important; }
    h3 { font-size: 1.2rem !important; }
</style>""", unsafe_allow_html=True)

# ── Main area ─────────────────────────────────────────────────────────────────
st.title("Bioassay Browser & Curation Tool")
st.caption(
    f"Showing **{len(filtered)}** of **{len(df_master)}** assays "
    f"| {st.session_state.edit_count} unsaved edit(s)"
)

# ── Editable data table ──────────────────────────────────────────────────────
st.subheader("Data Table")

# Build column config
column_config = {
    "AID": st.column_config.NumberColumn("AID", disabled=True, format="%d"),
}

for col in CONSTRAINED_COLS:
    options = col_options(col)
    column_config[col] = st.column_config.SelectboxColumn(
        col.replace("_", " "),
        options=options,
        required=False,
    )

for col in TEXT_COLS:
    column_config[col] = st.column_config.TextColumn(
        col.replace("_", " "),
        width="large" if col == "Study_Goal" else "medium",
    )

# Snapshot of filtered data before editing (for change detection)
filtered_snap = filtered.reset_index(drop=True).copy()

# Display editor
edited = st.data_editor(
    filtered_snap,
    column_config=column_config,
    use_container_width=True,
    num_rows="fixed",
    height=800,
    key="data_editor",
)

# Propagate edits back to session state (only actual changes)
if edited is not None:
    for i, row in edited.iterrows():
        aid = row["AID"]
        snap_row = filtered_snap.iloc[i]
        changed = False
        for col in df_master.columns:
            if col == "AID":
                continue
            if str(row[col]) != str(snap_row[col]):
                changed = True
                break
        if changed:
            master_idx = df_master.index[df_master["AID"] == aid]
            if len(master_idx) > 0:
                mi = master_idx[0]
                for col in df_master.columns:
                    if col == "AID":
                        continue
                    if str(row[col]) != str(snap_row[col]):
                        df_master.at[mi, col] = row[col]
                        st.session_state.edit_count += 1

# ── Save & Export (compact) ───────────────────────────────────────────────────
st.divider()
save_col, spacer, export_col = st.columns([2, 0.5, 3])

with save_col:
    if st.button("Save all changes to Excel", type="primary", use_container_width=True):
        try:
            df_master.to_excel(EXCEL_PATH, index=False, engine="openpyxl")
            st.session_state.edit_count = 0
            st.success(f"Saved {len(df_master)} rows.")
        except PermissionError:
            st.error("Cannot save — close the Excel file first.")

with export_col:
    fn_col, dl_col = st.columns([2, 2])
    with fn_col:
        filename = st.text_input(
            "Filename",
            value="filtered_bioassay_data",
            key="export_filename",
            label_visibility="collapsed",
            placeholder="Export filename...",
        )
    with dl_col:
        buffer = BytesIO()
        filtered.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)
        safe_name = "".join(c for c in filename if c.isalnum() or c in "-_ ").strip()
        if not safe_name:
            safe_name = "filtered_bioassay_data"
        st.download_button(
            label=f"Download {len(filtered)} rows (.xlsx)",
            data=buffer,
            file_name=f"{safe_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
