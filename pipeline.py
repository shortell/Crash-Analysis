import os
import glob
import pandas as pd
from sklearn.neighbors import KNeighborsClassifier
import geopandas as gpd
import matplotlib.pyplot as plt
import folium

# Base directory where the borough datasets are stored
BASE_DIR = "data/nyc_csv/"
# List of boroughs that users can view/upload
DIRECTORIES = ['brooklyn', 'citywide', 'manhattan',
               'queens', 'staten_island', 'the_bronx']

SHAPEFILE_PATH = "data/nyc_shapefile/nyc_zip_code_map.shp"


def get_latest_csv(borough: str) -> str:
    """
    Get the CSV file from the specified borough's directory.

    Parameters:
    - borough (str): The borough or "citywide" to search for the CSV file.

    Returns:
    - csv_file (str): The path to the CSV file.
    """

    # Construct the full directory path based on the borough
    borough_dir = os.path.join(BASE_DIR, borough)

    # Check if the directory exists
    if not os.path.isdir(borough_dir):
        raise FileNotFoundError(f"The directory for '{
                                borough}' does not exist.")

    # Search for the CSV file in the directory
    csv_files = glob.glob(os.path.join(borough_dir, "*.csv"))

    # Check if any CSV file was found
    if not csv_files:
        raise FileNotFoundError(
            f"No CSV file found in the directory for '{borough}'.")

    # Since there will only be one file, grab the first one
    csv_file = csv_files[0]

    return csv_file


def split_accidents(csv_filename):
    # Load the CSV file into a pandas DataFrame
    df = pd.read_csv(csv_filename)

    # Filter dataframes based on the conditions
    # 1. Accidents with a zip code & latitude and longitude coordinates
    df_zip_lat_long = df.dropna(subset=['zip_code', 'latitude', 'longitude'])

    # 2. Accidents with no zip code, but have latitude and longitude coordinates
    df_no_zip_lat_long = df[df['zip_code'].isna(
    ) & df['latitude'].notna() & df['longitude'].notna()]

    # 3. Accidents with a zip code, but no latitude and longitude coordinates
    df_zip_no_lat_long = df[df['zip_code'].notna() & (
        df['latitude'].isna() | df['longitude'].isna())]

    # 4. Accidents with no zip code, and no latitude and longitude coordinates
    df_no_zip_no_lat_long = df[df['zip_code'].isna() & (
        df['latitude'].isna() | df['longitude'].isna())]

    # 5. Accidents with a null crash count
    df_null_crash_count = df[df['crash_count'].isna()]

    # Return the filtered dataframes and the total number of records
    total_records = len(df)

    return df_zip_lat_long, df_no_zip_lat_long, df_zip_no_lat_long, df_no_zip_no_lat_long, df_null_crash_count, total_records


def assign_zip_codes_knn(df_zip_lat_long, df_no_zip_lat_long, k=1):
    """
    Assign zip codes to accidents missing them using K-Nearest Neighbors (KNN).

    Parameters:
    - df_zip_lat_long (DataFrame): DataFrame containing accidents with valid zip codes.
    - df_no_zip_lat_long (DataFrame): DataFrame containing accidents with no zip codes but with latitude and longitude.
    - k (int): Number of neighbors to consider for KNN. Default is 1.

    Returns:
    - knn_crashlist (DataFrame): DataFrame of accidents with assigned zip codes from KNN.
    """
    try:
        # Ensure the necessary latitude and longitude columns are present
        if 'latitude' not in df_zip_lat_long.columns or 'longitude' not in df_zip_lat_long.columns:
            raise ValueError(
                "df_zip_lat_long must contain 'latitude' and 'longitude' columns")
        if 'latitude' not in df_no_zip_lat_long.columns or 'longitude' not in df_no_zip_lat_long.columns:
            raise ValueError(
                "df_no_zip_lat_long must contain 'latitude' and 'longitude' columns")

        # Extract features (latitude and longitude) and target (zip_code) from the df_zip_lat_long DataFrame
        X_with_zip = df_zip_lat_long[['latitude', 'longitude']]
        y_with_zip = df_zip_lat_long['zip_code']  # Target (zip codes)

        # Extract features (latitude and longitude) from the df_no_zip_lat_long DataFrame
        X_without_zip = df_no_zip_lat_long[['latitude', 'longitude']]

        # Initialize the KNeighborsClassifier with k neighbors
        knn = KNeighborsClassifier(n_neighbors=k)

        # Fit the model using the accidents with zip codes
        knn.fit(X_with_zip, y_with_zip)

        # Predict zip codes for accidents without zip codes
        predicted_zip_codes = knn.predict(X_without_zip)

        # Assign the predicted zip codes to the df_no_zip_lat_long DataFrame
        df_no_zip_lat_long['zip_code'] = predicted_zip_codes

        # Return the updated DataFrame (knn_crashlist) with assigned zip codes
        return df_no_zip_lat_long
    except Exception as e:
        print(f"An error occurred in assign_zip_codes_knn: {e}")
        return None


def create_master_accidents_df(knn_crashlist, df_zip_lat_long, df_zip_no_lat_long):
    """
    Create a master dataframe that combines all accidents, grouped by zipcode and borough,
    and calculates the accident count with rankings, along with a decile column based on rank.

    Parameters:
    - knn_crashlist (DataFrame): DataFrame with assigned zip codes from KNN.
    - df_zip_lat_long (DataFrame): DataFrame containing accidents with zip codes and coordinates.
    - df_zip_no_lat_long (DataFrame): DataFrame containing accidents with zip codes but missing coordinates.

    Returns:
    - master_df (DataFrame): A master DataFrame with rank, decile, zip code, borough, and accident count per zip code.
    """
    try:
        # Concatenate the three DataFrames: df_zip_lat_long, knn_crashlist, and df_zip_no_lat_long
        combined_df = pd.concat(
            [df_zip_lat_long, knn_crashlist, df_zip_no_lat_long], ignore_index=True)

        # Group by 'zip_code' and 'borough', and calculate the number of accidents (accident count)
        grouped_df = combined_df.groupby(
            ['zip_code', 'borough']).size().reset_index(name='accident_count')

        # Sort the grouped DataFrame by accident count in descending order
        grouped_df = grouped_df.sort_values(
            by='accident_count', ascending=False)

        # Add a 'rank' column based on the accident count
        grouped_df['rank'] = grouped_df['accident_count'].rank(
            method='first', ascending=False).astype(int)

        # Add a 'decile' column based on the rank, where decile 10 gets the highest accident counts
        grouped_df['decile'] = pd.qcut(
            grouped_df['rank'], 10, labels=False) + 1

        # Reverse the decile so that the highest ranks (smallest numbers) are in decile 1
        grouped_df['decile'] = 11 - grouped_df['decile']

        # Reorder the columns to place 'decile' between 'rank' and 'zip_code'
        master_df = grouped_df[['rank', 'decile',
                                'zip_code', 'borough', 'accident_count']]

        return master_df

    except Exception as e:
        print(f"An error occurred in create_master_accidents_df: {e}")
        return None


def analyze_accidents(master_df):
    """
    Analyze the master_df to calculate the average number of accidents per zip code
    and add a decile column that breaks zip codes into 10 groups based on accident count.

    Parameters:
    - master_df (DataFrame): The master DataFrame containing rank, zip code, borough, and accident count.

    Returns:
    - master_df (DataFrame): Updated DataFrame with the average accident count and decile group for each zip code.
    - avg_accidents_per_zip (float): The average number of accidents per zip code.
    """
    try:
        # Calculate the average number of accidents per zip code
        avg_accidents_per_zip = master_df['accident_count'].mean()

        # Add a 'decile' column to group zip codes into 10 groups based on accident count
        master_df['decile'] = pd.qcut(
            master_df['accident_count'], 10, labels=False) + 1

        return master_df, avg_accidents_per_zip

    except Exception as e:
        print(f"An error occurred in analyze_accidents: {e}")
        return None, None


def count_accidents_per_zipcode(all_accidents):
    try:
        # Count the number of accidents per zip code, including the borough information
        accidents_per_zipcode = all_accidents.groupby(
            ['zip_code', 'borough']).size().reset_index(name='accident_count')

        # Calculate the average number of accidents per zip code
        average_accidents_per_zip = accidents_per_zipcode['accident_count'].mean(
        )

        return accidents_per_zipcode[['zip_code', 'borough', 'accident_count']], round(average_accidents_per_zip, 2)
    except Exception as e:
        print(f"An error occurred in count accidents per zipcode: {e}")
        return None, None


def main(borough: str, k: int):
    """
    Main function to execute the accident data processing pipeline.

    Parameters:
    - borough (str): The borough or "citywide" for which to process the data.
    - k (int): Number of neighbors to use for KNN when assigning missing zip codes.

    Returns:
    - total_accidents (int): The total number of accidents in the dataset.
    - average_accidents_per_zip (float): The average number of accidents per zip code.
    - decile_table_sorted (DataFrame): A DataFrame containing 'Decile', 'Zip Code', 'Accident Count', 'Multiplier'.
    """

    pd.set_option('display.max_rows', None)  # Show all rows
    pd.set_option('display.max_columns', None)  # Show all columns
    pd.set_option('display.expand_frame_repr', False)  # Prevent line wrapping
    # Fetch the latest CSV file for the specified borough
    file_name = get_latest_csv(borough)

    # Split the accidents into those with and without zip codes
    df_zip_lat_long, df_no_zip_lat_long, df_zip_no_lat_long, df_no_zip_no_lat_long, df_null_crash_count, total_accidents = split_accidents(
        file_name)

    # Assign zip codes to accidents without zip codes
    knn_crashlist = assign_zip_codes_knn(
        df_zip_lat_long, df_no_zip_lat_long, k=k)

    all_accidents = create_master_accidents_df(
        knn_crashlist, df_zip_lat_long, df_zip_no_lat_long)

    # Count accidents per zip code and calculate the average
    # accidents_per_zipcode, average_accidents_per_zip = count_accidents_per_zipcode(
    #     all_accidents)

    # Calculate total number of accidents
    # total_accidents = all_accidents.shape[0]

    # Split zip codes into deciles based on accidents
    # decile_table = split_zip_codes_into_deciles(
    #     accidents_per_zipcode, average_accidents_per_zip)

    # Sort the decile table by Accident Count in descending order
    all_accidents = all_accidents.sort_values(
        by='accident_count', ascending=False).reset_index(drop=True)

    # Calculate the average number of accidents per zip code
    average_accidents_per_zip = all_accidents['accident_count'].mean(
    )

    return total_accidents, all_accidents, round(average_accidents_per_zip, 2)


def create_heatmap(borough: str, decile_table, shapefile_path=SHAPEFILE_PATH):
    """
    Create a heatmap for the selected borough or citywide using the decile table and NYC's shapefile.

    Parameters:
    - borough (str): The borough or "citywide" to create a heatmap for.
    - decile_table (DataFrame): DataFrame containing the decile, zip codes, accident counts, and other information.
    - shapefile_path (str): Path to the shapefile of NYC zip code boundaries.

    Returns:
    - None: Displays the heatmap plot.
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
            decile_table = decile_table[decile_table['Borough'].str.lower(
            ) == borough.lower()]
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

        # Plot the heatmap using the decile values, using 'OrRd_r' to have the darkest color for decile 10
        fig, ax = plt.subplots(1, 1, figsize=(12, 12))
        merged_gdf.plot(column='Decile', cmap='OrRd_r', linewidth=0.8,
                        ax=ax, edgecolor='0.8', missing_kwds={'color': 'lightgrey'})

        # Set the plot limits to focus on the selected borough's bounding box
        if borough.lower() != "citywide":
            minx, miny, maxx, maxy = merged_gdf.total_bounds
            ax.set_xlim(minx, maxx)
            ax.set_ylim(miny, maxy)

        # Set plot title based on the selected borough
        title = 'NYC Accident Heatmap by Zip Code - ' + \
            ('Citywide' if borough.lower() == 'citywide' else borough.capitalize())
        ax.set_title(title, fontsize=16)
        ax.axis('off')  # Turn off the axis for better visualization

        # Show the plot
        plt.show()

    except Exception as e:
        print(f"An error occurred in create_heatmap: {e}")


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
            decile_table = decile_table[decile_table['Borough'].str.lower(
            ) == borough.lower()]
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

        # Add zip code polygons to the map
        folium.Choropleth(
            geo_data=merged_gdf,
            name='choropleth',
            data=merged_gdf,
            columns=['ZIPCODE', 'Decile'],
            key_on='feature.properties.ZIPCODE',
            fill_color='OrRd',
            fill_opacity=0.7,
            line_opacity=0.2,
            legend_name='Accident Decile'
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

pd.set_option('display.max_rows', None)  # Show all rows
pd.set_option('display.max_columns', None)  # Show all columns
pd.set_option('display.expand_frame_repr', False)  # Prevent line wrapping
for area in DIRECTORIES:
    total_accidents, all_accidents, average_accidents_per_zip = main(area, 3)
    print(f"Total accidents in {area}: {total_accidents}")
    print(f"Average accidents per zip code in {area}: {average_accidents_per_zip}")
    print(all_accidents)
    print("\n")
    print("=" * 50)
    print("\n")



def combine_csv_files(file1: str, file2: str, new_file: str) -> None:
    """
    Combines two CSV files into one.

    Args:
        file1 (str): Path to the first CSV file.
        file2 (str): Path to the second CSV file.
        new_file (str): Path where the combined CSV file will be saved.

    Returns:
        None
    """
    try:
        # Read the CSV files
        df1 = pd.read_csv(file1)
        df2 = pd.read_csv(file2)

        # Combine the DataFrames
        combined_df = pd.concat([df1, df2], ignore_index=True)

        # Save the combined DataFrame to a new CSV file
        combined_df.to_csv(new_file, index=False)

        print(f"Combined CSV file saved as: {new_file}")

    except Exception as e:
        print(f"An error occurred: {e}")
