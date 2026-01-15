#!/usr/bin/env python3
"""
Diagnostic script to test share calculations
"""

import pandas as pd
import geopandas as gpd
from pathlib import Path

print('=' * 60)
print('DIAGNOSTIC: Share Calculations')
print('=' * 60)

# Load actual data
print('\n1. Loading population data...')
pop_file = Path('data/processed/admin3_payams_with_population.geojson')
if not pop_file.exists():
    print(f'   ERROR: File not found: {pop_file}')
    exit(1)

pop_data = gpd.read_file(pop_file)
print(f'   Loaded {len(pop_data)} LLGs')
print(f'   Has ADM3_PCODE: {"ADM3_PCODE" in pop_data.columns}')
if 'ADM3_PCODE' in pop_data.columns:
    print(f'   ADM3_PCODE type: {pop_data["ADM3_PCODE"].dtype}')
    print(f'   Sample ADM3_PCODE: {pop_data["ADM3_PCODE"].head(3).tolist()}')

print('\n2. Loading conflict data...')
conflict_file = Path('data/processed/ward_conflict_data.csv')
if not conflict_file.exists():
    print(f'   ERROR: File not found: {conflict_file}')
    exit(1)

conflict_data = pd.read_csv(conflict_file)
print(f'   Loaded {len(conflict_data)} conflict records')
print(f'   Has wardcode: {"wardcode" in conflict_data.columns}')

# Rename conflict data columns to match expected format
conflict_processed = conflict_data.rename(columns={
    'wardcode': 'ADM3_PCODE',
    'wardname': 'ADM3_EN',
    'countyname': 'ADM2_EN',
    'statename': 'ADM1_EN'
})

# Ensure PCODE is string
conflict_processed['ADM3_PCODE'] = conflict_processed['ADM3_PCODE'].astype(str)
pop_data = pop_data.copy()
pop_data['ADM3_PCODE'] = pop_data['ADM3_PCODE'].astype(str)

print(f'   After rename - ADM3_PCODE type: {conflict_processed["ADM3_PCODE"].dtype}')
print(f'   Sample conflict ADM3_PCODE: {conflict_processed["ADM3_PCODE"].head(3).tolist()}')

# Filter for a test period (Jan 2024 - Nov 2025)
print('\n3. Filtering conflict data for Jan 2024 - Nov 2025...')
period_conflict = conflict_processed[
    ((conflict_processed['year'] == 2024) & (conflict_processed['month'] >= 1) & (conflict_processed['month'] <= 11)) |
    ((conflict_processed['year'] == 2025) & (conflict_processed['month'] >= 1) & (conflict_processed['month'] <= 11))
].copy()

print(f'   Filtered to {len(period_conflict)} records')
print(f'   Total fatalities in period: {period_conflict["ACLED_BRD_total"].sum():.0f}')

# Test thresholds
rate_thresh = 10.0
abs_thresh = 5

print(f'\n4. Testing with thresholds: rate_thresh={rate_thresh}, abs_thresh={abs_thresh}')

# Merge conflict data with population data
if len(period_conflict) > 0 and 'ADM3_PCODE' in period_conflict.columns:
    conflict_llg = period_conflict.groupby(['ADM3_PCODE'], as_index=False).agg({
        'ACLED_BRD_state': 'sum',
        'ACLED_BRD_nonstate': 'sum',
        'ACLED_BRD_total': 'sum'
    })
    
    print(f'   Conflict LLG aggregation: {len(conflict_llg)} unique LLGs with conflict')
    print(f'   Sample conflict_llg ADM3_PCODE: {conflict_llg["ADM3_PCODE"].head(3).tolist()}')
    
    merged = pd.merge(pop_data, conflict_llg, on='ADM3_PCODE', how='left')
    print(f'   After merge: {len(merged)} LLGs')
    
    conflict_cols = ['ACLED_BRD_state', 'ACLED_BRD_nonstate', 'ACLED_BRD_total']
    merged[conflict_cols] = merged[conflict_cols].fillna(0)
    
    print(f'   LLGs with conflict: {(merged["ACLED_BRD_total"] > 0).sum()}')
    print(f'   Total fatalities in merged: {merged["ACLED_BRD_total"].sum():.0f}')
else:
    merged = pop_data.copy()
    merged['ACLED_BRD_state'] = 0
    merged['ACLED_BRD_nonstate'] = 0
    merged['ACLED_BRD_total'] = 0

# Calculate death rates
merged['acled_total_death_rate'] = (merged['ACLED_BRD_total'] / (merged['pop_count_millions'] * 1e6)) * 1e5

print(f'\n5. Calculating violence_affected...')
print(f'   LLGs with death rate > {rate_thresh}: {(merged["acled_total_death_rate"] > rate_thresh).sum()}')
print(f'   LLGs with fatalities > {abs_thresh}: {(merged["ACLED_BRD_total"] > abs_thresh).sum()}')

# Classify LLGs as violence-affected
merged['violence_affected'] = (
    (merged['acled_total_death_rate'] > rate_thresh) & 
    (merged['ACLED_BRD_total'] > abs_thresh)
)

print(f'   Total violence_affected LLGs: {merged["violence_affected"].sum()}')
print(f'   Sample violence_affected values: {merged["violence_affected"].head(5).tolist()}')

# Test ADM1 aggregation
print(f'\n6. Testing ADM1 aggregation...')
group_cols = ['ADM1_PCODE', 'ADM1_EN']

aggregated = merged.groupby(group_cols, as_index=False).agg({
    'pop_count': 'sum',
    'violence_affected': 'sum',
    'ADM3_PCODE': 'count',
    'ACLED_BRD_total': 'sum'
})

aggregated.rename(columns={'ADM3_PCODE': 'total_llgs'}, inplace=True)

print(f'   Aggregated to {len(aggregated)} provinces')
print(f'\n   Aggregated data sample:')
print(aggregated[['ADM1_PCODE', 'ADM1_EN', 'pop_count', 'violence_affected', 'total_llgs', 'ACLED_BRD_total']].head())

# Calculate share_llgs_affected
print(f'\n7. Calculating share_llgs_affected...')
aggregated['share_llgs_affected'] = aggregated['violence_affected'] / aggregated['total_llgs']
print(f'   share_llgs_affected sample:')
print(aggregated[['ADM1_PCODE', 'violence_affected', 'total_llgs', 'share_llgs_affected']].head(10))
print(f'   Non-zero shares: {(aggregated["share_llgs_affected"] > 0).sum()}')

# Calculate affected_population
print(f'\n8. Calculating affected_population...')
affected_llgs = merged[merged['violence_affected']].copy()
print(f'   Affected LLGs: {len(affected_llgs)}')

if len(affected_llgs) > 0:
    print(f'   Sample affected LLGs:')
    print(affected_llgs[['ADM1_PCODE', 'ADM3_PCODE', 'pop_count', 'ACLED_BRD_total']].head())
    
    affected_pop = affected_llgs.groupby(group_cols, as_index=False)['pop_count'].sum()
    affected_pop.rename(columns={'pop_count': 'affected_population'}, inplace=True)
    print(f'\n   Affected population by province:')
    print(affected_pop.head(10))
    
    aggregated = pd.merge(aggregated, affected_pop, on=group_cols, how='left')
    aggregated['affected_population'] = aggregated['affected_population'].fillna(0)
else:
    aggregated['affected_population'] = 0
    print('   No affected LLGs - setting affected_population to 0')

# Calculate share_population_affected
print(f'\n9. Calculating share_population_affected...')
aggregated['share_population_affected'] = aggregated.apply(
    lambda row: row['affected_population'] / row['pop_count'] if row['pop_count'] > 0 else 0.0,
    axis=1
)

print(f'   Final aggregated data with shares:')
result_cols = ['ADM1_PCODE', 'ADM1_EN', 'pop_count', 'violence_affected', 'total_llgs', 
               'affected_population', 'share_llgs_affected', 'share_population_affected']
print(aggregated[result_cols].head(10))

print(f'\n   Summary:')
print(f'   Provinces with share_llgs_affected > 0: {(aggregated["share_llgs_affected"] > 0).sum()}')
print(f'   Provinces with share_population_affected > 0: {(aggregated["share_population_affected"] > 0).sum()}')
print(f'   Max share_llgs_affected: {aggregated["share_llgs_affected"].max():.4f}')
print(f'   Max share_population_affected: {aggregated["share_population_affected"].max():.4f}')

print('\n' + '=' * 60)
print('DIAGNOSTIC COMPLETE')
print('=' * 60)
