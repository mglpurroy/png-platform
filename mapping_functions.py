import folium
import geopandas as gpd
import pandas as pd
import streamlit as st
import time
from datetime import datetime

def clean_gdf_for_folium(gdf):
    """Remove non-serializable columns (Timestamps, etc.) from GeoDataFrame for Folium"""
    if gdf.empty:
        return gdf
    
    gdf_clean = gdf.copy()
    
    # Drop columns that contain Timestamp or other non-serializable types
    cols_to_drop = []
    for col in gdf_clean.columns:
        if col == 'geometry':
            continue
        # Check for datetime64 dtypes
        if pd.api.types.is_datetime64_any_dtype(gdf_clean[col]):
            cols_to_drop.append(col)
        # Check if column contains Timestamp objects (object dtype)
        elif gdf_clean[col].dtype == 'object':
            sample = gdf_clean[col].dropna()
            if len(sample) > 0 and isinstance(sample.iloc[0], (pd.Timestamp, datetime)):
                cols_to_drop.append(col)
        # Also drop known date columns by name
        elif 'date' in col.lower() or 'valid' in col.lower():
            cols_to_drop.append(col)
    
    if cols_to_drop:
        gdf_clean = gdf_clean.drop(columns=cols_to_drop)
    
    # Keep only essential columns for boundaries (geometry + identifiers)
    essential_cols = ['geometry']
    for col in ['ADM1_PCODE', 'ADM1_EN', 'ADM2_PCODE', 'ADM2_EN', 'ADM3_PCODE', 'ADM3_EN']:
        if col in gdf_clean.columns:
            essential_cols.append(col)
    
    # Keep only essential columns
    available_cols = [col for col in essential_cols if col in gdf_clean.columns]
    gdf_clean = gdf_clean[available_cols]
    
    return gdf_clean

def create_admin_map(aggregated, boundaries, agg_level, map_var, agg_thresh, period_info, rate_thresh, abs_thresh):
    """Create administrative units map with optimized performance"""
    import time
    start_time = time.time()
    
    # Determine columns based on boundary structure
    if agg_level == 'ADM1':
        # Region level
        pcode_col = 'ADM1_PCODE'  # From boundary file
        name_col = 'ADM1_EN'      # From boundary file
        agg_pcode_col = 'ADM1_PCODE'  # From aggregated data
        agg_name_col = 'ADM1_EN'      # From aggregated data
    else:
        # District level  
        pcode_col = 'ADM2_PCODE'  # From boundary file
        name_col = 'ADM2_EN'      # From boundary file
        agg_pcode_col = 'ADM2_PCODE'  # From aggregated data
        agg_name_col = 'ADM2_EN'      # From aggregated data
    
    if map_var == 'share_llgs_affected':
        value_col = 'share_llgs_affected'
        value_label = 'Share of LLGs Affected'
    else:
        value_col = 'share_population_affected'
        value_label = 'Share of Population Affected'
    
    # Get appropriate boundary data
    map_level_num = 1 if agg_level == 'ADM1' else 2
    gdf = boundaries[map_level_num]
    
    if gdf.empty:
        st.error(f"No boundary data available for {agg_level}")
        return None
    
    # Merge data with boundaries using optimized merge
    merge_cols = [agg_pcode_col, value_col, 'above_threshold', 'violence_affected', 'total_llgs', 'pop_count', 'ACLED_BRD_total']
    merged_gdf = gdf.merge(aggregated[merge_cols], left_on=pcode_col, right_on=agg_pcode_col, how='left')
    
    # Use vectorized fillna
    fill_values = {
        value_col: 0, 
        'above_threshold': False, 
        'violence_affected': 0, 
        'total_llgs': 0,
        'pop_count': 0,
        'ACLED_BRD_total': 0
    }
    merged_gdf = merged_gdf.fillna(fill_values)
    
    # Create map with optimized settings - centered on Papua New Guinea
    m = folium.Map(
        location=[-6.0, 150.0],  # Papua New Guinea center coordinates
        zoom_start=7,  # Increased zoom to focus on PNG
        tiles='OpenStreetMap',
        prefer_canvas=True,
        min_zoom=5,
        max_zoom=15
    )
    
    # Fit map bounds to Papua New Guinea if we have boundary data
    if boundaries and 1 in boundaries and not boundaries[1].empty:
        bounds = boundaries[1].total_bounds  # [minx, miny, maxx, maxy]
        m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])  # [[lat_min, lon_min], [lat_max, lon_max]]
    
    # Pre-calculate colors and status for better performance
    def get_color_status(value):
        if value > agg_thresh:
            return '#d73027', 0.8, "HIGH VIOLENCE"
        elif value > 0:
            return '#fd8d3c', 0.7, "Some Violence"
        else:
            return '#2c7fb8', 0.4, "Low/No Violence"
    
    # Add choropleth layer with optimized rendering
    for _, row in merged_gdf.iterrows():
        value = row[value_col]
        color, opacity, status = get_color_status(value)
        
        # Simplified popup content for better performance
        popup_content = f"""
        <div style="width: 280px; font-family: Arial, sans-serif;">
            <h4 style="color: {color}; margin: 0;">{row.get(name_col, 'Unknown')}</h4>
            <div style="background: {color}; color: white; padding: 3px; border-radius: 2px; text-align: center; margin: 5px 0;">
                <strong>{status}</strong>
            </div>
            <p><strong>{value_label}:</strong> {value:.1%}</p>
            <p><strong>Affected LLGs:</strong> {row['violence_affected']}/{row['total_llgs']}</p>
            <p><strong>Total Deaths:</strong> {row['ACLED_BRD_total']:,.0f}</p>
        </div>
        """
        
        folium.GeoJson(
            row.geometry,
            style_function=lambda x, color=color, opacity=opacity: {
                'fillColor': color,
                'color': 'black',
                'weight': 0.8,
                'fillOpacity': opacity
            },
            popup=folium.Popup(popup_content, max_width=300),
            tooltip=f"{row.get(name_col, 'Unknown')}: {value:.1%}"
        ).add_to(m)
    
    # Simplified legend
    legend_html = f'''
    <div style="position: fixed; top: 10px; right: 10px; width: 250px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:11px; padding: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                border-radius: 4px;">
    <h4 style="margin: 0 0 6px 0; color: #333;">{value_label}</h4>
    <div style="margin-bottom: 6px;">
        <div style="margin: 2px 0;"><span style="background:#d73027; color:white; padding:1px 3px; border-radius:1px; font-size:9px;">HIGH</span> >{agg_thresh:.1%}</div>
        <div style="margin: 2px 0;"><span style="background:#fd8d3c; color:white; padding:1px 3px; border-radius:1px; font-size:9px;">SOME</span> >0%</div>
        <div style="margin: 2px 0;"><span style="background:#2c7fb8; color:white; padding:1px 3px; border-radius:1px; font-size:9px;">LOW</span> 0%</div>
    </div>
    <div style="font-size:9px; color:#666;">
        <strong>Period:</strong> {period_info['label']}<br>
        <strong>Criteria:</strong> >{rate_thresh:.1f}/100k & >{abs_thresh} deaths<br>
        <strong>Black borders:</strong> Region boundaries
    </div>
    </div>
    '''
    
    # Add Region borders on top of admin units (non-interactive reference layer)
    admin1_gdf = boundaries[1]
    if not admin1_gdf.empty:
        admin1_gdf_clean = clean_gdf_for_folium(admin1_gdf)
        folium.GeoJson(
            admin1_gdf_clean,
            style_function=lambda x: {
                'fillColor': 'transparent',
                'color': '#000000',
                'weight': 2,
                'fillOpacity': 0,
                'opacity': 0.8,
                'interactive': False
            },
            interactive=False
        ).add_to(m)
    
    m.get_root().html.add_child(folium.Element(legend_html))
    
    return m

def create_llg_map(llg_data, boundaries, period_info, rate_thresh, abs_thresh, show_all_llgs=False, indonesia_events=None, australia_events=None):
    """Create LLG (admin3) classification map with highly optimized performance"""
    import time
    import json
    start_time = time.time()
    
    # Get LLG boundaries (admin3)
    llg_gdf = boundaries[3].copy()
    
    if llg_gdf.empty:
        st.error("No LLG boundary data available")
        return None
    
    # Filter out null or invalid geometries before processing
    valid_geom_mask = llg_gdf.geometry.notna() & llg_gdf.geometry.is_valid
    llg_gdf = llg_gdf[valid_geom_mask].copy()
    
    if llg_gdf.empty:
        st.error("No valid LLG geometries available")
        return None
    
    # Simplify geometries for faster rendering (tolerance in degrees, ~1km)
    llg_gdf['geometry'] = llg_gdf['geometry'].simplify(tolerance=0.01, preserve_topology=True)
    
    # Merge with classification data using optimized merge
    # Only merge on ADM3_PCODE to avoid column name conflicts
    merge_cols = ['ADM3_PCODE', 'ADM3_EN', 'ADM2_EN', 'ADM1_EN', 'pop_count', 'violence_affected', 'ACLED_BRD_total', 'acled_total_death_rate']
    
    # Check which columns actually exist in llg_data
    available_cols = ['ADM3_PCODE'] + [col for col in merge_cols[1:] if col in llg_data.columns]
    
    # Drop columns from llg_gdf that will cause conflicts (keep only ADM3_PCODE and geometry)
    llg_gdf_clean = llg_gdf[['ADM3_PCODE', 'geometry']].copy()
    
    merged_llg = llg_gdf_clean.merge(llg_data[available_cols], on='ADM3_PCODE', how='left')
    
    # Use vectorized fillna
    fill_values = {
        'ADM3_EN': 'Unknown',
        'ADM2_EN': 'Unknown',
        'ADM1_EN': 'Unknown',
        'pop_count': 0,
        'ACLED_BRD_total': 0,
        'acled_total_death_rate': 0.0,
        'violence_affected': False
    }
    
    # Only fill values for columns that exist
    fill_values_filtered = {k: v for k, v in fill_values.items() if k in merged_llg.columns}
    merged_llg = merged_llg.fillna(fill_values_filtered)
    
    # Ensure all required columns exist with defaults
    for col in ['ADM3_EN', 'ADM2_EN', 'ADM1_EN']:
        if col not in merged_llg.columns:
            merged_llg[col] = 'Unknown'
    for col in ['pop_count', 'ACLED_BRD_total', 'acled_total_death_rate']:
        if col not in merged_llg.columns:
            merged_llg[col] = 0
    if 'violence_affected' not in merged_llg.columns:
        merged_llg['violence_affected'] = False
    
    # Filter to only affected LLGs if requested (default for performance)
    if not show_all_llgs:
        merged_llg = merged_llg[merged_llg['violence_affected'] == True].copy()
    
    # If no affected LLGs, return None with message
    if len(merged_llg) == 0:
        st.warning("No violence-affected LLGs to display in the selected period. Try selecting 'Show All LLGs' or a different time period.")
        return None
    
    # Pre-calculate statistics for legend
    total_llgs = len(llg_data)
    affected_llgs = sum(llg_data['violence_affected'])
    affected_percentage = (affected_llgs / total_llgs * 100) if total_llgs > 0 else 0
    
    # Clean the GeoDataFrame to remove any non-serializable columns (Timestamps, etc.)
    # Keep only the columns we need for the map
    essential_cols = ['geometry', 'ADM3_PCODE', 'ADM3_EN', 'ADM2_EN', 'ADM1_EN', 
                      'pop_count', 'violence_affected', 'ACLED_BRD_total', 'acled_total_death_rate']
    available_cols = [col for col in essential_cols if col in merged_llg.columns]
    merged_llg = merged_llg[available_cols].copy()
    
    # Add color column for choropleth-style rendering
    merged_llg['color'] = merged_llg.apply(
        lambda x: '#d73027' if x['violence_affected'] else (
            '#fd8d3c' if x['ACLED_BRD_total'] > 0 else '#2c7fb8'
        ), axis=1
    )
    merged_llg['status'] = merged_llg.apply(
        lambda x: 'AFFECTED' if x['violence_affected'] else (
            'Below Threshold' if x['ACLED_BRD_total'] > 0 else 'No Violence'
        ), axis=1
    )
    
    # Create map with optimized settings - centered on Papua New Guinea
    m = folium.Map(
        location=[-6.0, 150.0],  # Papua New Guinea center coordinates
        zoom_start=7,  # Increased zoom to focus on PNG
        tiles='CartoDB positron',  # Lighter, faster tiles
        prefer_canvas=True,
        min_zoom=5,
        max_zoom=15,
        zoom_control=True
    )
    
    # Fit map bounds to Papua New Guinea if we have boundary data
    if boundaries and 1 in boundaries and not boundaries[1].empty:
        bounds = boundaries[1].total_bounds  # [minx, miny, maxx, maxy]
        m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])  # [[lat_min, lon_min], [lat_max, lon_max]]
    
    # Create a single GeoJson layer with all LLGs (much faster than individual layers)
    # Prepare fields for tooltip and popup
    merged_llg['popup_html'] = merged_llg.apply(
        lambda row: f"""
        <b>{row['ADM3_EN']}</b><br>
        <b>Status:</b> {row['status']}<br>
        <b>District:</b> {row['ADM2_EN']}<br>
        <b>Province:</b> {row['ADM1_EN']}<br>
        <b>Deaths:</b> {int(row['ACLED_BRD_total'])}<br>
        <b>Rate:</b> {row['acled_total_death_rate']:.1f}/100k<br>
        <b>Pop:</b> {int(row['pop_count']):,}
        """, axis=1
    )
    
    # Use style_function for dynamic coloring
    def style_function(feature):
        return {
            'fillColor': feature['properties']['color'],
            'color': 'black',
            'weight': 0.5,
            'fillOpacity': 0.7
        }
    
    def highlight_function(feature):
        return {
            'fillColor': feature['properties']['color'],
            'color': 'yellow',
            'weight': 3,
            'fillOpacity': 0.9
        }
    
    # Convert to GeoJSON for better performance
    llg_geojson = folium.GeoJson(
        merged_llg[['geometry', 'ADM3_EN', 'ADM2_EN', 'ADM1_EN', 'status', 'ACLED_BRD_total', 
                     'acled_total_death_rate', 'pop_count', 'color', 'popup_html']],
        name='LLGs',
        style_function=style_function,
        highlight_function=highlight_function,
        tooltip=folium.GeoJsonTooltip(
            fields=['ADM3_EN', 'status', 'ACLED_BRD_total'],
            aliases=['LLG:', 'Status:', 'Deaths:'],
            localize=True,
            sticky=False,
            labels=True,
            style="""
                background-color: white;
                border: 2px solid black;
                border-radius: 3px;
                box-shadow: 3px;
            """,
        ),
        popup=folium.GeoJsonPopup(
            fields=['popup_html'],
            labels=False,
            localize=True,
            style="background-color: white;",
        ),
        zoom_on_click=True,
    )
    
    llg_geojson.add_to(m)
    
    # Add neighboring country events as point layers
    if indonesia_events is not None and not indonesia_events.empty:
        for idx, event in indonesia_events.iterrows():
            # Create popup content
            event_date = event.get('event_date', 'N/A')
            if pd.notna(event_date) and hasattr(event_date, 'strftime'):
                event_date = event_date.strftime('%Y-%m-%d')
            elif pd.notna(event_date):
                event_date = str(event_date)[:10]  # Take first 10 chars for date
            
            notes = event.get('notes', '')
            notes_html = f"<p><strong>Notes:</strong> {str(notes)[:100]}...</p>" if pd.notna(notes) and str(notes) != '' else ''
            
            popup_html = f"""
            <div style="width: 250px; font-family: Arial, sans-serif;">
                <h4 style="color: #e31a1c; margin: 0;">🇮🇩 Indonesia Event</h4>
                <p><strong>Date:</strong> {event_date}</p>
                <p><strong>Type:</strong> {event.get('event_type', 'N/A')}</p>
                <p><strong>Location:</strong> {event.get('location', 'N/A')}</p>
                <p><strong>Fatalities:</strong> {int(event.get('fatalities', 0))}</p>
                <p><strong>Admin1:</strong> {event.get('admin1', 'N/A')}</p>
                {notes_html}
            </div>
            """
            
            folium.CircleMarker(
                location=[event.geometry.y, event.geometry.x],
                radius=5 + min(int(event.get('fatalities', 0)) / 5, 15),  # Size based on fatalities
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"Indonesia: {int(event.get('fatalities', 0))} deaths",
                color='#e31a1c',
                fillColor='#e31a1c',
                fillOpacity=0.7,
                weight=2
            ).add_to(m)
    
    if australia_events is not None and not australia_events.empty:
        for idx, event in australia_events.iterrows():
            # Create popup content
            event_date = event.get('event_date', 'N/A')
            if pd.notna(event_date) and hasattr(event_date, 'strftime'):
                event_date = event_date.strftime('%Y-%m-%d')
            elif pd.notna(event_date):
                event_date = str(event_date)[:10]  # Take first 10 chars for date
            
            notes = event.get('notes', '')
            notes_html = f"<p><strong>Notes:</strong> {str(notes)[:100]}...</p>" if pd.notna(notes) and str(notes) != '' else ''
            
            popup_html = f"""
            <div style="width: 250px; font-family: Arial, sans-serif;">
                <h4 style="color: #238b45; margin: 0;">🇦🇺 Australia Event</h4>
                <p><strong>Date:</strong> {event_date}</p>
                <p><strong>Type:</strong> {event.get('event_type', 'N/A')}</p>
                <p><strong>Location:</strong> {event.get('location', 'N/A')}</p>
                <p><strong>Fatalities:</strong> {int(event.get('fatalities', 0))}</p>
                <p><strong>Admin1:</strong> {event.get('admin1', 'N/A')}</p>
                {notes_html}
            </div>
            """
            
            folium.CircleMarker(
                location=[event.geometry.y, event.geometry.x],
                radius=5 + min(int(event.get('fatalities', 0)) / 5, 15),  # Size based on fatalities
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"Australia: {int(event.get('fatalities', 0))} deaths",
                color='#238b45',
                fillColor='#238b45',
                fillOpacity=0.7,
                weight=2
            ).add_to(m)
    
    # Add Province borders on top of LLGs (non-interactive to allow LLG clicks)
    admin1_gdf = boundaries[1]
    if not admin1_gdf.empty:
        admin1_gdf_clean = clean_gdf_for_folium(admin1_gdf)
        folium.GeoJson(
            admin1_gdf_clean,
            style_function=lambda x: {
                'fillColor': 'transparent',
                'color': '#000000',
                'weight': 2,
                'fillOpacity': 0,
                'opacity': 0.8,
                'interactive': False  # Makes the layer non-interactive
            },
            interactive=False  # Disable all interactivity for this layer
        ).add_to(m)
    
    # Simplified legend
    legend_html = f'''
    <div style="position: fixed; top: 10px; right: 10px; width: 240px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:11px; padding: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                border-radius: 4px;">
    <h4 style="margin: 0 0 6px 0; color: #333;">LLG Classification</h4>
    <div style="margin-bottom: 6px;">
        <div style="margin: 2px 0;"><span style="background:#d73027; color:white; padding:1px 3px; border-radius:1px; font-size:9px;">AFFECTED</span> Violence Affected</div>
        <div style="margin: 2px 0;"><span style="background:#fd8d3c; color:white; padding:1px 3px; border-radius:1px; font-size:9px;">BELOW</span> Below Threshold</div>
        <div style="margin: 2px 0;"><span style="background:#2c7fb8; color:white; padding:1px 3px; border-radius:1px; font-size:9px;">NONE</span> No Violence</div>
    </div>
    <div style="font-size:9px; color:#666;">
        <strong>Period:</strong> {period_info['label']}<br>
        <strong>Criteria:</strong> >{rate_thresh:.1f}/100k & >{abs_thresh} deaths<br>
        <strong>Affected:</strong> {affected_llgs}/{total_llgs} ({affected_percentage:.1f}%)<br>
        <strong>Black borders:</strong> Region boundaries
        {f"<br><strong>🇮🇩 Indonesia events:</strong> {len(indonesia_events) if indonesia_events is not None and not indonesia_events.empty else 0}" if indonesia_events is not None else ""}
        {f"<br><strong>🇦🇺 Australia events:</strong> {len(australia_events) if australia_events is not None and not australia_events.empty else 0}" if australia_events is not None else ""}
    </div>
    </div>
    '''
    
    m.get_root().html.add_child(folium.Element(legend_html))
    
    
    return m
