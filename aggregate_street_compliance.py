import geopandas as gpd
import pandas as pd
import json

def process_street_compliance():
    input_file = "Final_Buildings_Compliance.geojson"
    output_excel = "Street_Compliance_Summary.xlsx"

    print(f"Loading {input_file}...")
    try:
        # Load safely just in case of any date issues, although it shouldn't be an issue for the final file
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        gdf = gpd.GeoDataFrame.from_features(data.get('features', []))
    except Exception as e:
        print(f"Error reading {input_file}: {e}")
        return

    # 1. Cleaning and standardizing Street Names
    # In ComBulid, the primary name field is 'Name', and from points it might be 'الشارع'
    street_col = 'Name'
    
    if street_col not in gdf.columns:
        if 'الشارع' in gdf.columns:
            street_col = 'الشارع'
        else:
            print(f"Error: Neither 'Name' nor 'الشارع' found in the dataset.")
            print("Available columns:", gdf.columns.tolist())
            return

    print("Cleaning street names...")
    # Convert to string, replace Nan/None/NULL
    gdf[street_col] = gdf[street_col].astype(str).replace(['nan', 'None', 'NULL', 'null', '<Null>'], 'غير محدد')
    
    # Strip leading/trailing whitespaces, replace multiple spaces with single space
    gdf[street_col] = gdf[street_col].str.strip()
    gdf[street_col] = gdf[street_col].str.replace(r'\s+', ' ', regex=True)
    
    # Optional: You can add specific string replacements if 'طريق الملك عبد العزيز' exists in multiple forms
    # Example: gdf[street_col] = gdf[street_col].str.replace('عبدالعزيز', 'عبد العزيز')
    
    # 2. Aggregation (Group By)
    print("Aggregating compliance by street name...")
    
    # Create the grouped dataframe
    summary_df = gdf.groupby(street_col).agg(
        Count_All=('Compliance_Status', 'size'),
        Count_Compliant=('Compliance_Status', lambda x: (x == 'ممتثل').sum()),
        Count_Non_Compliant=('Compliance_Status', lambda x: (x == 'غير ممتثل').sum())
    ).reset_index()

    # 3. Calculate Compliance Ratio (KPI)
    print("Calculating Compliance Ratio (KPI)...")
    summary_df['Compliance_Ratio (%)'] = ((summary_df['Count_Compliant'] / summary_df['Count_All']) * 100).round(1)

    # Sort by Compliance Ratio ascending (Least compliant first)
    summary_df = summary_df.sort_values('Compliance_Ratio (%)', ascending=True)

    print(f"\n--- Street Compliance Summary ---")
    print(summary_df.head(10).to_string(index=False)) # print top 10
    print(f"---------------------------------\n")

    print(f"Saving summary to {output_excel}...")
    try:
        summary_df.to_excel(output_excel, index=False)
        print(f"Saved {output_excel} successfully!")
    except ImportError:
        print("Error: 'openpyxl' library not installed. Cannot save to Excel. Saving to CSV instead.")
        output_csv = "Street_Compliance_Summary.csv"
        summary_df.to_csv(output_csv, index=False, encoding='utf-8-sig')
        print(f"Saved to {output_csv} successfully!")


if __name__ == "__main__":
    process_street_compliance()
