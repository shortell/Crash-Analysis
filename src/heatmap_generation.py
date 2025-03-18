import geopandas as gpd
import folium

SHAPEFILE_PATH = "data/nyc_shapefile/nyc_zip_code_map.shp"


def create_interactive_heatmap(borough: str, decile_table, shapefile_path=SHAPEFILE_PATH):
    """
    Create an interactive heatmap for the selected borough or citywide using the decile table and NYC's shapefile.
    """
    try:
        nyc_gdf = gpd.read_file(shapefile_path)
        nyc_gdf['ZIPCODE'] = nyc_gdf['modzcta'].astype(str).str.strip()

        decile_table['Zip Code'] = decile_table['Zip Code'].apply(
            lambda x: str(int(x)).zfill(5)).str.strip()

        if borough != "Citywide":
            decile_table = decile_table[decile_table['Borough'] == borough]
            zip_codes_in_borough = decile_table['Zip Code'].unique()
            nyc_gdf = nyc_gdf[nyc_gdf['ZIPCODE'].isin(zip_codes_in_borough)]

        merged_gdf = nyc_gdf.merge(
            decile_table, left_on='ZIPCODE', right_on='Zip Code', how='left')

        if merged_gdf.empty:
            print("No matching zip codes found between the shapefile and decile table.")
            return

        m = folium.Map(location=[40.7128, -74.0060], zoom_start=11)

        bins = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        folium.Choropleth(
            geo_data=merged_gdf,
            name='choropleth',
            data=merged_gdf,
            columns=['ZIPCODE', 'Decile'],
            key_on='feature.properties.ZIPCODE',
            fill_color='OrRd_r',
            fill_opacity=0.7,
            line_opacity=0.2,
            legend_name='Accident Decile',
            bins=bins,
            reset=True
        ).add_to(m)

        for _, row in merged_gdf.iterrows():
            centroid = row['geometry'].centroid
            zip_code = row['ZIPCODE']
            accidents = row['Accident Count']
            decile = row['Decile']
            rank = row['Rank']
            tooltip_text = f"Zip Code: {zip_code}<br>Accidents: {accidents}<br>Decile: {decile}<br>Rank: {rank}"

            folium.Marker(
                location=[centroid.y, centroid.x],
                icon=None,
                tooltip=tooltip_text
            ).add_to(m)
        print("Interactive heatmap created.")
        return m

    except Exception as e:
        print(f"An error occurred in create_interactive_heatmap: {e}")
        return None
    


