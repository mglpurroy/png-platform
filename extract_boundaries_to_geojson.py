"""
Extract NSO PNG boundaries to GeoJSON format for easier loading
Run this once to create GeoJSON files from NSO PNG shapefiles
"""

import sys
from pathlib import Path
import geopandas as gpd
import zipfile
import tempfile
import shutil

# Check if we're in a virtual environment or if packages are available
try:
    import geopandas as gpd
    import fiona
except ImportError as e:
    venv_python = Path(__file__).parent / "venv" / "bin" / "python"
    if venv_python.exists():
        print("=" * 60)
        print("ERROR: Required packages not found in current Python environment")
        print("=" * 60)
        print(f"Missing: {e}")
        print(f"\nPlease activate the virtual environment first:")
        print(f"  source venv/bin/activate")
        print(f"\nOr run with venv Python directly:")
        print(f"  {venv_python} {__file__}")
        print("=" * 60)
        sys.exit(1)
    else:
        print("ERROR: Required packages not found. Please install:")
        print("  pip install -r requirements.txt")
        sys.exit(1)

# Data paths
DATA_PATH = Path("data/")
BOUNDARIES_PATH = DATA_PATH / "boundaries"
NSO_BOUNDARIES_DIR = Path("NSO_PNG Boundaries")

# Create boundaries directory
BOUNDARIES_PATH.mkdir(parents=True, exist_ok=True)

def map_nso_columns(gdf, level):
    """Map NSO PNG boundary columns to standard ADM format"""
    gdf = gdf.copy()
    
    # Common column name patterns in PNG boundaries
    # Try to find and map columns based on common naming patterns
    for col in gdf.columns:
        col_upper = col.upper()
        
        if level == 1:  # Province/Region level
            # Look for province/region codes and names
            if any(x in col_upper for x in ['PROV', 'REGION', 'ADM1']):
                if any(x in col_upper for x in ['CODE', 'ID', 'PCODE']):
                    if 'ADM1_PCODE' not in gdf.columns:
                        gdf['ADM1_PCODE'] = gdf[col].astype(str)
                elif any(x in col_upper for x in ['NAME', 'EN']):
                    if 'ADM1_EN' not in gdf.columns:
                        gdf['ADM1_EN'] = gdf[col].astype(str)
        
        elif level == 2:  # District level
            # Look for district codes and names
            if any(x in col_upper for x in ['DIST', 'ADM2']):
                if any(x in col_upper for x in ['CODE', 'ID', 'PCODE']):
                    if 'ADM2_PCODE' not in gdf.columns:
                        gdf['ADM2_PCODE'] = gdf[col].astype(str)
                elif any(x in col_upper for x in ['NAME', 'EN']):
                    if 'ADM2_EN' not in gdf.columns:
                        gdf['ADM2_EN'] = gdf[col].astype(str)
            # Also look for parent province columns
            if any(x in col_upper for x in ['PROV', 'REGION', 'ADM1']):
                if any(x in col_upper for x in ['CODE', 'ID', 'PCODE']):
                    if 'ADM1_PCODE' not in gdf.columns:
                        gdf['ADM1_PCODE'] = gdf[col].astype(str)
                elif any(x in col_upper for x in ['NAME', 'EN']):
                    if 'ADM1_EN' not in gdf.columns:
                        gdf['ADM1_EN'] = gdf[col].astype(str)
        
        elif level == 3:  # LLG level
            # Look for LLG codes and names
            if any(x in col_upper for x in ['LLG', 'ADM3']):
                if any(x in col_upper for x in ['CODE', 'ID', 'PCODE']):
                    if 'ADM3_PCODE' not in gdf.columns:
                        gdf['ADM3_PCODE'] = gdf[col].astype(str)
                elif any(x in col_upper for x in ['NAME', 'EN']):
                    if 'ADM3_EN' not in gdf.columns:
                        gdf['ADM3_EN'] = gdf[col].astype(str)
            # Also look for parent district and province columns
            if any(x in col_upper for x in ['DIST', 'ADM2']):
                if any(x in col_upper for x in ['CODE', 'ID', 'PCODE']):
                    if 'ADM2_PCODE' not in gdf.columns:
                        gdf['ADM2_PCODE'] = gdf[col].astype(str)
                elif any(x in col_upper for x in ['NAME', 'EN']):
                    if 'ADM2_EN' not in gdf.columns:
                        gdf['ADM2_EN'] = gdf[col].astype(str)
            if any(x in col_upper for x in ['PROV', 'REGION', 'ADM1']):
                if any(x in col_upper for x in ['CODE', 'ID', 'PCODE']):
                    if 'ADM1_PCODE' not in gdf.columns:
                        gdf['ADM1_PCODE'] = gdf[col].astype(str)
                elif any(x in col_upper for x in ['NAME', 'EN']):
                    if 'ADM1_EN' not in gdf.columns:
                        gdf['ADM1_EN'] = gdf[col].astype(str)
    
    # Ensure required columns exist (create from index if needed)
    if level >= 1:
        if 'ADM1_PCODE' not in gdf.columns:
            gdf['ADM1_PCODE'] = gdf.index.astype(str)
        if 'ADM1_EN' not in gdf.columns:
            gdf['ADM1_EN'] = gdf['ADM1_PCODE']
    
    if level >= 2:
        if 'ADM2_PCODE' not in gdf.columns:
            gdf['ADM2_PCODE'] = gdf.index.astype(str)
        if 'ADM2_EN' not in gdf.columns:
            gdf['ADM2_EN'] = gdf['ADM2_PCODE']
    
    if level >= 3:
        if 'ADM3_PCODE' not in gdf.columns:
            gdf['ADM3_PCODE'] = gdf.index.astype(str)
        if 'ADM3_EN' not in gdf.columns:
            gdf['ADM3_EN'] = gdf['ADM3_PCODE']
    
    return gdf

def extract_nso_boundaries_to_geojson():
    """Extract NSO PNG boundaries and convert to GeoJSON"""
    print("=" * 60)
    print("Extracting NSO PNG Boundaries to GeoJSON")
    print("=" * 60)
    
    if not NSO_BOUNDARIES_DIR.exists():
        print(f"Error: {NSO_BOUNDARIES_DIR} directory not found")
        return
    
    try:
        # Load admin1 (provinces/regions)
        admin1_shp = NSO_BOUNDARIES_DIR / "png_prov_boundaries_2011census_region.shp"
        if admin1_shp.exists():
            print(f"\nLoading admin1 (provinces) from {admin1_shp.name}...")
            admin1_gdf = gpd.read_file(str(admin1_shp))
            admin1_gdf = admin1_gdf.to_crs('EPSG:4326')
            print(f"  Original columns: {list(admin1_gdf.columns)}")
            
            # Map columns to standard format
            admin1_gdf = map_nso_columns(admin1_gdf, level=1)
            
            # Save as GeoJSON
            output_file = BOUNDARIES_PATH / "admin1_regions.geojson"
            admin1_gdf.to_file(output_file, driver='GeoJSON')
            print(f"  ✓ Saved {len(admin1_gdf)} provinces to {output_file}")
            print(f"  File size: {output_file.stat().st_size / 1024:.2f} KB")
        else:
            print(f"Warning: {admin1_shp.name} not found")
        
        # Load admin2 (districts)
        admin2_shp = NSO_BOUNDARIES_DIR / "png_dist_boundaries_2011census_region.shp"
        if admin2_shp.exists():
            print(f"\nLoading admin2 (districts) from {admin2_shp.name}...")
            admin2_gdf = gpd.read_file(str(admin2_shp))
            admin2_gdf = admin2_gdf.to_crs('EPSG:4326')
            print(f"  Original columns: {list(admin2_gdf.columns)}")
            
            # Map columns to standard format
            admin2_gdf = map_nso_columns(admin2_gdf, level=2)
            
            # Save as GeoJSON for admin2
            output_file = BOUNDARIES_PATH / "admin2_subprefectures.geojson"
            admin2_gdf.to_file(output_file, driver='GeoJSON')
            print(f"  ✓ Saved {len(admin2_gdf)} districts to {output_file}")
            print(f"  File size: {output_file.stat().st_size / 1024:.2f} KB")
        else:
            print(f"Warning: {admin2_shp.name} not found")
        
        # Load admin3 (LLG - Local Level Government)
        admin3_shp = NSO_BOUNDARIES_DIR / "png_llg_boundaries_2011census_region.shp"
        if admin3_shp.exists():
            print(f"\nLoading admin3 (LLG) from {admin3_shp.name}...")
            admin3_gdf = gpd.read_file(str(admin3_shp))
            admin3_gdf = admin3_gdf.to_crs('EPSG:4326')
            print(f"  Original columns: {list(admin3_gdf.columns)}")
            
            # Map columns to standard format
            admin3_gdf = map_nso_columns(admin3_gdf, level=3)
            
            # Save as GeoJSON for admin3
            output_file = BOUNDARIES_PATH / "admin3_subprefectures.geojson"
            admin3_gdf.to_file(output_file, driver='GeoJSON')
            print(f"  ✓ Saved {len(admin3_gdf)} LLGs to {output_file}")
            print(f"  File size: {output_file.stat().st_size / 1024:.2f} KB")
        else:
            print(f"Warning: {admin3_shp.name} not found")
            # If admin3 doesn't exist, use admin2 as admin3 for compatibility
            if admin2_shp.exists() and 'admin2_gdf' in locals():
                print("  Using admin2 as admin3 for compatibility...")
                admin3_gdf = admin2_gdf.copy()
                if 'ADM2_PCODE' in admin3_gdf.columns:
                    admin3_gdf['ADM3_PCODE'] = admin3_gdf['ADM2_PCODE']
                if 'ADM2_EN' in admin3_gdf.columns:
                    admin3_gdf['ADM3_EN'] = admin3_gdf['ADM2_EN']
                output_file = BOUNDARIES_PATH / "admin3_subprefectures.geojson"
                admin3_gdf.to_file(output_file, driver='GeoJSON')
                print(f"  ✓ Saved as admin3 (for compatibility) to {output_file}")
        
        print("\n" + "=" * 60)
        print("Boundary extraction complete!")
        print("=" * 60)
        print(f"\nOutput files saved to: {BOUNDARIES_PATH}")
        print("  - admin1_regions.geojson")
        print("  - admin2_subprefectures.geojson")
        print("  - admin3_subprefectures.geojson")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    extract_nso_boundaries_to_geojson()
