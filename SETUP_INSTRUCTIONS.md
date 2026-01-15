# Setup and Data Generation Instructions

## Step 1: Set Up Python Environment

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

## Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 3: Regenerate Population Data

Regenerate population data for Papua New Guinea:

```bash
python extract_population.py
```

This will:
- Load boundaries from `NSO_PNG Boundaries/` directory
- Load admin1 (provinces), admin2 (districts), and admin3 (LLG) boundaries
- Extract population from `png_pop_2025_CN_100m_R2025A_v1.tif`
- Create GeoJSON files in `data/processed/`:
  - `admin3_payams_with_population.geojson`
  - `admin2_counties_with_population.geojson`
  - `admin1_states_with_population.geojson`

## Step 4: Process Conflict Data

```bash
python process_conflict_data.py
```

This will:
- Load ACLED data from `acled_Papua_New_Guinea.csv`
- Match events to admin boundaries using spatial joins
- Create `data/processed/ward_conflict_data.csv`

## Step 5: Run the Dashboard

```bash
streamlit run Home.py
```

The dashboard will be available at `http://localhost:8501`

## Verification

After running the scripts, verify the output:

- Check that `data/processed/` contains new GeoJSON files with Papua New Guinea data
- Verify the conflict data CSV has been updated
- The dashboard should load Papua New Guinea-specific data

## Troubleshooting

If you encounter issues:

1. **Missing packages**: Make sure the virtual environment is activated and all packages from `requirements.txt` are installed
2. **File not found errors**: Ensure `NSO_PNG Boundaries/` directory exists with boundary shapefiles and `png_pop_2025_CN_100m_R2025A_v1.tif` is in the project root
3. **Population extraction takes time**: This is normal - extracting from raster can take 2-5 minutes depending on your system
