import geopandas as gpd
import json

def ultimate_fix():
    print("Loading Final_Buildings_Compliance.geojson...")
    # Read using geopandas to let it handle the complex geometries and force 2D
    # It will automatically drop Z if we force it via wkb or just by saving it normally
    try:
        with open('Final_Buildings_Compliance.geojson', 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        print("Forcing 2D coordinates recursively...")    
        def force_2d(coords):
            if not isinstance(coords, list): return
            if len(coords) > 0 and isinstance(coords[0], (int, float)):
                if len(coords) > 2:
                    del coords[2:] # Keep only X, Y
            else:
                for item in coords:
                    force_2d(item)
                    
        for feature in data.get('features', []):
            geom = feature.get('geometry')
            if geom and 'coordinates' in geom:
                force_2d(geom['coordinates'])

            # Clean properties of NaNs which break MapLibre
            props = feature.get('properties', {})
            clean_props = {}
            # These special columns should NOT be treated as NaN even if they contain 'nan' strings
            preserve_as_is = {'Compliance_Status', 'البلدية'}
            for k, v in props.items():
                if v is None:
                    clean_props[k] = ""
                elif k not in preserve_as_is and str(v).lower() in ['nan', '<null>', 'null']:
                    clean_props[k] = ""
                else:
                    clean_props[k] = v
                    
            # Ensure Compliance_Status defaults correctly
            if 'Compliance_Status' not in clean_props or not clean_props['Compliance_Status']:
                clean_props['Compliance_Status'] = 'غير ممتثل'
            
            feature['properties'] = clean_props

        print("Writing to data/Final_Buildings_Compliance.geojson...")
        with open('data/Final_Buildings_Compliance.geojson', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
            
        print("Success! Reload the page.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    ultimate_fix()
