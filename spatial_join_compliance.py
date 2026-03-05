import geopandas as gpd
import pandas as pd
import json

def read_geojson_safe(filepath):
    print(f"Reading {filepath} safely without auto-date parsing...")
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    features = data.get('features', [])
    crs = "EPSG:4326"
    if 'crs' in data and 'properties' in data['crs'] and 'name' in data['crs']['properties']:
        crs_name = data['crs']['properties']['name']
        if 'CRS84' in crs_name or '4326' in crs_name:
            crs = "EPSG:4326"
        else:
            crs = crs_name
    return gpd.GeoDataFrame.from_features(features, crs=crs)

def spatial_join_compliance():
    buildings_file = "processed_ComBulid.geojson"
    points_file = "processed_Comapoints.geojson"
    output_file = "Final_Buildings_Compliance.geojson"

    print(f"Loading {buildings_file}...")
    try:
        gdf_buildings = read_geojson_safe(buildings_file)
    except Exception as e:
        print(f"Error reading {buildings_file}: {e}")
        return

    print(f"Loading {points_file}...")
    try:
        gdf_points = read_geojson_safe(points_file)
        
        # Remove duplicate coordinates
        initial_cnt = len(gdf_points)
        gdf_points['geom_str'] = gdf_points.geometry.astype(str)
        gdf_points = gdf_points.drop_duplicates(subset=['geom_str']).drop(columns=['geom_str'])
        print(f"Removed {initial_cnt - len(gdf_points)} duplicate coordinates from points. Remaining: {len(gdf_points)}")
        
    except Exception as e:
        print(f"Error reading {points_file}: {e}")
        return

    print("Projecting to EPSG:32638 (UTM Zone 38N) for accurate meter buffering...")
    gdf_buildings_proj = gdf_buildings.to_crs("EPSG:32638")
    gdf_points_proj = gdf_points.to_crs("EPSG:32638")

    # Keep only geometry + key columns from points to avoid column conflicts
    has_muni = 'البلدية' in gdf_points_proj.columns
    has_cert = 'رقم الشهادة' in gdf_points_proj.columns
    
    pts_cols = ['geometry']
    if has_muni: pts_cols.append('البلدية')
    if has_cert: pts_cols.append('رقم الشهادة')
    pts_slim = gdf_points_proj[pts_cols].copy()

    print("Performing Spatial Join (Exact Intersects)...")
    exact_join = gpd.sjoin(gdf_buildings_proj, pts_slim, how='inner', predicate='intersects')
    exact_joined_idx = set(exact_join.index.unique())

    # Extract municipality and cert number for exact matches
    municipality_map = {}
    cert_map = {}
    if has_muni and 'البلدية' in exact_join.columns:
        for idx, row in exact_join.groupby(level=0):
            municipality_map[idx] = str(row['البلدية'].iloc[0]).strip()
    if has_cert and 'رقم الشهادة' in exact_join.columns:
        for idx, row in exact_join.groupby(level=0):
            val = row['رقم الشهادة'].iloc[0]
            if pd.notna(val): cert_map[idx] = str(val).strip()

    print("Buffering points by 3 meters for approximate matches...")
    pts_buffered = pts_slim.copy()
    pts_buffered['geometry'] = pts_buffered.geometry.buffer(3)

    # Only test buildings not already marked exact match
    non_exact_idx = [i for i in gdf_buildings_proj.index if i not in exact_joined_idx]
    buildings_for_buffer = gdf_buildings_proj.loc[non_exact_idx]

    if not buildings_for_buffer.empty:
        buffer_join = gpd.sjoin(buildings_for_buffer, pts_buffered, how='inner', predicate='intersects')
        buffer_joined_idx = set(buffer_join.index.unique())

        if has_muni and 'البلدية' in buffer_join.columns:
            for idx, row in buffer_join.groupby(level=0):
                if idx not in municipality_map:
                    municipality_map[idx] = str(row['البلدية'].iloc[0]).strip()
        if has_cert and 'رقم الشهادة' in buffer_join.columns:
            for idx, row in buffer_join.groupby(level=0):
                if idx not in cert_map:
                    val = row['رقم الشهادة'].iloc[0]
                    if pd.notna(val): cert_map[idx] = str(val).strip()
    else:
        buffer_joined_idx = set()

    print("Adding 'Compliance_Status' column...")
    def get_status(idx):
        if idx in exact_joined_idx:
            return 'ممتثل'
        elif idx in buffer_joined_idx:
            return 'ممتثل (تقريبي)'
        else:
            return 'غير ممتثل'

    gdf_buildings_proj['Compliance_Status'] = gdf_buildings_proj.index.map(get_status)

    # Assign municipality and cert number to compliant buildings
    gdf_buildings_proj['البلدية'] = gdf_buildings_proj.index.map(lambda i: municipality_map.get(i, None))
    gdf_buildings_proj['رقم الشهادة'] = gdf_buildings_proj.index.map(lambda i: cert_map.get(i, None))

    print("Assigning 'البلدية' to non-compliant buildings via nearest-neighbor...")
    compliant_with_muni = gdf_buildings_proj[gdf_buildings_proj['البلدية'].notna()].copy()
    non_compliant = gdf_buildings_proj[gdf_buildings_proj['البلدية'].isna()].copy()

    if has_muni and len(compliant_with_muni) > 0 and len(non_compliant) > 0:
        # Build GeoDataFrames using centroids for faster nearest join
        known_gdf = gpd.GeoDataFrame(
            {'البلدية': compliant_with_muni['البلدية'].values},
            geometry=compliant_with_muni.geometry.centroid.values,
            crs=gdf_buildings_proj.crs
        )

        unknown_gdf = gpd.GeoDataFrame(
            {'orig_idx': non_compliant.index.tolist()},
            geometry=non_compliant.geometry.centroid.values,
            crs=gdf_buildings_proj.crs
        )

        print(f"  Running nearest join on {len(unknown_gdf)} buildings...")
        nearest = gpd.sjoin_nearest(unknown_gdf, known_gdf[['geometry', 'البلدية']], how='left')

        if 'البلدية' in nearest.columns:
            for _, row in nearest.iterrows():
                orig_idx = row['orig_idx']
                muni = row['البلدية']
                if pd.notna(muni):
                    gdf_buildings_proj.at[orig_idx, 'البلدية'] = str(muni).strip()

    print("Projecting back to WGS84 (EPSG:4326)...")
    final_gdf = gdf_buildings_proj.to_crs("EPSG:4326")

    print(f"Saving final result to {output_file}...")
    final_gdf.to_file(output_file, driver='GeoJSON')

    comp_exact = (final_gdf['Compliance_Status'] == 'ممتثل').sum()
    comp_buf   = (final_gdf['Compliance_Status'] == 'ممتثل (تقريبي)').sum()
    noncomp    = (final_gdf['Compliance_Status'] == 'غير ممتثل').sum()
    with_muni  = final_gdf['البلدية'].notna().sum()
    print("\n--- Statistics ---")
    print(f"Total Buildings: {len(final_gdf)}")
    print(f"Compliant (Direct): {comp_exact}")
    print(f"Compliant (Buffered): {comp_buf}")
    print(f"Non-Compliant: {noncomp}")
    print(f"Buildings with Municipality: {with_muni}")
    print("------------------\n")
    print("Spatial Join Completed Successfully!")

if __name__ == "__main__":
    spatial_join_compliance()
