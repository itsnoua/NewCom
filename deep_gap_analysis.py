import json
from shapely.geometry import shape, Point
from shapely.strtree import STRtree

SEP = "=" * 55

# ---- 1. Check actual fields in Final_Buildings_Compliance ----
print(SEP)
print("STEP 1: Fields inside Final_Buildings_Compliance.geojson")
with open('Final_Buildings_Compliance.geojson', 'r', encoding='utf-8') as f:
    final = json.load(f)

final_feats = final['features']
if final_feats:
    sample_props = final_feats[0]['properties']
    print("  Fields:", list(sample_props.keys()))
    # Check a few samples for cert num
    cert_key = None
    for k in sample_props.keys():
        if 'شهاد' in k or 'cert' in k.lower() or 'Cert' in k:
            cert_key = k
            break
    print(f"  Cert key found: {cert_key}")
    if cert_key:
        sample_vals = [f['properties'].get(cert_key) for f in final_feats[:20]]
        print(f"  Sample cert values (first 20): {sample_vals}")
        non_null = sum(1 for f in final_feats if f['properties'].get(cert_key) not in [None, '', 'nan', 'None', 'null'])
        print(f"  Buildings with non-null cert: {non_null}")

print()

# ---- 2. Load points (raw certs) ----
print(SEP)
print("STEP 2: Load Comapoints and check spatial match")
with open('Comapoints.geojson', 'r', encoding='utf-8') as f:
    pts_data = json.load(f)

pts_feats = pts_data['features']
print(f"  Total certificate points: {len(pts_feats)}")

# Check field names in certificates
if pts_feats:
    print(f"  Cert point fields: {list(pts_feats[0]['properties'].keys())}")

# ---- 3. Spatial match: how many certs fall inside a building ----
print()
print(SEP)
print("STEP 3: Spatial matching - certs vs buildings")

# Build R-tree from buildings
print("  Building spatial index...")
building_shapes = []
for feat in final_feats:
    try:
        geom = shape(feat['geometry'])
        if geom.is_valid:
            building_shapes.append(geom)
        else:
            building_shapes.append(geom.buffer(0))
    except:
        building_shapes.append(None)

valid_buildings = [(i, g) for i, g in enumerate(building_shapes) if g is not None]
tree = STRtree([g for _, g in valid_buildings])
idx_map = {id(g): i for i, (_, g) in enumerate(valid_buildings)}

matched_certs     = 0
unmatched_certs   = 0
multi_bldg_certs  = 0  # certs matching >1 building
bldg_cert_count   = {}  # building_idx -> count of certs

print("  Testing each certificate point...")
for feat in pts_feats:
    try:
        coords = feat['geometry']['coordinates']
        pt = Point(float(coords[0]), float(coords[1]))
        candidates = tree.query(pt)
        hits = [idx_map[id(g)] for g in candidates if g.contains(pt)]
        if hits:
            matched_certs += 1
            if len(hits) > 1:
                multi_bldg_certs += 1
            for h in hits:
                bldg_cert_count[h] = bldg_cert_count.get(h, 0) + 1
        else:
            unmatched_certs += 1
    except Exception as e:
        unmatched_certs += 1

buildings_with_1plus = sum(1 for v in bldg_cert_count.values() if v >= 1)
buildings_with_2plus = sum(1 for v in bldg_cert_count.values() if v >= 2)
total_certs_in_multi = sum(v for v in bldg_cert_count.values() if v >= 2)
max_certs_per_bldg   = max(bldg_cert_count.values()) if bldg_cert_count else 0

print()
print(SEP)
print("STEP 4: FULL GAP REPORT")
print(f"  Total certificate points:            {len(pts_feats)}")
print(f"  Certs that MATCH a building:         {matched_certs}")
print(f"  Certs OUTSIDE all buildings:         {unmatched_certs}")
print(f"  Certs matching >1 building polygon:  {multi_bldg_certs}")
print()
print(f"  Buildings with at least 1 cert:      {buildings_with_1plus}")
print(f"  Buildings with 2+ certs (stacked):   {buildings_with_2plus}")
print(f"  Max certs on one building:            {max_certs_per_bldg}")
print(f"  Total certs lost to multi-match:     {total_certs_in_multi - buildings_with_2plus}")
print()
print("  SUMMARY:")
print(f"  User expects to see:  14533 (or {len(pts_feats)} raw)")
print(f"  Website shows:        13152 buildings (total, not certs)")
print(f"  Compliant buildings:  {sum(1 for f in final_feats if f['properties'].get('Compliance_Status') in ['ممتثل','ممتثل (تقريبي)'])}")
print(f"  Spatially matched:    {matched_certs} certs -> {buildings_with_1plus} unique buildings")
print(f"  Unmatched certs:      {unmatched_certs} (outside building footprints)")
