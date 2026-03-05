import json

# ---- 1. Comapoints (raw certificates) ----
print("=" * 50)
print("1. Comapoints.geojson (Raw Certificates)")
with open('Comapoints.geojson', 'r', encoding='utf-8') as f:
    raw = json.load(f)

raw_feats = raw.get('features', [])
total_raw = len(raw_feats)
print(f"   Total records: {total_raw}")

no_geom          = sum(1 for f in raw_feats if f.get('geometry') is None)
null_coords      = sum(1 for f in raw_feats if f.get('geometry') and f['geometry'].get('coordinates') is None)

def is_valid_coord(f):
    g = f.get('geometry')
    if not g: return False
    c = g.get('coordinates')
    if not c or len(c) < 2: return False
    try:
        lon, lat = float(c[0]), float(c[1])
        return -180 <= lon <= 180 and -90 <= lat <= 90 and not (lon == 0 and lat == 0)
    except:
        return False

valid_coords   = sum(1 for f in raw_feats if is_valid_coord(f))
invalid_coords = total_raw - valid_coords

print(f"   No geometry:     {no_geom}")
print(f"   Null coords:     {null_coords}")
print(f"   Valid coords:    {valid_coords}")
print(f"   Invalid coords:  {invalid_coords}")

# ---- 2. processed_Comapoints ----
print()
print("=" * 50)
print("2. processed_Comapoints.geojson")
with open('processed_Comapoints.geojson', 'r', encoding='utf-8') as f:
    proc = json.load(f)

proc_feats = proc.get('features', [])
print(f"   Total records: {len(proc_feats)}")
diff_proc = total_raw - len(proc_feats)
print(f"   Lost vs raw:   {diff_proc}")

# ---- 3. Final_Buildings_Compliance ----
print()
print("=" * 50)
print("3. Final_Buildings_Compliance.geojson (Buildings)")
with open('Final_Buildings_Compliance.geojson', 'r', encoding='utf-8') as f:
    final = json.load(f)

final_feats = final.get('features', [])
total_bldg     = len(final_feats)
compliant      = sum(1 for f in final_feats if f['properties'].get('Compliance_Status') == 'ممتثل')
comp_buffer    = sum(1 for f in final_feats if f['properties'].get('Compliance_Status') == 'ممتثل (تقريبي)')
non_compliant  = sum(1 for f in final_feats if f['properties'].get('Compliance_Status') == 'غير ممتثل')
with_cert      = sum(1 for f in final_feats if f['properties'].get('رقم الشهادة') not in [None, '', 'nan', 'None'])
compliant_total = compliant + comp_buffer

print(f"   Total buildings:           {total_bldg}")
print(f"   Compliant (exact):         {compliant}")
print(f"   Compliant (buffer ~3m):    {comp_buffer}")
print(f"   Non-Compliant:             {non_compliant}")
print(f"   Total compliant:           {compliant_total}")
print(f"   Buildings with cert-num:   {with_cert}")

# ---- 4. Summary of gaps ----
print()
print("=" * 50)
print("4. GAP ANALYSIS")
print(f"   Raw certs in file:         {total_raw}")
print(f"   Compliant buildings found: {compliant_total}")
print(f"   GAP (unmatched certs):     {total_raw - compliant_total}")
print()
print(f"   Possible reasons:")
print(f"   a) Certs with invalid/missing coords:   {invalid_coords}")
print(f"   b) Multiple certs on same building:     (need to check)")
print()

# ---- 5. Check for duplicate cert assignments (multiple certs per building) ----
cert_counts = {}
for f in final_feats:
    cert = f['properties'].get('رقم الشهادة')
    if cert and cert not in ['', 'nan', 'None', None]:
        cert_counts[cert] = cert_counts.get(cert, 0) + 1

dup_certs = {k: v for k, v in cert_counts.items() if v > 1}
print(f"   Unique cert numbers in buildings: {len(cert_counts)}")
print(f"   Cert numbers assigned to >1 bldg: {len(dup_certs)}")

# ---- 6. Check for multiple certs on same building (sjoin gives many-to-one) ----
# i.e. how many raw certs land in same polygon
print()
print("   Top 5 duplicate cert assignments:")
for cert, count in sorted(dup_certs.items(), key=lambda x: -x[1])[:5]:
    print(f"     Cert {cert} -> {count} buildings")
