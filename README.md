# Papua New Guinea Violence Analysis Dashboard

Interactive dashboard for analyzing conflict data in Papua New Guinea with spatial visualization and administrative level analysis.

## Setup

1. **Create and activate virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Extract population data (recommended for faster loading):**
   ```bash
   python extract_population.py
   ```
   This will create pre-extracted GeoJSON files with population data in `data/processed/`.

4. **Run the app:**
   ```bash
   streamlit run Home.py
   ```

## Data Files Required

- `NSO_PNG Boundaries/` - Administrative boundaries from PNG National Statistical Office
  - `png_prov_boundaries_2011census_region.shp` - Provinces (admin1)
  - `png_dist_boundaries_2011census_region.shp` - Districts (admin2)
  - `png_llg_boundaries_2011census_region.shp` - Local Level Governments (admin3)
- `png_pop_2025_CN_100m_R2025A_v1.tif` - Population raster
- `acled_Papua_New_Guinea.csv` - ACLED conflict event data

## Features

- **Spatial Analysis**: Interactive maps showing violence-affected payams, counties, and states
- **Payam Analysis**: Detailed time series analysis for individual payams
- **Data Export**: Download processed data and visualizations

## Administrative Levels

Papua New Guinea uses:
- **Admin Level 1**: States/Regions
- **Admin Level 2**: Counties/Districts
- **Admin Level 3**: Payams/Sub-districts

## Notes

- First load may take time if population data needs to be extracted from raster
- Pre-extracted population files significantly improve load times
- The app automatically extracts population on-the-fly if pre-extracted files are not available

