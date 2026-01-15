import streamlit as st
import pandas as pd
import sys
from pathlib import Path
import datetime
import time

try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import utilities
from dashboard_utils import (
    init_session_state, load_custom_css,
    load_population_data, create_admin_levels, load_conflict_data,
    load_admin_boundaries, DATA_PATH
)

# Page configuration
st.set_page_config(
    page_title="Trends Analysis - Papua New Guinea Violence Dashboard",
    page_icon="📈",
    layout="wide"
)

# Initialize
init_session_state()
load_custom_css()

if not PLOTLY_AVAILABLE:
    st.error("Plotly not installed. Please run: pip install plotly")
    st.stop()

# Header
st.markdown("""
<div class="main-header">
    <h1>📈 Trends Analysis</h1>
</div>
""", unsafe_allow_html=True)

# Load data
if not st.session_state.data_loaded:
    with st.spinner("Loading data..."):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.text("Loading population data...")
            progress_bar.progress(20)
            st.session_state.pop_data = load_population_data()
            
            status_text.text("Creating administrative levels...")
            progress_bar.progress(40)
            st.session_state.admin_data = create_admin_levels(st.session_state.pop_data)
            
            status_text.text("Loading conflict data...")
            progress_bar.progress(60)
            st.session_state.conflict_data = load_conflict_data()
            
            status_text.text("Loading administrative boundaries...")
            progress_bar.progress(80)
            if 'boundaries' not in st.session_state or st.session_state.boundaries is None:
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

# Time period selection
st.sidebar.subheader("📅 Time Period")

col1, col2 = st.sidebar.columns(2)

with col1:
    start_year = st.selectbox(
        "Start Year",
        options=list(range(1997, 2026)),
        index=0,  # Default to 1997
        key="trends_start_year"
    )
    start_month = st.selectbox(
        "Start Month",
        options=list(range(1, 13)),
        format_func=lambda x: datetime.date(2020, x, 1).strftime('%B'),
        index=0,  # Default to January
        key="trends_start_month"
    )

with col2:
    end_year = st.selectbox(
        "End Year",
        options=list(range(1997, 2026)),
        index=28,  # Default to 2025
        key="trends_end_year"
    )
    end_month = st.selectbox(
        "End Month",
        options=list(range(1, 13)),
        format_func=lambda x: datetime.date(2020, x, 1).strftime('%B'),
        index=10,  # Default to November
        key="trends_end_month"
    )

# Aggregation level
st.sidebar.subheader("📍 Aggregation Level")

agg_level = st.sidebar.radio(
    "Administrative Level",
    ["National", "Province", "District", "LLG"],
    index=0,
    help="Level for trend aggregation"
)

# Selected province/district/LLG if not national
selected_province = None
selected_district = None
selected_llg = None

if agg_level == "Province":
    provinces = st.session_state.admin_data['admin1']['ADM1_EN'].unique().tolist()
    selected_province = st.sidebar.selectbox("Select Province", options=sorted(provinces))
elif agg_level == "District":
    districts = st.session_state.admin_data['admin2']['ADM2_EN'].unique().tolist()
    selected_district = st.sidebar.selectbox("Select District", options=sorted(districts))
elif agg_level == "LLG":
    llgs = st.session_state.admin_data['admin3']['ADM3_EN'].unique().tolist()
    selected_llg = st.sidebar.selectbox("Select LLG", options=sorted(llgs))

# Process conflict data for trends
conflict_data = st.session_state.conflict_data.copy()

if conflict_data.empty:
    st.error("No conflict data available.")
    st.stop()

# Filter by date range
conflict_data['date'] = pd.to_datetime(
    conflict_data['year'].astype(str) + '-' + 
    conflict_data['month'].astype(str).str.zfill(2) + '-01'
)

start_date = datetime.date(start_year, start_month, 1)
end_date = datetime.date(end_year, end_month, 28)  # Use 28 to handle all months

conflict_filtered = conflict_data[
    (conflict_data['date'] >= pd.Timestamp(start_date)) &
    (conflict_data['date'] <= pd.Timestamp(end_date))
].copy()

if conflict_filtered.empty:
    st.warning(f"No conflict events in the selected period ({start_date} to {end_date})")
    st.stop()

# Filter by administrative level
if agg_level == "Province" and selected_province:
    if 'ADM1_EN' in conflict_filtered.columns:
        conflict_filtered = conflict_filtered[conflict_filtered['ADM1_EN'] == selected_province]
elif agg_level == "District" and selected_district:
    if 'ADM2_EN' in conflict_filtered.columns:
        conflict_filtered = conflict_filtered[conflict_filtered['ADM2_EN'] == selected_district]
elif agg_level == "LLG" and selected_llg:
    if 'ADM3_EN' in conflict_filtered.columns:
        conflict_filtered = conflict_filtered[conflict_filtered['ADM3_EN'] == selected_llg]

# Aggregate by time period
if 'year' in conflict_filtered.columns and 'month' in conflict_filtered.columns:
    # Monthly aggregation
    monthly_trends = conflict_filtered.groupby(['year', 'month']).agg({
        'ACLED_BRD_total': 'sum',
        'ACLED_BRD_state': 'sum',
        'ACLED_BRD_nonstate': 'sum'
    }).reset_index()
    
    monthly_trends['date'] = pd.to_datetime(
        monthly_trends['year'].astype(str) + '-' + 
        monthly_trends['month'].astype(str).str.zfill(2) + '-01'
    )
    monthly_trends = monthly_trends.sort_values('date')
    
    # Yearly aggregation
    yearly_trends = conflict_filtered.groupby('year').agg({
        'ACLED_BRD_total': 'sum',
        'ACLED_BRD_state': 'sum',
        'ACLED_BRD_nonstate': 'sum'
    }).reset_index()
    yearly_trends = yearly_trends.sort_values('year')
    
    # Display metrics
    st.header("📊 Overview Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_deaths = conflict_filtered['ACLED_BRD_total'].sum()
    state_deaths = conflict_filtered['ACLED_BRD_state'].sum()
    nonstate_deaths = conflict_filtered['ACLED_BRD_nonstate'].sum()
    total_events = len(conflict_filtered)
    
    with col1:
        st.metric("Total Deaths", f"{total_deaths:,.0f}")
    
    with col2:
        st.metric("State Violence", f"{state_deaths:,.0f}", 
                  f"{(state_deaths/total_deaths*100) if total_deaths > 0 else 0:.1f}%")
    
    with col3:
        st.metric("Non-State Violence", f"{nonstate_deaths:,.0f}",
                  f"{(nonstate_deaths/total_deaths*100) if total_deaths > 0 else 0:.1f}%")
    
    with col4:
        st.metric("Total Events", f"{total_events:,}")
    
    st.markdown("---")
    
    # Create visualizations
    tab1, tab2, tab3 = st.tabs(["📅 Monthly Trends", "📆 Yearly Trends", "📊 Comparison"])
    
    with tab1:
        st.subheader("Monthly Violence Trends")
        
        if len(monthly_trends) > 0:
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('Total Deaths by Month', 'State vs Non-State Violence'),
                vertical_spacing=0.15,
                row_heights=[0.6, 0.4]
            )
            
            # Total deaths line
            fig.add_trace(
                go.Scatter(
                    x=monthly_trends['date'],
                    y=monthly_trends['ACLED_BRD_total'],
                    mode='lines+markers',
                    name='Total Deaths',
                    line=dict(color='#d73027', width=2),
                    marker=dict(size=6)
                ),
                row=1, col=1
            )
            
            # State violence
            fig.add_trace(
                go.Scatter(
                    x=monthly_trends['date'],
                    y=monthly_trends['ACLED_BRD_state'],
                    mode='lines+markers',
                    name='State Violence',
                    line=dict(color='#4575b4', width=2),
                    marker=dict(size=5)
                ),
                row=2, col=1
            )
            
            # Non-state violence
            fig.add_trace(
                go.Scatter(
                    x=monthly_trends['date'],
                    y=monthly_trends['ACLED_BRD_nonstate'],
                    mode='lines+markers',
                    name='Non-State Violence',
                    line=dict(color='#fc8d59', width=2),
                    marker=dict(size=5)
                ),
                row=2, col=1
            )
            
            fig.update_xaxes(title_text="Date", row=1, col=1)
            fig.update_xaxes(title_text="Date", row=2, col=1)
            fig.update_yaxes(title_text="Deaths", row=1, col=1)
            fig.update_yaxes(title_text="Deaths", row=2, col=1)
            
            fig.update_layout(
                height=700,
                showlegend=True,
                hovermode='x unified',
                title_text=f"Monthly Violence Trends - {agg_level}" + 
                          (f": {selected_province}" if selected_province else "") +
                          (f": {selected_district}" if selected_district else "") +
                          (f": {selected_llg}" if selected_llg else "")
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No monthly data available for the selected period.")
    
    with tab2:
        st.subheader("Yearly Violence Trends")
        
        if len(yearly_trends) > 0:
            fig = go.Figure()
            
            # Total deaths bar
            fig.add_trace(go.Bar(
                x=yearly_trends['year'],
                y=yearly_trends['ACLED_BRD_total'],
                name='Total Deaths',
                marker_color='#d73027',
                text=yearly_trends['ACLED_BRD_total'],
                textposition='outside'
            ))
            
            # State violence line
            fig.add_trace(go.Scatter(
                x=yearly_trends['year'],
                y=yearly_trends['ACLED_BRD_state'],
                mode='lines+markers',
                name='State Violence',
                line=dict(color='#4575b4', width=3),
                marker=dict(size=10),
                yaxis='y2'
            ))
            
            # Non-state violence line
            fig.add_trace(go.Scatter(
                x=yearly_trends['year'],
                y=yearly_trends['ACLED_BRD_nonstate'],
                mode='lines+markers',
                name='Non-State Violence',
                line=dict(color='#fc8d59', width=3),
                marker=dict(size=10),
                yaxis='y2'
            ))
            
            fig.update_layout(
                title=f"Yearly Violence Trends - {agg_level}" + 
                      (f": {selected_province}" if selected_province else "") +
                      (f": {selected_district}" if selected_district else "") +
                      (f": {selected_llg}" if selected_llg else ""),
                xaxis_title="Year",
                yaxis_title="Total Deaths",
                yaxis2=dict(
                    title="Deaths (State/Non-State)",
                    overlaying='y',
                    side='right'
                ),
                height=500,
                hovermode='x unified',
                barmode='group'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No yearly data available for the selected period.")
    
    with tab3:
        st.subheader("State vs Non-State Violence Comparison")
        
        if len(monthly_trends) > 0:
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=monthly_trends['date'],
                y=monthly_trends['ACLED_BRD_state'],
                mode='lines+markers',
                name='State Violence',
                fill='tozeroy',
                line=dict(color='#4575b4', width=2),
                marker=dict(size=5)
            ))
            
            fig.add_trace(go.Scatter(
                x=monthly_trends['date'],
                y=monthly_trends['ACLED_BRD_nonstate'],
                mode='lines+markers',
                name='Non-State Violence',
                fill='tozeroy',
                line=dict(color='#fc8d59', width=2),
                marker=dict(size=5)
            ))
            
            fig.update_layout(
                title="State vs Non-State Violence Over Time",
                xaxis_title="Date",
                yaxis_title="Deaths",
                height=500,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Summary statistics
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### State Violence")
                st.metric("Total", f"{state_deaths:,.0f}")
                st.metric("Average per Month", f"{(state_deaths/len(monthly_trends)) if len(monthly_trends) > 0 else 0:.1f}")
                st.metric("Peak Month", 
                         monthly_trends.loc[monthly_trends['ACLED_BRD_state'].idxmax(), 'date'].strftime('%B %Y') 
                         if len(monthly_trends) > 0 and monthly_trends['ACLED_BRD_state'].max() > 0 else "N/A")
            
            with col2:
                st.markdown("### Non-State Violence")
                st.metric("Total", f"{nonstate_deaths:,.0f}")
                st.metric("Average per Month", f"{(nonstate_deaths/len(monthly_trends)) if len(monthly_trends) > 0 else 0:.1f}")
                st.metric("Peak Month",
                         monthly_trends.loc[monthly_trends['ACLED_BRD_nonstate'].idxmax(), 'date'].strftime('%B %Y')
                         if len(monthly_trends) > 0 and monthly_trends['ACLED_BRD_nonstate'].max() > 0 else "N/A")
        else:
            st.info("No comparison data available for the selected period.")

else:
    st.error("Conflict data missing required date columns (year, month).")
