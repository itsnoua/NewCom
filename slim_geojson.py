import json
import os

INPUT  = 'data/Final_Buildings_Compliance.geojson'
OUTPUT = 'data/Final_Buildings_Compliance.geojson'  # Overwrite in-place

# Only keep the columns the web app actually uses
KEEP = {
    'BuildingUID',
    'LICENSENUMBER',
    'رقم المبنى_extracted',
    'رقم الشهادة_extracted',
    'Compliance_Status',
    'البلدية',
    '_clean_street',
    '_clean_municipality',
}

PRECISION = 6  # 6 decimal places = ~10 cm accuracy, more than enough for maps

def round_coords(coords):
    """Recursively round coordinate values to save space."""
    if not isinstance(coords, list):
        return coords
    if len(coords) > 0 and isinstance(coords[0], (int, float)):
        return [round(c, PRECISION) for c in coords]
    return [round_coords(c) for c in coords]

print(f"Loading {INPUT}...")
with open(INPUT, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Processing {len(data['features'])} features...")
for feature in data['features']:
    # Slim down properties
    props = feature.get('properties', {})
    feature['properties'] = {k: props.get(k, '') for k in KEEP}

    # Round coordinates
    geom = feature.get('geometry')
    if geom and 'coordinates' in geom:
        geom['coordinates'] = round_coords(geom['coordinates'])

print(f"Saving to {OUTPUT}...")
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, separators=(',', ':'))  # No spaces = smaller file

size_mb = os.path.getsize(OUTPUT) / 1024 / 1024
print(f"\nDone! Final size: {size_mb:.1f} MB")
print("Reload the page in the browser (Ctrl+F5).")
