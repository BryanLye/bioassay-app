# -*- coding: utf-8 -*-
"""
Interactive Bioassay Browser & Curation App
Streamlit app for filtering, visualising, and curating PubChem bioassay data.
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


# ── Helpers ───────────────────────────────────────────────────────────────────
def col_options(col):
    vals = df_master[col].dropna().unique().tolist()
    vals = [v for v in vals if v != ""]
    return sorted(vals, key=str)

_FILLER = {"or", "and", "of", "the", "in", "a", "an", "to", "for", "by", "on", "at", "is"}

def title_case(s: str) -> str:
    """Title-case a string, keeping filler words lowercase (except first word)."""
    words = s.replace("_", " ").split()
    result = []
    for i, w in enumerate(words):
        if i == 0 or w.lower() not in _FILLER:
            result.append(w.capitalize())
        else:
            result.append(w.lower())
    return " ".join(result)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filters")

    # AID filter (supports comma-separated or space-separated AIDs)
    aid_input = st.text_input(
        "Filter by AID(s)",
        placeholder="e.g. 1, 3, 5",
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
        label = title_case(col)
        filter_selections[col] = st.multiselect(
            label, options=options, default=[], key=f"filter_{col}"
        )

    st.divider()

    # Single reset button — clears filters and reverts edits
    if st.button("Reset All", use_container_width=True):
        st.cache_data.clear()
        # Clear filter widget keys
        for key in ["aid_input", "search_text"]:
            if key in st.session_state:
                del st.session_state[key]
        for col in FILTER_COLS:
            k = f"filter_{col}"
            if k in st.session_state:
                del st.session_state[k]
        # Revert data
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


# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""<style>
    .main .block-container {
        padding-top: 0.5rem;
        padding-bottom: 1rem;
    }
    [data-testid="stSidebar"] {
        min-width: 200px;
    }
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 3.2rem;
    }
    [data-testid="stSidebar"] [data-testid="stMultiSelect"] {
        margin-bottom: -0.5rem;
    }
    /* Bigger fonts */
    .main .block-container, [data-testid="stSidebar"] {
        font-size: 16px;
    }
    h1 { font-size: 1.8rem !important; margin-bottom: -0.5rem !important; }
    h3 { font-size: 1.2rem !important; }
    /* Centre all data-editor columns except Study Goal (2nd col) */
    [data-testid="stDataEditor"] [data-testid="glide-cell"] {
        text-align: center;
    }
    [data-testid="stDataEditor"] [data-testid="glide-cell"]:nth-child(2) {
        text-align: left;
    }
    /* Compact caption */
    .main .block-container [data-testid="stCaptionContainer"] {
        margin-bottom: -0.5rem;
    }
</style>""", unsafe_allow_html=True)

# ── Main area ─────────────────────────────────────────────────────────────────
st.title("Bioassay Browser & Curation Tool")
st.caption(
    f"Showing **{len(filtered)}** of **{len(df_master)}** assays "
    f"| {st.session_state.edit_count} unsaved edit(s)"
)

# ── Editable data table ──────────────────────────────────────────────────────
# Build column config
column_config = {
    "AID": st.column_config.NumberColumn("AID", disabled=True, format="%d"),
}

for col in CONSTRAINED_COLS:
    options = col_options(col)
    column_config[col] = st.column_config.SelectboxColumn(
        title_case(col),
        options=options,
        required=False,
    )

for col in TEXT_COLS:
    column_config[col] = st.column_config.TextColumn(
        title_case(col),
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
    height=1000,
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

# ── Download ──────────────────────────────────────────────────────────────────
st.divider()

@st.dialog("Download filtered data")
def download_dialog():
    filename = st.text_input("File name", value="filtered_bioassay_data")
    fmt = st.radio("Format", ["Excel (.xlsx)", "CSV (.csv)"], horizontal=True)
    safe_name = "".join(c for c in filename if c.isalnum() or c in "-_ ").strip()
    if not safe_name:
        safe_name = "filtered_bioassay_data"
    buf = BytesIO()
    if fmt == "CSV (.csv)":
        buf.write(filtered.to_csv(index=False).encode("utf-8"))
        buf.seek(0)
        st.download_button(
            label=f"Download {len(filtered)} rows as CSV",
            data=buf,
            file_name=f"{safe_name}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        filtered.to_excel(buf, index=False, engine="openpyxl")
        buf.seek(0)
        st.download_button(
            label=f"Download {len(filtered)} rows as Excel",
            data=buf,
            file_name=f"{safe_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

if st.button(f"Download {len(filtered)} rows", type="primary"):
    download_dialog()
