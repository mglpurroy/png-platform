import streamlit as st
import pandas as pd
import sys
from pathlib import Path
import datetime
import calendar
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import utilities
from dashboard_utils import (
    init_session_state, load_custom_css,
    load_population_data, create_admin_levels, load_conflict_data,
    load_admin_boundaries, classify_and_aggregate_data, load_neighboring_country_events
)
from mapping_functions import create_admin_map, create_llg_map
from streamlit_folium import st_folium

# Page configuration
st.set_page_config(
    page_title="Spatial Analysis - Papua New Guinea Violence Dashboard",
    page_icon="🗺️",
    layout="wide"
)

# Initialize
init_session_state()
load_custom_css()

# Header
st.markdown("""
<div class="main-header">
    <h1>🗺️ Spatial Analysis</h1>
</div>
""", unsafe_allow_html=True)

# Load data with progress indicators
if not st.session_state.data_loaded:
    with st.spinner("Loading data... This may take a moment on first load."):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.text("Loading population data...")
            progress_bar.progress(20)
            st.session_state.pop_data = load_population_data()
            
            status_text.text("Creating administrative levels...")
            progress_bar.progress(50)
            st.session_state.admin_data = create_admin_levels(st.session_state.pop_data)
            
            status_text.text("Loading conflict data...")
            progress_bar.progress(70)
            st.session_state.conflict_data = load_conflict_data()
            
            status_text.text("Loading administrative boundaries...")
            progress_bar.progress(90)
            st.session_state.boundaries = load_admin_boundaries()
            
            progress_bar.progress(100)
            status_text.text("✅ Data loaded successfully!")
            st.session_state.data_loaded = True
            
            time.sleep(0.5)
            progress_bar.empty()
            status_text.empty()
            
        except Exception as e:
            st.error(f"Error loading data: {str(e)}")
            st.stop()

# Sidebar controls
st.sidebar.header("📊 Analysis Parameters")

# Custom date range selection
st.sidebar.subheader("📅 Time Period")

col1, col2 = st.sidebar.columns(2)

with col1:
    start_year = st.selectbox(
        "Start Year",
        options=list(range(1997, 2026)),
        index=27,  # Default to 2024
        key="start_year"
    )
    start_month = st.selectbox(
        "Start Month",
        options=list(range(1, 13)),
        format_func=lambda x: datetime.date(2020, x, 1).strftime('%B'),
        index=0,  # Default to January
        key="start_month"
    )

with col2:
    end_year = st.selectbox(
        "End Year",
        options=list(range(1997, 2026)),
        index=28,  # Default to 2025
        key="end_year"
    )
    end_month = st.selectbox(
        "End Month",
        options=list(range(1, 13)),
        format_func=lambda x: datetime.date(2020, x, 1).strftime('%B'),
        index=10,  # Default to November
        key="end_month"
    )

# Create period_info from custom selection
period_info = {
    'start_year': start_year,
    'start_month': start_month,
    'end_year': end_year,
    'end_month': end_month,
    'start_date': datetime.date(start_year, start_month, 1),
    'end_date': datetime.date(end_year, end_month, calendar.monthrange(end_year, end_month)[1]),
    'label': f"{datetime.date(2020, start_month, 1).strftime('%b')} {start_year} - {datetime.date(2020, end_month, 1).strftime('%b')} {end_year}"
}

# Calculate number of months
if start_year == end_year:
    period_info['months'] = end_month - start_month + 1
else:
    period_info['months'] = (end_year - start_year - 1) * 12 + (12 - start_month + 1) + end_month

# Validate date range
if (start_year > end_year) or (start_year == end_year and start_month > end_month):
    st.sidebar.error("⚠️ Start date must be before end date")
    st.stop()

# Display selected period info
st.sidebar.info(f"**Period:** {period_info['label']}\n\n**Duration:** {period_info['months']} months")

# Thresholds
st.sidebar.subheader("🎯 Violence Thresholds")

rate_thresh = st.sidebar.slider(
    "Death Rate (per 100k)",
    min_value=0.0,
    max_value=50.0,
    value=10.0,
    step=0.5,
    help="Minimum death rate per 100,000 population"
)

abs_thresh = st.sidebar.slider(
    "Absolute Deaths",
    min_value=0,
    max_value=100,
    value=5,
    step=1,
    help="Minimum number of deaths in absolute terms"
)

# Aggregation settings
st.sidebar.subheader("📍 Aggregation Settings")

agg_level = st.sidebar.radio(
    "Administrative Level",
    ["ADM1 (Province)", "ADM2 (District)"],
    help="Level for administrative aggregation"
)
agg_level = agg_level.split()[0]

agg_thresh = st.sidebar.slider(
    "Share Threshold (%)",
    min_value=0.0,
    max_value=100.0,
    value=10.0,
    step=1.0,
    help="Minimum percentage of LLGs affected to highlight administrative unit"
) / 100

map_var = st.sidebar.selectbox(
    "Map Variable",
    ["share_llgs_affected", "share_population_affected"],
    format_func=lambda x: "Share of LLGs Affected" if x == "share_llgs_affected" else "Share of Population Affected",
    help="Variable to display on administrative map"
)

# LLG display options
st.sidebar.subheader("🗺️ LLG Map Options")

show_all_llgs = st.sidebar.checkbox(
    "Show All LLGs",
    value=True,
    help="If checked, shows all LLGs. If unchecked, shows only violence-affected LLGs (faster rendering)"
)

# Neighboring country events
st.sidebar.subheader("🌍 Neighboring Country Events")

show_indonesia_events = st.sidebar.checkbox(
    "Show Indonesia Events",
    value=False,
    help="Show ACLED events from Indonesia near Papua New Guinea borders for the selected period"
)

show_australia_events = st.sidebar.checkbox(
    "Show Australia Events",
    value=False,
    help="Show ACLED events from Australia near Papua New Guinea borders for the selected period"
)

# Process data
with st.spinner("Processing data for selected period..."):
    pop_data = st.session_state.pop_data
    admin_data = st.session_state.admin_data
    conflict_data = st.session_state.conflict_data
    
    # Ensure boundaries are loaded
    if 'boundaries' not in st.session_state or st.session_state.boundaries is None:
        st.session_state.boundaries = load_admin_boundaries()
    boundaries = st.session_state.boundaries
    
    # Check if we have population data
    if pop_data.empty or admin_data['admin3'].empty:
        st.warning("⚠️ No population data available. Please ensure the population data file exists and matches the boundary data.")
        st.stop()
    
    # Classify and aggregate
    aggregated, merged = classify_and_aggregate_data(
        admin_data['admin3'], admin_data, conflict_data, period_info,
        rate_thresh, abs_thresh, agg_thresh, agg_level
    )
    
    if merged.empty:
        st.error("❌ No LLG data available after processing.")
        st.stop()

# Key metrics
st.header("📊 Overview Metrics")

total_llgs = len(merged)
affected_llgs = merged['violence_affected'].sum()
total_population = merged['pop_count'].sum()
affected_population = merged[merged['violence_affected']]['pop_count'].sum()
total_deaths = merged['ACLED_BRD_total'].sum()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <h4>📍 Total LLGs</h4>
        <div style="font-size: 24px; font-weight: bold;">{total_llgs:,}</div>
        <div>analyzed in {period_info['label']}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    affected_pct = (affected_llgs/total_llgs*100) if total_llgs > 0 else 0
    st.markdown(f"""
    <div class="metric-card">
        <h4>⚠️ Affected LLGs</h4>
        <div style="font-size: 24px; font-weight: bold;">{affected_llgs:,}</div>
        <div>out of {total_llgs:,} ({affected_pct:.1f}%)</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    affected_pop_pct = (affected_population/total_population*100) if total_population > 0 else 0
    st.markdown(f"""
    <div class="metric-card">
        <h4>👥 Affected Population</h4>
        <div style="font-size: 24px; font-weight: bold;">{affected_population:,.0f}</div>
        <div>out of {total_population:,.0f} ({affected_pop_pct:.1f}%)</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card">
        <h4>Total Deaths</h4>
        <div style="font-size: 24px; font-weight: bold;">{total_deaths:,}</div>
        <div>in {period_info['label']}</div>
    </div>
    """, unsafe_allow_html=True)

# Maps section
tab1, tab2 = st.tabs(["🏘️ LLGs", "📍 Provinces"])

with tab1:
    if len(merged) > 0:
        # Check if boundaries are available
        if not boundaries:
            st.error("❌ Boundaries not loaded. Please refresh the page to reload boundaries.")
        elif not isinstance(boundaries, dict):
            st.error(f"❌ Invalid boundaries format: {type(boundaries)}")
        elif 3 not in boundaries:
            st.error(f"❌ Admin3 boundaries not found. Available levels: {list(boundaries.keys())}")
        elif boundaries[3].empty:
            st.error("❌ Admin3 boundaries are empty.")
        else:
            with st.spinner("Generating LLG map... This may take a moment."):
                # Load neighboring country events if toggled
                indonesia_events = None
                australia_events = None
                
                if show_indonesia_events:
                    indonesia_events = load_neighboring_country_events(period_info, country='indonesia', border_distance_km=200)
                
                if show_australia_events:
                    australia_events = load_neighboring_country_events(period_info, country='australia', border_distance_km=200)
                
                llg_map = create_llg_map(
                    merged, boundaries, period_info, rate_thresh, abs_thresh, show_all_llgs,
                    indonesia_events=indonesia_events, australia_events=australia_events
                )
                if llg_map:
                    st_folium(llg_map, width=None, height=600, returned_objects=["last_object_clicked"])
                else:
                    st.error("Could not create LLG map. The map function returned None.")
    else:
        st.error("No LLG data available for the selected period.")

with tab2:
    if len(aggregated) > 0 and agg_level in ['ADM1', 'ADM2']:
        admin_level_num = 1 if agg_level == 'ADM1' else 2
        if boundaries and isinstance(boundaries, dict) and admin_level_num in boundaries and not boundaries[admin_level_num].empty:
            with st.spinner("Generating administrative map..."):
                try:
                    admin_map = create_admin_map(
                        aggregated, boundaries, agg_level, map_var, agg_thresh, period_info, rate_thresh, abs_thresh
                    )
                    if admin_map:
                        st_folium(admin_map, width=None, height=600, returned_objects=["last_object_clicked"])
                    else:
                        st.error("Could not create administrative map due to missing boundary data.")
                except Exception as e:
                    st.error(f"Error creating administrative map: {str(e)}")
        else:
            st.error("No administrative boundary data available.")
    else:
        st.error("No administrative data available for the selected period.")

