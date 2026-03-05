import geopandas as gpd
import pandas as pd
import re
import os
import json
def extract_from_html(html_str, keyword):
    """
    Extracts the value adjacent to a specific keyword from the exported FME HTML table.
    Looks for <td>keyword</td>\s*<td>value</td>
    """
    if not isinstance(html_str, str):
        return None
    
    # regex pattern to find <td>Keyword</td> then capture the next <td>
    pattern = rf'<td>\s*{re.escape(keyword)}\s*</td>\s*<td[^>]*>(.*?)</td>'
    match = re.search(pattern, html_str, re.IGNORECASE | re.DOTALL)
    
    if match:
        val = match.group(1).strip()
        if val == '&lt;Null&gt;' or val == '':
            return None
        return val
    return None

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

def process_datasets(points_file="Comapoints.geojson", buildings_file="ComBulid.geojson"):
    
    print(f"Reading {points_file}...")
    try:
        gdf_points = read_geojson_safe(points_file)
        print(f"Original {points_file} count: {len(gdf_points)}")
    except Exception as e:
        print(f"Error reading {points_file}: {e}")
        return

    # Check for duplicates in points
    dup_cols_points = [col for col in gdf_points.columns if col in ['رقم الشهادة', 'رقم المبنى']]
    if dup_cols_points:
        print(f"Removing duplicates in {points_file} based on columns: {dup_cols_points}")
        gdf_points = gdf_points.drop_duplicates(subset=dup_cols_points)
        print(f"Count after dropping duplicates: {len(gdf_points)}")
    else:
        print(f"No columns named 'رقم الشهادة' or 'رقم المبنى' found in {points_file}")

    # CRS check
    if not gdf_points.crs or gdf_points.crs.to_string() != "EPSG:4326":
        print(f"Current CRS for {points_file} is {gdf_points.crs}. Converting to EPSG:4326...")
        gdf_points = gdf_points.to_crs("EPSG:4326")
    else:
        print(f"CRS for {points_file} is already EPSG:4326")

    output_points = "processed_" + points_file
    print(f"Saving to {output_points}...")
    gdf_points.to_file(output_points, driver="GeoJSON")
    print(f"Saved {output_points}")


    print(f"\nReading {buildings_file}...")
    try:
        gdf_buildings = read_geojson_safe(buildings_file)
        print(f"Original {buildings_file} count: {len(gdf_buildings)}")
    except Exception as e:
        print(f"Error reading {buildings_file}: {e}")
        return

    # Extract BuildingUID from description HTML if present
    if 'description' in gdf_buildings.columns:
        print("Extracting BuildingUID and LICENSENUMBER from HTML descriptions...")
        gdf_buildings['BuildingUID'] = gdf_buildings['description'].apply(lambda x: extract_from_html(x, 'BuildingUID'))
        gdf_buildings['LICENSENUMBER'] = gdf_buildings['description'].apply(lambda x: extract_from_html(x, 'LICENSENUMBER'))
        gdf_buildings['رقم المبنى_extracted'] = gdf_buildings['description'].apply(lambda x: extract_from_html(x, 'رقم المبنى'))
        gdf_buildings['رقم الشهادة_extracted'] = gdf_buildings['description'].apply(lambda x: extract_from_html(x, 'رقم الشهادة'))

        # Create a unified building identifier for deduplication
        # Priorities: رقم المبنى -> BuildingUID -> id
        def get_identifier(row):
            if pd.notna(row.get('رقم المبنى_extracted')): return row['رقم المبنى_extracted']
            if pd.notna(row.get('BuildingUID')): return row['BuildingUID']
            if pd.notna(row.get('رقم الشهادة_extracted')): return row['رقم الشهادة_extracted']
            return None
        
        gdf_buildings['dedup_id'] = gdf_buildings.apply(get_identifier, axis=1)
        
        before_len = len(gdf_buildings)
        # Drop duplicates where dedup_id is not null and is duplicated
        gdf_buildings = gdf_buildings[~gdf_buildings.duplicated(subset=['dedup_id'], keep='first') | gdf_buildings['dedup_id'].isna()]
        
        print(f"Buildings count after dropping duplicates based on Extracted Building ID: {len(gdf_buildings)} (Removed {before_len - len(gdf_buildings)} duplicates)")
        
        # Cleanup temporary column
        gdf_buildings = gdf_buildings.drop(columns=['dedup_id'])
    else:
        dup_cols_b = [col for col in gdf_buildings.columns if col in ['رقم الشهادة', 'رقم المبنى', 'BuildingUID']]
        if dup_cols_b:
            print(f"Removing duplicates in {buildings_file} based on columns: {dup_cols_b}")
            before_len = len(gdf_buildings)
            gdf_buildings = gdf_buildings.drop_duplicates(subset=dup_cols_b)
            print(f"Count after dropping duplicates: {len(gdf_buildings)} (Removed {before_len - len(gdf_buildings)} duplicates)")

    # CRS check
    if not gdf_buildings.crs or gdf_buildings.crs.to_string() != "EPSG:4326":
        print(f"Current CRS for {buildings_file} is {gdf_buildings.crs}. Converting to EPSG:4326...")
        gdf_buildings = gdf_buildings.to_crs("EPSG:4326")
    else:
        print(f"CRS for {buildings_file} is already EPSG:4326")

    output_buildings = "processed_" + buildings_file
    print(f"Saving to {output_buildings}...")
    gdf_buildings.to_file(output_buildings, driver="GeoJSON")
    print(f"Saved {output_buildings}")
    
    print("\nProcessing completed successfully.")

if __name__ == "__main__":
    process_datasets("Comapoints.geojson", "ComBulid.geojson")
