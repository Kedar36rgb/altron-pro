import hashlib
import html
import io
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from altron.ops import apply_plan
from altron.llm import plan_cleaning, plan_chart, plan_pivot, plan_formula
from altron.charts import render
from altron.pivots import build_pivot
from altron.quality import quality_report
from altron.limits import allow

st.set_page_config(page_title="Altron Pro", page_icon="◆", layout="wide")

# ---------------------------------------------------------------
# DESIGN TOKENS
# ink = sidebar and hero, cobalt = the one action colour,
# mint / amber = good / needs attention, paper = page background
# ---------------------------------------------------------------
COBALT, INK, MINT, AMBER = "#2457F5", "#0B1B2B", "#12B886", "#F59F00"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');

:root{
  --ink:#0B1B2B; --ink-2:#14283D; --cobalt:#2457F5; --cobalt-soft:#E8EEFE;
  --mint:#12B886; --amber:#F59F00; --paper:#F4F6F9; --line:#DDE3EA; --muted:#5B6B7C;
}
.stApp, .stApp p, .stApp label, .stApp button, .stApp input, .stApp textarea,
.stApp h1, .stApp h2, .stApp h3, .stApp h4 { font-family:'Manrope', sans-serif; }
.stApp { background:var(--paper); }
header[data-testid="stHeader"] { background:transparent; }
.block-container { padding-top:1.6rem; max-width:1240px; }
h2, h3 { color:var(--ink); letter-spacing:-0.01em; }

/* ---------- sidebar ---------- */
section[data-testid="stSidebar"] { background:var(--ink); border-right:1px solid #1d3349; }
section[data-testid="stSidebar"] * { color:#DCE6F1; }
section[data-testid="stSidebar"] hr { border-color:rgba(255,255,255,.12); }
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
  background:var(--ink-2) !important; border:1px dashed #3a5673; border-radius:10px; }
section[data-testid="stSidebar"] [data-testid="stFileUploader"] div { background-color:transparent; }
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button {
  background:transparent; border:1px solid #3a5673; }
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button:hover {
  border-color:var(--cobalt); }
section[data-testid="stSidebar"] [data-testid="stFileUploaderFile"],
section[data-testid="stSidebar"] [data-testid="stFileUploaderFileData"] {
  background:var(--ink-2); border-radius:8px; }
section[data-testid="stSidebar"] .stButton > button {
  background:var(--ink-2); border:1px solid #3a5673; color:#DCE6F1; }
section[data-testid="stSidebar"] .stButton > button:hover { border-color:var(--cobalt); color:#fff; }
.brand { display:flex; align-items:center; gap:10px; margin:4px 0 6px 0; }
.brand .mark { width:30px; height:30px; border-radius:8px; background:var(--cobalt);
  display:flex; align-items:center; justify-content:center; font-weight:800; color:#fff !important; }
.brand .name { font-weight:800; font-size:1.2rem; color:#fff !important; letter-spacing:-0.01em; }
.side-note { font-size:.82rem; color:#93A8BD !important; line-height:1.45; }

/* ---------- hero (empty state) ---------- */
.hero { background:var(--ink); border-radius:14px; padding:2.4rem 2.6rem; margin-bottom:1.4rem; }
.hero h1 { color:#fff !important; font-weight:800; font-size:2.25rem; line-height:1.15;
  letter-spacing:-0.02em; margin:0 0 .6rem 0; padding:0; max-width:640px; }
.hero p { color:#B7C7D8; font-size:1.02rem; margin:0 0 1.5rem 0; max-width:560px; }
.steps { display:flex; gap:12px; flex-wrap:wrap; }
.step-pill { display:flex; align-items:center; gap:10px; background:var(--ink-2);
  border:1px solid #23415c; border-radius:10px; padding:.65rem .95rem; color:#E6EEF6; font-weight:600; font-size:.92rem; }
.step-pill b { background:var(--cobalt); color:#fff; width:24px; height:24px; border-radius:50%;
  display:inline-flex; align-items:center; justify-content:center; font-size:.8rem; }

/* ---------- feature tiles ---------- */
.tile { background:#fff; border:1px solid var(--line); border-radius:10px; padding:1rem 1.05rem; height:100%;
  transition:border-color .15s ease; }
.tile:hover { border-color:var(--cobalt); }
.tile h4 { margin:0 0 .3rem 0; font-size:.98rem; color:var(--ink); }
.tile p { margin:0; font-size:.85rem; color:var(--muted); line-height:1.45; }

/* ---------- file bar and chips ---------- */
.filebar { display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-bottom:1rem; }
.chip { display:inline-block; background:var(--cobalt-soft); color:var(--cobalt); font-weight:600;
  font-size:.82rem; padding:.28rem .7rem; border-radius:999px; }
.chip.file { background:var(--ink); color:#fff; }
.chip.op { background:#fff; border:1px solid var(--line); color:var(--ink); font-family:ui-monospace, Menlo, monospace; }

/* ---------- metrics ---------- */
div[data-testid="stMetric"] { background:#fff; border:1px solid var(--line); border-radius:10px; padding:.85rem 1rem; }
div[data-testid="stMetricLabel"] p { color:var(--muted); font-weight:600; font-size:.85rem; }
div[data-testid="stMetricValue"] { color:var(--ink); font-weight:800; }

/* ---------- containers ---------- */
div[data-testid="stVerticalBlockBorderWrapper"] { background:#fff; border-radius:12px; border-color:var(--line); }

/* ---------- tabs ---------- */
.stTabs [data-baseweb="tab-list"] { gap:6px; background:#fff; padding:5px; border:1px solid var(--line);
  border-radius:12px; width:fit-content; }
.stTabs [data-baseweb="tab"] { height:auto; padding:.5rem 1.05rem; border-radius:8px; font-weight:700; color:var(--muted); }
.stTabs [data-baseweb="tab"]:hover { color:var(--ink); background:var(--paper); }
.stTabs [aria-selected="true"] { background:var(--ink) !important; color:#fff !important; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display:none; }

/* ---------- buttons ---------- */
.stButton > button, .stDownloadButton > button { border-radius:8px; font-weight:700; border:1px solid var(--line);
  background:#fff; color:var(--ink); transition:border-color .15s ease, transform .1s ease; }
.stButton > button:hover, .stDownloadButton > button:hover { border-color:var(--cobalt); color:var(--cobalt); }
.stButton > button:active { transform:scale(.98); }
.stButton > button[kind="primary"], button[data-testid="stBaseButton-primary"] {
  background:var(--cobalt); border-color:var(--cobalt); color:#fff; }
.stButton > button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover {
  background:#1844d1; border-color:#1844d1; color:#fff; }

/* ---------- inputs ---------- */
.stTextInput input { border-radius:8px; border:1px solid var(--line); padding:.65rem .8rem; }
.stTextInput input:focus { border-color:var(--cobalt); box-shadow:0 0 0 3px var(--cobalt-soft); }

/* ---------- applied steps timeline ---------- */
.timeline { border-left:2px solid var(--line); margin-left:12px; padding-left:18px; }
.tl-item { position:relative; padding:.2rem 0 .9rem 0; color:var(--ink); font-size:.93rem; }
.tl-item .dot { position:absolute; left:-31px; top:.15rem; width:24px; height:24px; border-radius:50%;
  background:var(--mint); color:#fff; font-size:.75rem; font-weight:800; display:flex; align-items:center; justify-content:center; }
.section-sub { color:var(--muted); font-size:.92rem; margin:-.4rem 0 .9rem 0; }
.footer { text-align:center; color:#8896A6; font-size:.8rem; margin:2.5rem 0 .5rem 0; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------
# STATE
# ---------------------------------------------------------------
DEFAULTS = {
    "fid": None, "fname": None, "last_upload_fid": None,
    "original": None, "history": [], "pending": None,
    "chart_spec": None, "pivot_spec": None, "formula_result": None,
    "clean_req": "", "chart_req": "", "pivot_req": "", "formula_req": "",
}
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)


def load_bytes(data: bytes, name: str):
    fid = hashlib.md5(data).hexdigest()
    if st.session_state.fid != fid:
        reader = pd.read_csv if name.lower().endswith(".csv") else pd.read_excel
        st.session_state.update(
            fid=fid, fname=name, original=reader(io.BytesIO(data)),
            history=[], pending=None, chart_spec=None, pivot_spec=None,
            formula_result=None, clean_req="", chart_req="", pivot_req="", formula_req="",
        )


def current_df():
    df = st.session_state.original
    for plan in st.session_state.history:
        df = apply_plan(df, plan)
    return df


def use_suggestion(key, text):
    st.session_state[key] = text


def apply_pending():
    """Runs before widgets are built, so it can safely clear the prompt box."""
    plan, _ = st.session_state.pending
    st.session_state.history.append(plan)
    st.session_state.pending = None
    st.session_state.clean_req = ""
    st.toast("Changes applied", icon="✅")


def discard_pending():
    st.session_state.pending = None


def undo_last():
    if st.session_state.history:
        st.session_state.history.pop()
        st.toast("Last step undone", icon="↩️")


def reset_all():
    for k, v in DEFAULTS.items():
        if k == "last_upload_fid":
            continue  # keeps an attached upload from instantly reloading
        st.session_state[k] = [] if isinstance(v, list) else v


def suggestion_row(options, prefix, target_key):
    """Clickable chips that fill the prompt box for the user."""
    if not options:
        return
    st.caption("Try one of these")
    cols = st.columns(len(options))
    for i, (col, text) in enumerate(zip(cols, options)):
        col.button(text, key=f"{prefix}_{i}", on_click=use_suggestion, args=(target_key, text))


def pick_columns(df):
    nums = list(df.select_dtypes(include="number").columns)
    cats = [c for c in df.select_dtypes(exclude="number").columns if df[c].nunique() <= 30]
    return nums, cats


# ---------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------
with st.sidebar:
    st.markdown(
        '<div class="brand"><div class="mark">A</div><div class="name">Altron Pro</div></div>'
        '<div class="side-note">Natural language data cleaning with a preview before every change.</div>',
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown("**Your data**")
    uploaded_file = st.file_uploader("CSV or Excel file", type=["csv", "xlsx"], label_visibility="collapsed")
    if uploaded_file is not None:
        raw = uploaded_file.getvalue()
        ufid = hashlib.md5(raw).hexdigest()
        if ufid != st.session_state.last_upload_fid:
            st.session_state.last_upload_fid = ufid
            load_bytes(raw, uploaded_file.name)

    st.divider()
    st.markdown("**Privacy**")
    share = st.toggle("Share 3 sample values per column with the AI", value=False)
    st.markdown(
        '<div class="side-note">Off: only column names, types and missing-value rates are sent. '
        "On: results improve, but a few real values leave your machine.</div>",
        unsafe_allow_html=True,
    )

    st.divider()
    usage_slot = st.empty()  # filled at the end of the script so it is never one click behind

    if st.session_state.original is not None:
        st.button("Start over with new data", on_click=reset_all)

def draw_usage():
    used = st.session_state.get("calls", 0)
    with usage_slot.container():
        st.markdown(f"**AI calls this session:** {used} of 20")
        st.progress(min(used / 20, 1.0))


# ---------------------------------------------------------------
# EMPTY STATE
# ---------------------------------------------------------------
if st.session_state.original is None:
    st.markdown(
        """
<div class="hero">
<h1>Clean, chart and summarise your data in plain English</h1>
<p>Describe what you want. Altron plans it, shows you a preview, and changes your data only after you approve.</p>
<div class="steps">
<div class="step-pill"><b>1</b>Upload or pick a sample</div>
<div class="step-pill"><b>2</b>Describe the change</div>
<div class="step-pill"><b>3</b>Review and approve</div>
</div>
</div>
""",
        unsafe_allow_html=True,
    )

    samples = sorted(Path("data").glob("*.csv"))[:4]
    if samples:
        st.markdown("### Start with a sample")
        st.markdown('<div class="section-sub">No file handy? Load one and try the tabs.</div>', unsafe_allow_html=True)
        cols = st.columns(len(samples))
        for col, path in zip(cols, samples):
            if col.button(f"Load {path.stem}", key=f"sample_{path.stem}", type="primary"):
                load_bytes(path.read_bytes(), path.name)
                st.rerun()
    else:
        st.info("Upload a CSV or Excel file in the sidebar. Put sample CSVs in a data/ folder to get one-click demos here.")

    st.markdown("### What you can do")
    tiles = [
        ("Cleaning", "Fix missing values, duplicates, casing and types. Undo any step."),
        ("Charts", "Ask for a chart in a sentence, then edit the spec."),
        ("Pivots", "Summarise by any columns without writing code."),
        ("Formulas", "Get Excel or Sheets formulas that use your real columns."),
        ("EDA", "Statistics, missing values and correlations at a glance."),
    ]
    for col, (title, text) in zip(st.columns(5), tiles):
        col.markdown(f'<div class="tile"><h4>{title}</h4><p>{text}</p></div>', unsafe_allow_html=True)

    st.markdown('<div class="footer">Altron Pro</div>', unsafe_allow_html=True)
    draw_usage()
    st.stop()

# ---------------------------------------------------------------
# LOADED STATE
# ---------------------------------------------------------------
df = current_df()
nums, cats = pick_columns(df)

st.markdown(
    f'<div class="filebar"><span class="chip file">{html.escape(str(st.session_state.fname))}</span>'
    f'<span class="chip">{len(df):,} rows</span><span class="chip">{df.shape[1]} columns</span>'
    f'<span class="chip">{len(st.session_state.history)} step{"s" if len(st.session_state.history) != 1 else ""} applied</span></div>',
    unsafe_allow_html=True,
)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Cleaning", "Charts", "Pivots", "Formulas", "EDA"])

# ---------------------------------------------------------------
# TAB 1: CLEANING
# ---------------------------------------------------------------
with tab1:
    quality = quality_report(df)
    base_score = quality_report(st.session_state.original)["score"]

    left, right = st.columns([1, 1.6], gap="large")
    with left:
        with st.container(border=True):
            st.markdown("#### Data quality")
            score = quality["score"]
            fig = go.Figure(go.Indicator(
                mode="gauge+number", value=score,
                number={"font": {"size": 44, "color": INK}, "suffix": " / 100"},
                gauge={
                    "axis": {"range": [0, 100], "tickcolor": "#9AA8B6"},
                    "bar": {"color": COBALT, "thickness": 0.28},
                    "bgcolor": "white", "borderwidth": 0,
                    "steps": [
                        {"range": [0, 50], "color": "#FDE3E3"},
                        {"range": [50, 80], "color": "#FEF0CC"},
                        {"range": [80, 100], "color": "#D3F5E6"},
                    ],
                },
            ))
            fig.update_layout(height=210, margin=dict(l=20, r=20, t=20, b=0), paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, width="stretch")
            delta = score - base_score
            if delta > 0:
                st.success(f"Up {delta} points since you uploaded this file.")
            elif quality["mostly_empty_columns"]:
                st.warning("Mostly empty: " + ", ".join(map(str, quality["mostly_empty_columns"])))
            else:
                st.caption("Apply cleaning steps and watch the score move.")
    with right:
        m1, m2 = st.columns(2)
        m1.metric("Missing values", f"{quality['missing_pct']}%")
        m2.metric("Duplicate rows", quality["duplicate_rows"])
        m3, m4 = st.columns(2)
        m3.metric("Constant columns", len(quality["constant_columns"]))
        m4.metric("Shape", f"{len(df):,} × {df.shape[1]}")
        st.dataframe(df.head(8), width="stretch", height=250)

    st.markdown("### Describe the cleaning you want")
    st.markdown('<div class="section-sub">Altron proposes a plan. Nothing changes until you apply it.</div>', unsafe_allow_html=True)

    tips = []
    if quality["duplicate_rows"]:
        tips.append("Remove duplicate rows")
    null_cols = [c for c in df.columns if df[c].isna().any()]
    for c in null_cols[:2]:
        how = "the median" if c in nums else "the most common value"
        tips.append(f"Fill missing values in {c} with {how}")
    if not tips:
        tips.append("Trim extra spaces in all text columns")
    suggestion_row(tips[:3], "tip_clean", "clean_req")

    st.text_input("Cleaning request", key="clean_req", label_visibility="collapsed",
                  placeholder="For example: fill missing ages with the mean and lowercase the Name column")
    if st.button("Plan it", type="primary") and st.session_state.clean_req:
        if allow():
            with st.spinner("Planning your changes..."):
                try:
                    st.session_state.pending = plan_cleaning(df, st.session_state.clean_req, share)
                except RuntimeError as e:
                    st.error(str(e))
        else:
            st.warning("Demo limit reached. Run it locally with your own key for unlimited use.")

    if st.session_state.pending:
        plan, preview = st.session_state.pending
        with st.container(border=True):
            st.markdown("#### Proposed plan")
            st.write(plan.explanation)
            chips = "".join(f'<span class="chip op">{html.escape(o.op)}</span> ' for o in plan.operations)
            st.markdown(chips or '<span class="chip">No operations proposed</span>', unsafe_allow_html=True)
            with st.expander("See the exact operations"):
                st.json([o.model_dump() for o in plan.operations])

            c1, c2, c3 = st.columns(3)
            c1.metric("Rows", f"{len(preview):,}", delta=len(preview) - len(df))
            c2.metric("Columns", preview.shape[1], delta=preview.shape[1] - df.shape[1])
            c3.metric("Quality", quality_report(preview)["score"], delta=quality_report(preview)["score"] - score)
            st.dataframe(preview.head(10), width="stretch")

            a, b, _ = st.columns([1, 1, 3])
            a.button("Apply changes", type="primary", on_click=apply_pending)
            b.button("Discard", on_click=discard_pending)

    if st.session_state.history:
        st.markdown("### Applied steps")
        items = "".join(
            f'<div class="tl-item"><div class="dot">{i + 1}</div>{html.escape(p.explanation)}</div>'
            for i, p in enumerate(st.session_state.history)
        )
        st.markdown(f'<div class="timeline">{items}</div>', unsafe_allow_html=True)
        st.button("Undo last step", on_click=undo_last)

    st.markdown("### Export")
    e1, e2, _ = st.columns([1, 1, 2])
    e1.download_button("Download cleaned CSV", df.to_csv(index=False), "cleaned.csv", mime="text/csv")
    e2.download_button(
        "Download recipe (JSON)",
        json.dumps([p.model_dump() for p in st.session_state.history], indent=2),
        "recipe.json", mime="application/json",
    )

# ---------------------------------------------------------------
# TAB 2: CHARTS
# ---------------------------------------------------------------
with tab2:
    st.markdown("### Describe the chart you want")
    st.markdown('<div class="section-sub">The generated spec is shown below the chart so you can see what the AI chose.</div>', unsafe_allow_html=True)
    ideas = []
    if nums and cats:
        ideas += [f"Bar chart of average {nums[0]} by {cats[0]}", f"Pie chart of total {nums[0]} by {cats[0]}"]
    if nums:
        ideas.append(f"Histogram of {nums[0]}")
    if len(nums) > 1:
        ideas.append(f"Scatter plot of {nums[0]} against {nums[1]}")
    suggestion_row(ideas[:3], "tip_chart", "chart_req")

    st.text_input("Chart request", key="chart_req", label_visibility="collapsed",
                  placeholder="For example: bar chart of average salary by city")
    if st.button("Generate chart", type="primary") and st.session_state.chart_req:
        if allow():
            with st.spinner("Building your chart..."):
                try:
                    st.session_state.chart_spec = plan_chart(df, st.session_state.chart_req, share)
                except Exception as e:
                    st.error(f"Could not build the chart: {e}")
        else:
            st.warning("Demo limit reached.")

    if st.session_state.chart_spec:
        spec = st.session_state.chart_spec
        with st.container(border=True):
            try:
                fig = render(df, spec)
                fig.update_layout(
                    template="plotly_white", font_family="Manrope",
                    colorway=[COBALT, MINT, AMBER, "#7C5CFF", "#E5484D", "#0B1B2B"],
                    margin=dict(l=10, r=10, t=50, b=10),
                )
                fig.update_traces(marker_color=COBALT, selector=dict(type="bar"))
                st.plotly_chart(fig, width="stretch")
            except Exception as e:
                st.error(f"Could not render this chart: {e}")
        with st.expander("View chart spec"):
            st.json(spec.model_dump())

# ---------------------------------------------------------------
# TAB 3: PIVOTS
# ---------------------------------------------------------------
with tab3:
    st.markdown("### Describe the pivot table")
    st.markdown('<div class="section-sub">Summarise your data by any columns.</div>', unsafe_allow_html=True)
    pideas = []
    if nums and cats:
        pideas += [f"Sum of {nums[0]} by {cats[0]}", f"Average {nums[0]} by {cats[0]}"]
        if len(cats) > 1:
            pideas.append(f"Sum of {nums[0]} by {cats[0]} and {cats[1]}")
    suggestion_row(pideas[:3], "tip_pivot", "pivot_req")

    st.text_input("Pivot request", key="pivot_req", label_visibility="collapsed",
                  placeholder="For example: sum of sales by region and month")
    if st.button("Generate pivot", type="primary") and st.session_state.pivot_req:
        if allow():
            with st.spinner("Building your pivot..."):
                try:
                    st.session_state.pivot_spec = plan_pivot(df, st.session_state.pivot_req, share)
                except Exception as e:
                    st.error(f"Could not build the pivot: {e}")
        else:
            st.warning("Demo limit reached.")

    if st.session_state.pivot_spec:
        spec = st.session_state.pivot_spec
        with st.container(border=True):
            try:
                result = build_pivot(df, spec)
                st.dataframe(result, width="stretch", hide_index=isinstance(result.index, pd.RangeIndex))
                st.download_button("Download pivot (CSV)", result.to_csv(index=not isinstance(result.index, pd.RangeIndex)), "pivot.csv", mime="text/csv")
            except Exception as e:
                st.error(f"Could not build this pivot: {e}")
        with st.expander("View pivot spec"):
            st.json(spec.model_dump())

# ---------------------------------------------------------------
# TAB 4: FORMULAS
# ---------------------------------------------------------------
with tab4:
    st.markdown("### Get a formula that uses your columns")
    st.markdown('<div class="section-sub">Column letters follow the order of your file, with headers in row 1.</div>', unsafe_allow_html=True)
    dialect = st.radio("Spreadsheet", ["Excel", "Google Sheets"], horizontal=True)
    fideas = []
    if nums:
        fideas.append(f"Double the value in {nums[0]}")
    if cats:
        fideas.append(f"Extract the first word from {cats[0]}")
    suggestion_row(fideas[:2], "tip_formula", "formula_req")

    st.text_input("Formula request", key="formula_req", label_visibility="collapsed",
                  placeholder="For example: multiply Age by 2")
    if st.button("Write formula", type="primary") and st.session_state.formula_req:
        if allow():
            with st.spinner("Writing your formula..."):
                try:
                    st.session_state.formula_result = plan_formula(df, st.session_state.formula_req, dialect)
                except Exception as e:
                    st.error(f"Could not write the formula: {e}")
        else:
            st.warning("Demo limit reached.")

    if st.session_state.formula_result:
        res = st.session_state.formula_result
        with st.container(border=True):
            st.markdown("#### Your formula")
            st.code(res.formula, language="excel")
            st.write(res.explanation)

# ---------------------------------------------------------------
# TAB 5: EDA
# ---------------------------------------------------------------
with tab5:
    numeric_df = df.select_dtypes(include=["number"])
    st.markdown("### Descriptive statistics")
    if not numeric_df.empty:
        st.dataframe(numeric_df.describe().T, width="stretch")
    else:
        st.info("No numeric columns to summarise.")

    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("### Missing values")
        missing = (df.isna().mean() * 100)
        missing = missing[missing > 0].reset_index()
        missing.columns = ["Column", "Missing %"]
        if not missing.empty:
            fig_m = px.bar(missing, x="Missing %", y="Column", orientation="h",
                           color_discrete_sequence=[AMBER], template="plotly_white")
            fig_m.update_layout(font_family="Manrope", margin=dict(l=10, r=10, t=10, b=10), height=320)
            st.plotly_chart(fig_m, width="stretch")
        else:
            st.success("No missing values found.")
    with c2:
        st.markdown("### Correlations")
        if len(numeric_df.columns) > 1:
            fig_c = px.imshow(numeric_df.corr(), text_auto=".2f", aspect="auto",
                              color_continuous_scale=[[0, AMBER], [0.5, "#FFFFFF"], [1, COBALT]],
                              zmin=-1, zmax=1, template="plotly_white")
            fig_c.update_layout(font_family="Manrope", margin=dict(l=10, r=10, t=10, b=10), height=320)
            st.plotly_chart(fig_c, width="stretch")
        else:
            st.info("Needs at least two numeric columns.")

st.markdown('<div class="footer">Altron Pro</div>', unsafe_allow_html=True)
draw_usage()