import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import os

def process_compliance_data(compliance_file_path, buildings_file_path, output_path="processed_data.geojson"):
    """
    يقوم بقراءة ملف إحداثيات شهادات الامتثال وملف مباني شوارع الأنسنة.
    - تحويل أعمدة Latitude و Longitude إلى بيانات جغرافية.
    - إزالة السجلات المكررة بناءً على 'رقم المبنى' أو 'رقم الشهادة'.
    - توحيد النظام الإحداثي إلى WGS84 (EPSG:4326).
    """
    
    # 1. قراءة ملف إحداثيات شهادات الامتثال (CSV أو Excel)
    print(f"Reading compliance data from {compliance_file_path}...")
    if compliance_file_path.endswith('.csv'):
        df_compliance = pd.read_csv(compliance_file_path)
    elif compliance_file_path.endswith(('.xlsx', '.xls')):
        df_compliance = pd.read_excel(compliance_file_path)
    else:
        # إذا كان الملف GeoJSON مثلاً
        df_compliance = gpd.read_file(compliance_file_path)

    # تحويل خطوط الطول والعرض إلى نقاط جغرافية إذا كانت البيانات في DataFrame
    if not isinstance(df_compliance, gpd.GeoDataFrame):
        # البحث عن أعمدة خطوط الطول والعرض المحتملة
        lat_col = next((col for col in df_compliance.columns if col.lower() in ['lat', 'latitude', 'y', 'خط العرض']), None)
        lon_col = next((col for col in df_compliance.columns if col.lower() in ['lon', 'long', 'longitude', 'x', 'خط الطول']), None)
        
        if lat_col and lon_col:
            # التأكد من تحويلها إلى أرقام
            df_compliance[lat_col] = pd.to_numeric(df_compliance[lat_col], errors='coerce')
            df_compliance[lon_col] = pd.to_numeric(df_compliance[lon_col], errors='coerce')
            
            # إسقاط القيم الفارغة في الإحداثيات إن وجدت
            df_compliance = df_compliance.dropna(subset=[lat_col, lon_col])
            
            # إنشاء العمود الجغرافي
            geometry = [Point(xy) for xy in zip(df_compliance[lon_col], df_compliance[lat_col])]
            gdf_compliance = gpd.GeoDataFrame(df_compliance, geometry=geometry, crs="EPSG:4326")
        else:
            raise ValueError("لم يتم العثور على أعمدة Latitude و Longitude في ملف الامتثال.")
    else:
        gdf_compliance = df_compliance

    # 2. إزالة السجلات المكررة بناءً على "رقم المبنى" أو "رقم الشهادة"
    columns_to_check_duplicates = []
    
    # البحث عن الأعمدة المتعلقة برقم المبنى ورقم الشهادة
    cert_col = next((col for col in gdf_compliance.columns if 'رقم الشهادة' in str(col) or 'cert' in str(col).lower()), None)
    building_col = next((col for col in gdf_compliance.columns if 'رقم المبنى' in str(col) or 'building' in str(col).lower()), None)
    
    if cert_col: columns_to_check_duplicates.append(cert_col)
    if building_col: columns_to_check_duplicates.append(building_col)
    
    if columns_to_check_duplicates:
        print(f"Removing duplicates based on: { columns_to_check_duplicates }")
        gdf_compliance = gdf_compliance.drop_duplicates(subset=columns_to_check_duplicates)
    else:
        print("لم يتم العثور على أعمدة 'رقم المبنى' أو 'رقم الشهادة' لإزالة المكررات.")

    # 3. توحيد إحداثيات ملف الامتثال إلى EPSG:4326
    if gdf_compliance.crs and gdf_compliance.crs != "EPSG:4326":
        gdf_compliance = gdf_compliance.to_crs("EPSG:4326")
    elif not gdf_compliance.crs:
        gdf_compliance.set_crs("EPSG:4326", inplace=True)

    # 4. قراءة ملف مباني شوارع الأنسنة (GeoJSON أو KMZ)
    print(f"Reading buildings data from {buildings_file_path}...")
    if buildings_file_path.endswith('.kmz') or buildings_file_path.endswith('.kml'):
        # يتطلب تفعيل دعم KML في fiona
        import fiona
        fiona.drvsupport.supported_drivers['KML'] = 'rw'
        fiona.drvsupport.supported_drivers['KMZ'] = 'rw'
        gdf_buildings = gpd.read_file(buildings_file_path, driver='KMZ' if buildings_file_path.endswith('.kmz') else 'KML')
    else:
        gdf_buildings = gpd.read_file(buildings_file_path)

    # 5. تحويل إحداثيات مباني الأنسنة إلى EPSG:4326 إذا كان النظام مختلفاً
    if gdf_buildings.crs and gdf_buildings.crs != "EPSG:4326":
        print(f"Converting buildings CRS from {gdf_buildings.crs} to EPSG:4326...")
        gdf_buildings = gdf_buildings.to_crs("EPSG:4326")
    elif not gdf_buildings.crs:
        gdf_buildings.set_crs("EPSG:4326", inplace=True)
        
    print("Data processing completed successfully. CRS is set to EPSG:4326 for both datasets.")
    
    # حفظ النتائج (مثال)
    gdf_compliance.to_file(output_path, driver="GeoJSON")
    print(f"Saved processed compliance data to {output_path}")
    
    return gdf_compliance, gdf_buildings

if __name__ == "__main__":
    # أمثلة للاستخدام:
    # يرجى تعديل مسارات الملفات أدناه لتتطابق مع أسماء الملفات الفعلية لديك
    compliance_file = "certificates.csv" # أو .xlsx
    buildings_file = "buildings.kmz"     # أو .geojson
    
    if os.path.exists(compliance_file) and os.path.exists(buildings_file):
        process_compliance_data(compliance_file, buildings_file)
    else:
        print("الرجاء تعديل مسارات الملفات في الكود لتتطابق مع الملفات الموجودة في المجلد.")
