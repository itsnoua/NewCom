import geopandas as gpd
import json
import os

def strip_z_coordinates(input_file="Final_Buildings_Compliance.geojson", output_file="data/Final_Buildings_Compliance.geojson"):
    print(f"Loading {input_file}...")
    
    # Read the JSON safely to bypass date parsing issues
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Strip Z coordinates defensively
    def strip_z(coords):
        if not isinstance(coords, list): return
        if len(coords) > 0 and isinstance(coords[0], (int, float)):
            if len(coords) > 2:
                del coords[2:]
        else:
            for i in range(len(coords)):
                strip_z(coords[i])
                
    print("Stripping Z-coordinates from geometries...")
    for feature in data.get('features', []):
        geom = feature.get('geometry')
        if geom and 'coordinates' in geom:
            strip_z(geom['coordinates'])

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Write optimized GeoJSON
    print(f"Saving optimized 2D GeoJSON to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
        
    print("Done! Reload your browser page at http://localhost:8000")

if __name__ == "__main__":
    strip_z_coordinates()
