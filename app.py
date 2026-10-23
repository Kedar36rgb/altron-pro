import hashlib
import io
import json

import pandas as pd
import streamlit as st
import plotly.express as px

from altron.ops import apply_plan
from altron.llm import plan_cleaning, plan_chart, plan_pivot, plan_formula
from altron.charts import render
from altron.pivots import build_pivot
from altron.quality import quality_report
from altron.limits import allow

st.set_page_config(page_title="Altron Pro", page_icon="🧞‍♂️", layout="wide")
st.title("🧞‍♂️ Altron Pro: Natural Language Data Cleaning")

# Initialize session state
if 'fid' not in st.session_state:
    st.session_state.fid = None
    st.session_state.original = None
    st.session_state.history = []
    st.session_state.pending = None
    st.session_state.chart_spec = None
    st.session_state.pivot_spec = None
    st.session_state.formula_result = None

def load(uploaded):
    data = uploaded.getvalue()
    fid = hashlib.md5(data).hexdigest()
    if st.session_state.get('fid') != fid:
        reader = pd.read_csv if uploaded.name.endswith('.csv') else pd.read_excel
        st.session_state.update(
            fid=fid, 
            original=reader(io.BytesIO(data)), 
            history=[], 
            pending=None,
            chart_spec=None,
            pivot_spec=None,
            formula_result=None
        )

def current_df():
    df = st.session_state.original
    for plan in st.session_state.history:
        df = apply_plan(df, plan)
    return df

# Sidebar
with st.sidebar:
    st.header("Data Upload")
    uploaded_file = st.file_uploader("Choose a CSV or Excel file", type=["csv", "xlsx"])
    
    if uploaded_file is not None:
        load(uploaded_file)
    
    st.divider()
    st.write("**Privacy Settings**")
    share = st.toggle('Share 3 sample values per column with the AI', value=False)
    
    # Show API call limits
    used_calls = st.session_state.get('calls', 0)
    st.caption(f"AI calls used this session: {used_calls} / 20")

# Main Area
if st.session_state.original is not None:
    df = current_df()
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🧹 Cleaning", "📊 Charts", "🔄 Pivots", "🧮 Formulas", "📈 EDA"])
    
    # ---------------------------------------------------------
    # TAB 1: CLEANING & QUALITY SCORE
    # ---------------------------------------------------------
    with tab1:
        st.subheader("Current Data")
        
        # Quality Score Section
        quality = quality_report(df)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Quality Score", f"{quality['score']} / 100")
        col2.metric("Missing Values", f"{quality['missing_pct']}%")
        col3.metric("Duplicate Rows", quality['duplicate_rows'])
        col4.metric("Constant Columns", len(quality['constant_columns']))
        
        if quality['mostly_empty_columns']:
            st.warning(f"Columns with >40% missing data: {', '.join(quality['mostly_empty_columns'])}")
        
        st.dataframe(df.head(10), width="stretch")
        st.caption(f"{len(df)} rows × {df.shape[1]} columns")
        
        st.divider()
        st.subheader("AI Data Cleaning")
        req = st.text_input('Describe the cleaning you want (e.g., "Fill missing ages with the mean and lowercase the Name column")')
        
        if st.button('Plan it') and req:
            if allow():
                with st.spinner("AI is thinking..."):
                    try:
                        st.session_state.pending = plan_cleaning(df, req, share)
                    except RuntimeError as e:
                        st.error(str(e))
            else:
                st.warning('Demo limit reached. Run it locally with your own key for unlimited use.')
        
        # Preview & Approve Section
        if st.session_state.get('pending'):
            plan, preview = st.session_state.pending
            st.info(f"**AI Explanation:** {plan.explanation}")
            st.json([o.model_dump() for o in plan.operations])
            
            st.write("**Preview of Changes:**")
            st.caption(f'Rows: {len(df)} → {len(preview)} | Columns: {df.shape[1]} → {preview.shape[1]}')
            st.dataframe(preview.head(10), width="stretch")
            
            col1, col2 = st.columns(2)
            if col1.button('✅ Apply Changes', type="primary"):
                st.session_state.history.append(plan)
                st.session_state.pending = None
                st.rerun()
            if col2.button('❌ Discard'):
                st.session_state.pending = None
                st.rerun()
                
        # History & Undo
        st.divider()
        if st.session_state.history:
            st.write("**Applied Steps:**")
            for i, p in enumerate(st.session_state.history):
                st.write(f"{i+1}. {p.explanation}")
                
            if st.button('⏪ Undo last step'):
                st.session_state.history.pop()
                st.rerun()
                
        # Export
        st.divider()
        col1, col2 = st.columns(2)
        col1.download_button(
            '📥 Download cleaned CSV', 
            df.to_csv(index=False), 
            'cleaned.csv',
            mime='text/csv'
        )
        col2.download_button(
            '📥 Download recipe (JSON)',
            json.dumps([p.model_dump() for p in st.session_state.history], indent=2),
            'recipe.json',
            mime='application/json'
        )

    # ---------------------------------------------------------
    # TAB 2: AI CHARTS
    # ---------------------------------------------------------
    with tab2:
        st.subheader("Natural Language Charts")
        chart_req = st.text_input('Describe the chart you want (e.g., "Show a bar chart of average salary by city")')
        
        if st.button('Generate Chart') and chart_req:
            if allow():
                with st.spinner("Generating chart spec..."):
                    try:
                        spec = plan_chart(df, chart_req, share)
                        st.session_state.chart_spec = spec
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                st.warning('Demo limit reached.')

        if st.session_state.get('chart_spec'):
            spec = st.session_state.chart_spec
            with st.expander("View generated Chart Spec"):
                st.json(spec.model_dump())
                
            try:
                fig = render(df, spec)
                st.plotly_chart(fig, width="stretch")
            except Exception as e:
                st.error(f"Could not render chart: {e}")

    # ---------------------------------------------------------
    # TAB 3: AI PIVOTS
    # ---------------------------------------------------------
    with tab3:
        st.subheader("Natural Language Pivot Tables")
        pivot_req = st.text_input('Describe the pivot (e.g., "Sum of salary by city and age")')
        
        if st.button('Generate Pivot') and pivot_req:
            if allow():
                with st.spinner("Generating pivot spec..."):
                    try:
                        st.session_state.pivot_spec = plan_pivot(df, pivot_req, share)
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                st.warning('Demo limit reached.')

        if st.session_state.get('pivot_spec'):
            spec = st.session_state.pivot_spec
            with st.expander("View generated Pivot Spec"):
                st.json(spec.model_dump())
                
            try:
                pivot_result = build_pivot(df, spec)
                st.dataframe(pivot_result, width="stretch")
            except Exception as e:
                st.error(f"Could not build pivot: {e}")

    # ---------------------------------------------------------
    # TAB 4: AI FORMULAS
    # ---------------------------------------------------------
    with tab4:
        st.subheader("Excel / Google Sheets Formula Helper")
        st.write("Ask the AI to write a formula based on your actual columns.")
        
        dialect = st.radio("Select Dialect:", ["Excel", "Google Sheets"], horizontal=True)
        formula_req = st.text_input('What do you want to calculate? (e.g., "Multiply Age by 2")')
        
        if st.button('Generate Formula') and formula_req:
            if allow():
                with st.spinner("Writing formula..."):
                    try:
                        st.session_state.formula_result = plan_formula(df, formula_req, dialect)
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                st.warning('Demo limit reached.')

        if st.session_state.get('formula_result'):
            res = st.session_state.formula_result
            st.success(f"**Explanation:** {res.explanation}")
            st.code(res.formula, language="excel")

    # ---------------------------------------------------------
    # TAB 5: AUTOMATED EDA
    # ---------------------------------------------------------
    with tab5:
        st.subheader("Automated EDA Report")
        
        # 1. Descriptive Statistics
        st.write("**Descriptive Statistics (Numeric Columns)**")
        numeric_df = df.select_dtypes(include=['number'])
        if not numeric_df.empty:
            st.dataframe(numeric_df.describe().T, width="stretch")
        else:
            st.info("No numeric columns found for statistical summary.")
            
        st.divider()
        
        # 2. Missing Values Chart
        st.write("**Missing Values by Column**")
        missing_data = df.isna().mean() * 100
        missing_data = missing_data[missing_data > 0].reset_index()
        missing_data.columns = ['Column', 'Missing Percentage']
        
        if not missing_data.empty:
            fig_missing = px.bar(
                missing_data, x='Column', y='Missing Percentage', 
                title="Percentage of Missing Values", color='Missing Percentage'
            )
            st.plotly_chart(fig_missing, width="stretch")
        else:
            st.success("No missing values detected in the dataset!")
            
        st.divider()
        
        # 3. Correlation Heatmap
        st.write("**Correlation Heatmap**")
        if len(numeric_df.columns) > 1:
            corr = numeric_df.corr()
            fig_corr = px.imshow(
                corr, text_auto=True, aspect="auto", 
                title="Correlation Matrix", color_continuous_scale='RdBu_r'
            )
            st.plotly_chart(fig_corr, width="stretch")
        else:
            st.info("Need at least 2 numeric columns to generate a correlation heatmap.")

else:
    st.info("👈 Please upload a CSV file in the sidebar to get started. (Try one of the files in your `data/` folder!)")