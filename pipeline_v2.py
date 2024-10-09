import os
import glob
import pandas as pd
from sklearn.neighbors import KNeighborsClassifier
import geopandas as gpd
import matplotlib.pyplot as plt
import folium

# Base directory where the borough datasets are stored
BASE_DIR = "borough_assets"
# List of boroughs that users can view/upload
AREA_DIRECTORIES = ['brooklyn', 'citywide', 'manhattan',
               'queens', 'staten_island', 'the_bronx']

DATA_DIRECTORIES = ['unprocessed_data', 'processed_data', 'heatmap']
# Path to the NYC shapefile for zip code boundaries
SHAPEFILE_PATH = "data/nyc_shapefile/nyc_zip_code_map.shp"

# Standardized column names
COLUMN_MAPPING = {
    'zip_code': 'Zip Code',
    'borough': 'Borough',
    'accident_count': 'Accident Count',
    'latitude': 'Latitude',
    'longitude': 'Longitude',
    'crash_count': 'Crash Count'
}

def get_latest_csv(borough: str) -> str:
    """
    Get the CSV file from the specified borough's directory.
    """
    borough_dir = os.path.join(BASE_DIR, borough, 'unprocessed_data')
    if not os.path.isdir(borough_dir):
        raise FileNotFoundError(f"The directory for '{borough}' does not exist.")

    csv_files = glob.glob(os.path.join(borough_dir, "*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV file found in the directory for '{borough}'.")

    return csv_files[0]


def load_accident_data(csv_filename):
    """
    Load the CSV file into a DataFrame and standardize column names.
    """
    df = pd.read_csv(csv_filename)
    df.rename(columns=COLUMN_MAPPING, inplace=True)
    return df


def filter_accidents(df):
    """
    Split the accidents DataFrame into five categories based on zip code and location data.
    """
    df_zip_lat_long = df.dropna(subset=[COLUMN_MAPPING['zip_code'], COLUMN_MAPPING['latitude'], COLUMN_MAPPING['longitude']])
    df_no_zip_lat_long = df[df[COLUMN_MAPPING['zip_code']].isna() & df[COLUMN_MAPPING['latitude']].notna() & df[COLUMN_MAPPING['longitude']].notna()]
    df_zip_no_lat_long = df[df[COLUMN_MAPPING['zip_code']].notna() & (df[COLUMN_MAPPING['latitude']].isna() | df[COLUMN_MAPPING['longitude']].isna())]
    df_no_zip_no_lat_long = df[df[COLUMN_MAPPING['zip_code']].isna() & (df[COLUMN_MAPPING['latitude']].isna() | df[COLUMN_MAPPING['longitude']].isna())]
    df_null_crash_count = df[df[COLUMN_MAPPING['crash_count']].isna()]

    return df_zip_lat_long, df_no_zip_lat_long, df_zip_no_lat_long, df_no_zip_no_lat_long, df_null_crash_count

def assign_zip_codes_knn(df_zip_lat_long, df_no_zip_lat_long, k=1):
    """
    Assign zip codes to accidents missing them using K-Nearest Neighbors (KNN).
    """
    X_with_zip = df_zip_lat_long[[COLUMN_MAPPING['latitude'], COLUMN_MAPPING['longitude']]]
    y_with_zip = df_zip_lat_long[COLUMN_MAPPING['zip_code']]

    X_without_zip = df_no_zip_lat_long[[COLUMN_MAPPING['latitude'], COLUMN_MAPPING['longitude']]]

    knn = KNeighborsClassifier(n_neighbors=k)
    knn.fit(X_with_zip, y_with_zip)

    predicted_zip_codes = knn.predict(X_without_zip)
    
    # Use .loc to avoid setting values on a copy of a slice
    df_no_zip_lat_long.loc[:, COLUMN_MAPPING['zip_code']] = predicted_zip_codes

    return df_no_zip_lat_long



def create_combined_dataframe(df_zip_lat_long, knn_crashlist, df_zip_no_lat_long):
    """
    Combine the accident DataFrames with known and predicted zip codes.
    """
    return pd.concat([df_zip_lat_long, knn_crashlist, df_zip_no_lat_long], ignore_index=True)


def group_and_rank_accidents(combined_df):
    """
    Group accidents by zip code and borough, calculate accident counts, and assign ranks and deciles.
    """
    grouped_df = combined_df.groupby([COLUMN_MAPPING['zip_code'], COLUMN_MAPPING['borough']]).size().reset_index(name=COLUMN_MAPPING['accident_count'] )

    grouped_df = grouped_df.sort_values(by=COLUMN_MAPPING['accident_count'], ascending=False)
    grouped_df['Rank'] = grouped_df[COLUMN_MAPPING['accident_count']].rank(method='first', ascending=False).astype(int)

    grouped_df['Decile'] = pd.qcut(grouped_df['Rank'], 10, labels=False) + 1
    grouped_df['Decile'] = 11 - grouped_df['Decile']

    return grouped_df[['Rank', 'Decile', COLUMN_MAPPING['zip_code'], COLUMN_MAPPING['borough'], COLUMN_MAPPING['accident_count']]]

def save_master_table(df, borough, file_path):
    """
    Save the master table DataFrame to a CSV file.
    """
    df.to_csv(os.path.join(file_path, f"{borough}_master_table.csv"), index=False)

def validate_borough_zip_codes(borough_df, citywide_df, borough):
    """
    Cross-reference the borough dataset with the citywide dataset to ensure zip codes belong to the correct borough.

    Parameters:
    - borough_df (DataFrame): DataFrame for the selected borough.
    - citywide_df (DataFrame): Citywide DataFrame with zip code and borough information.
    - borough (str): The name of the borough to validate.

    Returns:
    - DataFrame: The validated borough DataFrame with incorrect zip codes removed.
    """
    # Ensure that both dataframes have the same column names for comparison
    borough_df[COLUMN_MAPPING['borough']] = borough_df[COLUMN_MAPPING['borough']].str.lower()
    citywide_df[COLUMN_MAPPING['borough']] = citywide_df[COLUMN_MAPPING['borough']].str.lower()

    # Filter citywide data to only include zip codes assigned to the selected borough
    valid_zip_codes = citywide_df[citywide_df[COLUMN_MAPPING['borough']] == borough.lower()][COLUMN_MAPPING['zip_code']]

    # Filter the borough_df to only include rows where the zip code is valid for the selected borough
    validated_borough_df = borough_df[borough_df[COLUMN_MAPPING['zip_code']].isin(valid_zip_codes)]

    # Optionally, print how many invalid zip codes were found and removed
    removed_count = len(borough_df) - len(validated_borough_df)
    if removed_count > 0:
        print(f"Removed {removed_count} incorrect zip codes from the {borough} dataset.")

    return validated_borough_df


# def main(borough: str, k: int):
#     """
#     Main function to execute the accident data processing pipeline.
#     """
#     file_name = get_latest_csv(borough)
#     df = load_accident_data(file_name)

#     df_zip_lat_long, df_no_zip_lat_long, df_zip_no_lat_long, df_no_zip_no_lat_long, df_null_crash_count = filter_accidents(df)

#     knn_crashlist = assign_zip_codes_knn(df_zip_lat_long, df_no_zip_lat_long, k=k)
#     combined_df = create_combined_dataframe(df_zip_lat_long, knn_crashlist, df_zip_no_lat_long)

#     grouped_accidents_df = group_and_rank_accidents(combined_df)

#     average_accidents_per_zip = grouped_accidents_df[COLUMN_MAPPING['accident_count']].mean()

#     return len(df), grouped_accidents_df, round(average_accidents_per_zip, 2)

def main(borough: str, k: int):
    """
    Main function to execute the accident data processing pipeline.
    """
    # Load the latest borough data
    file_name = get_latest_csv(borough)
    df = load_accident_data(file_name)

    # Load citywide data for cross-referencing
    citywide_file_name = get_latest_csv('citywide')
    citywide_df = load_accident_data(citywide_file_name)

    # Filter the data into the necessary categories
    df_zip_lat_long, df_no_zip_lat_long, df_zip_no_lat_long, df_no_zip_no_lat_long, df_null_crash_count = filter_accidents(df)

    # Assign zip codes to accidents without zip codes using KNN
    knn_crashlist = assign_zip_codes_knn(df_zip_lat_long, df_no_zip_lat_long, k=k)

    # Combine the datasets
    combined_df = create_combined_dataframe(df_zip_lat_long, knn_crashlist, df_zip_no_lat_long)

    # Validate zip codes for the borough by cross-referencing with citywide data
    # validated_combined_df = validate_borough_zip_codes(combined_df, citywide_df, borough)

    # Group accidents by zip code and borough, calculate accident counts, assign ranks and deciles
    grouped_accidents_df = group_and_rank_accidents(combined_df)

    # Calculate the average number of accidents per zip code
    average_accidents_per_zip = grouped_accidents_df[COLUMN_MAPPING['accident_count']].mean()

    return len(df), grouped_accidents_df, round(average_accidents_per_zip, 2)

# def create_heatmap(borough: str, decile_table, shapefile_path=SHAPEFILE_PATH):
#     """
#     Create a heatmap for the selected borough or citywide using the decile table and NYC's shapefile.
#     """
#     try:
#         nyc_gdf = gpd.read_file(shapefile_path)
#         nyc_gdf['ZIPCODE'] = nyc_gdf['modzcta'].astype(str).str.strip()

#         decile_table[COLUMN_MAPPING['zip_code']] = decile_table[COLUMN_MAPPING['zip_code']].apply(lambda x: str(int(x)).zfill(5)).str.strip()

#         if borough.lower() != "citywide":
#             decile_table = decile_table[decile_table[COLUMN_MAPPING['borough']].str.lower() == borough.lower()]
#             zip_codes_in_borough = decile_table[COLUMN_MAPPING['zip_code']].unique()
#             nyc_gdf = nyc_gdf[nyc_gdf['ZIPCODE'].isin(zip_codes_in_borough)]

#         merged_gdf = nyc_gdf.merge(decile_table, left_on='ZIPCODE', right_on=COLUMN_MAPPING['zip_code'], how='left')

#         if merged_gdf.empty:
#             print("No matching zip codes found between the shapefile and decile table.")
#             return

#         fig, ax = plt.subplots(1, 1, figsize=(12, 12))
#         merged_gdf.plot(column='Decile', cmap='OrRd_r', linewidth=0.8, ax=ax, edgecolor='0.8', missing_kwds={'color': 'lightgrey'})

#         if borough.lower() != "citywide":
#             minx, miny, maxx, maxy = merged_gdf.total_bounds
#             ax.set_xlim(minx, maxx)
#             ax.set_ylim(miny, maxy)

#         title = 'NYC Accident Heatmap by Zip Code - ' + ('Citywide' if borough.lower() == 'citywide' else borough.capitalize())
#         ax.set_title(title, fontsize=16)
#         ax.axis('off')

#         plt.show()

#     except Exception as e:
#         print(f"An error occurred in create_heatmap: {e}")

def create_heatmap(borough: str, grouped_accidents_df: pd.DataFrame, shapefile_path=SHAPEFILE_PATH):
    """
    Create a heatmap for the selected borough or citywide using the decile data and NYC's shapefile.

    Parameters:
    - borough (str): The borough or "citywide" to create a heatmap for.
    - grouped_accidents_df (DataFrame): DataFrame containing the accident data, including zip code, decile, and accident count.
    - shapefile_path (str): Path to the shapefile of NYC zip code boundaries.

    Returns:
    - None: Displays the heatmap plot.
    """
    try:
        # Load the NYC shapefile into a GeoDataFrame
        nyc_gdf = gpd.read_file(shapefile_path)

        # Ensure the 'modzcta' (zip code in shapefile) is in string format and strip spaces
        nyc_gdf['ZIPCODE'] = nyc_gdf['modzcta'].astype(str).str.strip()

        # Ensure the zip codes in the grouped_accidents_df are in string format and match 5-digit formatting
        grouped_accidents_df[COLUMN_MAPPING['zip_code']] = grouped_accidents_df[COLUMN_MAPPING['zip_code']].apply(lambda x: str(int(x)).zfill(5))

        # If a specific borough is selected, filter the accidents data and shapefile for that borough
        if borough.lower() != "citywide":
            grouped_accidents_df = grouped_accidents_df[grouped_accidents_df[COLUMN_MAPPING['borough']].str.lower() == borough.lower()]
            zip_codes_in_borough = grouped_accidents_df[COLUMN_MAPPING['zip_code']].unique()
            nyc_gdf = nyc_gdf[nyc_gdf['ZIPCODE'].isin(zip_codes_in_borough)]

        # Merge the GeoDataFrame with the grouped accidents DataFrame on the zip code
        merged_gdf = nyc_gdf.merge(grouped_accidents_df, left_on='ZIPCODE', right_on=COLUMN_MAPPING['zip_code'], how='left')

        # Check if merged_gdf is empty
        if merged_gdf.empty:
            print("No matching zip codes found between the shapefile and accident data.")
            return

        # Plot the heatmap using the 'Decile' values, using 'OrRd_r' to have the darkest color for decile 10
        fig, ax = plt.subplots(1, 1, figsize=(12, 12))
        merged_gdf.plot(column='Decile', cmap='OrRd', linewidth=0.8, ax=ax, edgecolor='0.8', legend=True, missing_kwds={'color': 'lightgrey'})

        # Set the plot limits to focus on the selected borough's bounding box
        if borough.lower() != "citywide":
            minx, miny, maxx, maxy = merged_gdf.total_bounds
            ax.set_xlim(minx, maxx)
            ax.set_ylim(miny, maxy)

        # Set plot title based on the selected borough
        title = 'NYC Accident Heatmap by Zip Code - ' + ('Citywide' if borough.lower() == 'citywide' else borough.capitalize())
        ax.set_title(title, fontsize=16)
        ax.axis('off')  # Turn off the axis for better visualization

        # Show the plot
        plt.show()

    except Exception as e:
        print(f"An error occurred in create_heatmap: {e}")

# def create_interactive_heatmap(borough: str, decile_table, shapefile_path=SHAPEFILE_PATH):
#     """
#     Create an interactive heatmap for the selected borough or citywide using the decile table and NYC's shapefile.

#     Parameters:
#     - borough (str): The borough or "citywide" to create a heatmap for.
#     - decile_table (DataFrame): DataFrame containing the decile, zip codes, accident counts, and other information.
#     - shapefile_path (str): Path to the shapefile of NYC zip code boundaries.

#     Returns:
#     - folium.Map: A Folium map object with the interactive heatmap.
#     """
#     try:
#         # Load the NYC shapefile into a GeoDataFrame
#         nyc_gdf = gpd.read_file(shapefile_path)

#         # Ensure the 'modzcta' column (zip code) is in string format and strip spaces
#         nyc_gdf['ZIPCODE'] = nyc_gdf['modzcta'].astype(str).str.strip()

#         # Convert 'Zip Code' in the decile_table to string, ensure 5-digit format, and strip spaces
#         decile_table['Zip Code'] = decile_table['Zip Code'].apply(
#             lambda x: str(int(x)).zfill(5)).str.strip()

#         # If a specific borough is selected, filter the decile table and shapefile for that borough
#         if borough.lower() != "citywide":
#             decile_table = decile_table[decile_table['Borough'].str.lower(
#             ) == borough.lower()]
#             # Get the list of zip codes in the selected borough
#             zip_codes_in_borough = decile_table['Zip Code'].unique()
#             # Filter the shapefile for only those zip codes
#             nyc_gdf = nyc_gdf[nyc_gdf['ZIPCODE'].isin(zip_codes_in_borough)]

#         # Merge the GeoDataFrame with the decile table on the zip code
#         merged_gdf = nyc_gdf.merge(
#             decile_table, left_on='ZIPCODE', right_on='Zip Code', how='left')

#         # Check if merged_gdf is empty
#         if merged_gdf.empty:
#             print("No matching zip codes found between the shapefile and decile table.")
#             return

#         # Initialize a Folium map centered around NYC
#         m = folium.Map(location=[40.7128, -74.0060], zoom_start=11)

#         # Add zip code polygons to the map
#         folium.Choropleth(
#             geo_data=merged_gdf,
#             name='choropleth',
#             data=merged_gdf,
#             columns=['ZIPCODE', 'Decile'],
#             key_on='feature.properties.ZIPCODE',
#             fill_color='OrRd',
#             fill_opacity=0.7,
#             line_opacity=0.2,
#             legend_name='Accident Decile'
#         ).add_to(m)

#         # Add tooltips with zip code and accident count
#         for _, row in merged_gdf.iterrows():
#             # Extract coordinates for the center of the polygon to place the tooltip
#             centroid = row['geometry'].centroid
#             zip_code = row['ZIPCODE']
#             accidents = row['Accident Count']
#             tooltip_text = f"Zip Code: {zip_code}<br>Accidents: {accidents}"

#             # Add a marker with a tooltip
#             folium.Marker(
#                 location=[centroid.y, centroid.x],
#                 icon=None,
#                 tooltip=tooltip_text
#             ).add_to(m)

#         # Return the map object
#         return m

#     except Exception as e:
#         print(f"An error occurred in create_interactive_heatmap: {e}")

def create_interactive_heatmap(borough: str, decile_table, shapefile_path=SHAPEFILE_PATH):
    """
    Create an interactive heatmap for the selected borough or citywide using the decile table and NYC's shapefile.

    Parameters:
    - borough (str): The borough or "citywide" to create a heatmap for.
    - decile_table (DataFrame): DataFrame containing the decile, zip codes, accident counts, and other information.
    - shapefile_path (str): Path to the shapefile of NYC zip code boundaries.

    Returns:
    - folium.Map: A Folium map object with the interactive heatmap.
    """
    try:
        # Load the NYC shapefile into a GeoDataFrame
        nyc_gdf = gpd.read_file(shapefile_path)

        # Ensure the 'modzcta' column (zip code) is in string format and strip spaces
        nyc_gdf['ZIPCODE'] = nyc_gdf['modzcta'].astype(str).str.strip()

        # Convert 'Zip Code' in the decile_table to string, ensure 5-digit format, and strip spaces
        decile_table['Zip Code'] = decile_table['Zip Code'].apply(
            lambda x: str(int(x)).zfill(5)).str.strip()

        # If a specific borough is selected, filter the decile table and shapefile for that borough
        if borough.lower() != "citywide":
            decile_table = decile_table[decile_table['Borough'].str.lower() == borough.lower()]
            # Get the list of zip codes in the selected borough
            zip_codes_in_borough = decile_table['Zip Code'].unique()
            # Filter the shapefile for only those zip codes
            nyc_gdf = nyc_gdf[nyc_gdf['ZIPCODE'].isin(zip_codes_in_borough)]

        # Merge the GeoDataFrame with the decile table on the zip code
        merged_gdf = nyc_gdf.merge(
            decile_table, left_on='ZIPCODE', right_on='Zip Code', how='left')

        # Check if merged_gdf is empty
        if merged_gdf.empty:
            print("No matching zip codes found between the shapefile and decile table.")
            return

        # Initialize a Folium map centered around NYC
        m = folium.Map(location=[40.7128, -74.0060], zoom_start=11)

        # Define bins for the deciles from 1 to 10
        bins = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        # Add zip code polygons to the map with a fixed decile scale
        folium.Choropleth(
            geo_data=merged_gdf,
            name='choropleth',
            data=merged_gdf,
            columns=['ZIPCODE', 'Decile'],
            key_on='feature.properties.ZIPCODE',
            fill_color='OrRd',
            fill_opacity=0.7,
            line_opacity=0.2,
            legend_name='Accident Decile',
            bins=bins,  # Define explicit bins to cover the full decile range
            reset=True
        ).add_to(m)

        # Add tooltips with zip code and accident count
        for _, row in merged_gdf.iterrows():
            # Extract coordinates for the center of the polygon to place the tooltip
            centroid = row['geometry'].centroid
            zip_code = row['ZIPCODE']
            accidents = row['Accident Count']
            tooltip_text = f"Zip Code: {zip_code}<br>Accidents: {accidents}"

            # Add a marker with a tooltip
            folium.Marker(
                location=[centroid.y, centroid.x],
                icon=None,
                tooltip=tooltip_text
            ).add_to(m)

        # Return the map object
        return m

    except Exception as e:
        print(f"An error occurred in create_interactive_heatmap: {e}")


borough = "staten_island"
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
total_accidents, all_accidents, avg_accidents_per_zip_code = main(borough, 3)
print(all_accidents)
heatmap = create_interactive_heatmap("Staten Island", all_accidents)
heatmap.save('interactive_heatmap.html')