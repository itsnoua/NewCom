import json

# Check processed_Comapoints fields and coord sample
with open('processed_Comapoints.geojson', 'r', encoding='utf-8') as f:
    proc = json.load(f)

feats = proc['features']
print("Fields:", list(feats[0]['properties'].keys()))
print()

# Sample first 3 coordinates
for i, f in enumerate(feats[:3]):
    coords = f['geometry']['coordinates']
    props  = f['properties']
    cert   = props.get('رقم الشهادة', 'NOT FOUND')
    print(f"Record {i}: coords={coords}, cert={cert}")

print()

# Check if رقم الشهادة exists and has values
has_cert_field = 'رقم الشهادة' in feats[0]['properties']
print(f"'رقم الشهادة' field exists: {has_cert_field}")

if has_cert_field:
    non_null = sum(1 for f in feats if f['properties'].get('رقم الشهادة') not in [None, '', 'nan'])
    print(f"Records with cert number: {non_null}")

# Check coord range to detect if they are WGS84 or projected (UTM)
sample_lons = [f['geometry']['coordinates'][0] for f in feats[:100]]
sample_lats = [f['geometry']['coordinates'][1] for f in feats[:100]]
print(f"\nCoord range sample:")
print(f"  X range: {min(sample_lons):.2f} to {max(sample_lons):.2f}")
print(f"  Y range: {min(sample_lats):.2f} to {max(sample_lats):.2f}")
if max(sample_lons) > 180:
    print("  --> PROJECTED coords (UTM), NOT WGS84!")
else:
    print("  --> WGS84 coords")

# Count duplicates by coordinate
coord_counter = {}
for f in feats:
    c = tuple(f['geometry']['coordinates'][:2])
    coord_counter[c] = coord_counter.get(c, 0) + 1

dups = {k: v for k, v in coord_counter.items() if v > 1}
print(f"\nDuplicate locations: {len(dups)}")
print(f"Total records at duplicate locations: {sum(dups.values())}")
print(f"Unique locations: {len(coord_counter)}")
