import json

INPUT_FILE = 'processed_Comapoints.geojson'
OUTPUT_FILE = 'processed_Comapoints_unique.geojson'

print(f"Reading {INPUT_FILE}...")
with open(INPUT_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

features = data.get('features', [])
total = len(features)
print(f"Total original records: {total}")

# Keep track of seen coordinates (rounded to 6 decimals to avoid floating point issues, ~ 0.1 meter accuracy)
seen_coords = set()
unique_features = []
duplicates_removed = 0

for f in features:
    coords = f.get('geometry', {}).get('coordinates')
    if coords and len(coords) >= 2:
        # Tuple of (lon, lat) rounded to 6 decimal places
        coord_key = (round(float(coords[0]), 6), round(float(coords[1]), 6))
        
        if coord_key not in seen_coords:
            seen_coords.add(coord_key)
            unique_features.append(f)
        else:
            duplicates_removed += 1
    else:
        # Keep features without valid coords just in case, or drop them? 
        # Usually better to drop if we are doing spatial mapping
        duplicates_removed += 1

data['features'] = unique_features

print(f"Removed duplicates (same exact location): {duplicates_removed}")
print(f"Remaining unique records: {len(unique_features)}")

print(f"Saving to {OUTPUT_FILE}...")
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False)

print("Done. To apply this, we will rename the file to override the original.")
