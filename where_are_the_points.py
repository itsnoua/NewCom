import json
import geopandas as gpd
from shapely.geometry import shape, Point

print("Loading Buildings...")
with open('Final_Buildings_Compliance.geojson', 'r', encoding='utf-8') as f:
    bldgs = json.load(f)['features']

print("Loading Unique Points...")
with open('processed_Comapoints.geojson', 'r', encoding='utf-8') as f:
    pts = json.load(f)['features']

print(f"Total Buildings: {len(bldgs)}")
print(f"Total Unique Points (Certificates): {len(pts)}")

# 1. Analyze Points
out_of_bounds = 0
valid_pts = []
for p in pts:
    coords = p['geometry']['coordinates']
    try:
        lon, lat = float(coords[0]), float(coords[1])
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            out_of_bounds += 1
        elif lon == 0 or lat == 0:
            out_of_bounds += 1
        else:
            valid_pts.append(Point(lon, lat))
    except:
        out_of_bounds += 1

print(f"Points with severe coordinate errors (e.g., 0,0 or out of WGS84 bounds): {out_of_bounds}")
print(f"Points to test against buildings: {len(valid_pts)}")

# 2. Build GeoDataFrames for simple distance analysis
print("\nCreating spatial indices (this takes a moment)...")
gdf_bldgs = gpd.GeoDataFrame(
    {'id': [i for i in range(len(bldgs))]}, 
    geometry=[shape(b['geometry']) for b in bldgs if b.get('geometry')],
    crs="EPSG:4326"
)

gdf_pts = gpd.GeoDataFrame(
    {'id': [i for i in range(len(valid_pts))]},
    geometry=valid_pts,
    crs="EPSG:4326"
)

# Project to meters (UTM Zone 38N for Abha) to calculate real distances
gdf_bldgs_m = gdf_bldgs.to_crs("EPSG:32638")
gdf_pts_m = gdf_pts.to_crs("EPSG:32638")

print("\nPerforming nearest-neighbor analysis to find where the points are...")
# Find the distance from every point to the *nearest* building
nearest = gpd.sjoin_nearest(gdf_pts_m, gdf_bldgs_m, how='left', distance_col='dist_to_bldg')

inside_bldg = (nearest['dist_to_bldg'] == 0).sum()
within_3m = ((nearest['dist_to_bldg'] > 0) & (nearest['dist_to_bldg'] <= 3)).sum()
within_10m = ((nearest['dist_to_bldg'] > 3) & (nearest['dist_to_bldg'] <= 10)).sum()
within_50m = ((nearest['dist_to_bldg'] > 10) & (nearest['dist_to_bldg'] <= 50)).sum()
far_away = (nearest['dist_to_bldg'] > 50).sum()

print("\n--- WHERE ARE THE 14,533 POINTS? ---")
print(f"1. Exactly inside a building polygon: {inside_bldg}")
print(f"2. Outside, but very close (1-3 meters): {within_3m}")
print(f"3. Outside, close (3-10 meters): {within_10m}")
print(f"4. Across the street or in parking (10-50 meters): {within_50m}")
print(f"5. Completely completely far away (> 50 meters from ANY building): {far_away}")

print("\nConclusion:")
if (within_10m + within_50m + far_away) > 5000:
    print("The points are physically nowhere near the building polygons.")
    print("This means the coordinates entered by the engineering offices were inaccurate (dropped in the street, parking lot, or center of the neighborhood).")
