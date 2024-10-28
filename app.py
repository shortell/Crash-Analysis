from flask import Flask, render_template, request, redirect, url_for, flash
import os
import glob
from threading import Timer
import webbrowser
import os
import glob
import pandas as pd
from sklearn.neighbors import KNeighborsClassifier
import geopandas as gpd
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

BOROUGH_MAPPING = {
    'brooklyn': 'Brooklyn',
    'manhattan': 'Manhattan',
    'queens': 'Queens',
    'staten_island': 'Staten Island',
    'the_bronx': 'Bronx',
    'citywide': 'Citywide'
}


def get_latest_csv(borough: str) -> str:
    """
    Get the CSV file from the specified borough's unprocessed data directory.
    """
    borough_dir = os.path.join(BASE_DIR, borough, 'unprocessed_data')

    csv_files = glob.glob(os.path.join(borough_dir, "*.csv"))
    if not csv_files:
        raise FileNotFoundError(
            f"No CSV file found in the directory for '{borough}'.")

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
    df_zip_lat_long = df.dropna(subset=[
                                COLUMN_MAPPING['zip_code'], COLUMN_MAPPING['latitude'], COLUMN_MAPPING['longitude']])
    df_no_zip_lat_long = df[df[COLUMN_MAPPING['zip_code']].isna(
    ) & df[COLUMN_MAPPING['latitude']].notna() & df[COLUMN_MAPPING['longitude']].notna()]
    df_zip_no_lat_long = df[df[COLUMN_MAPPING['zip_code']].notna() & (
        df[COLUMN_MAPPING['latitude']].isna() | df[COLUMN_MAPPING['longitude']].isna())]
    df_no_zip_no_lat_long = df[df[COLUMN_MAPPING['zip_code']].isna() & (
        df[COLUMN_MAPPING['latitude']].isna() | df[COLUMN_MAPPING['longitude']].isna())]
    df_null_crash_count = df[df[COLUMN_MAPPING['crash_count']].isna()]

    return df_zip_lat_long, df_no_zip_lat_long, df_zip_no_lat_long, df_no_zip_no_lat_long, df_null_crash_count


def assign_zip_codes_knn(df_zip_lat_long, df_no_zip_lat_long, k=1):
    """
    Assign zip codes to accidents missing them using K-Nearest Neighbors (KNN).
    """
    X_with_zip = df_zip_lat_long[[
        COLUMN_MAPPING['latitude'], COLUMN_MAPPING['longitude']]]
    y_with_zip = df_zip_lat_long[COLUMN_MAPPING['zip_code']]

    X_without_zip = df_no_zip_lat_long[[
        COLUMN_MAPPING['latitude'], COLUMN_MAPPING['longitude']]]

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
    grouped_df = combined_df.groupby([COLUMN_MAPPING['zip_code'], COLUMN_MAPPING['borough']]).size(
    ).reset_index(name=COLUMN_MAPPING['accident_count'])

    grouped_df = grouped_df.sort_values(
        by=COLUMN_MAPPING['accident_count'], ascending=False)
    grouped_df['Rank'] = grouped_df[COLUMN_MAPPING['accident_count']].rank(
        method='first', ascending=False).astype(int)

    grouped_df['Decile'] = pd.qcut(grouped_df['Rank'], 10, labels=False) + 1
    grouped_df['Decile'] = 11 - grouped_df['Decile']

    return grouped_df[['Rank', 'Decile', COLUMN_MAPPING['zip_code'], COLUMN_MAPPING['borough'], COLUMN_MAPPING['accident_count']]]


def save_master_table(df, borough):
    """
    Save the master table DataFrame to a CSV file in the processed_data directory.
    """
    processed_dir = os.path.join(BASE_DIR, borough, 'processed_data')
    # Ensure the processed_data directory exists
    os.makedirs(processed_dir, exist_ok=True)
    df.to_csv(os.path.join(processed_dir, borough + "_master_table.csv"), index=False)


def load_master_table(borough):
    """
    Load the master table from the processed_data directory if it exists.
    """
    processed_dir = os.path.join(BASE_DIR, borough, 'processed_data')
    master_file = os.path.join(processed_dir, f"{borough}_master_table.csv")
    if os.path.exists(master_file):
        return pd.read_csv(master_file)
    return None


def validate_borough_zip_codes(borough_df, citywide_df, borough):
    """
    Cross-reference the borough dataset with the citywide dataset to ensure zip codes belong to the correct borough.
    """
    borough_df[COLUMN_MAPPING['borough']
               ] = borough_df[COLUMN_MAPPING['borough']].str.lower()
    citywide_df[COLUMN_MAPPING['borough']
                ] = citywide_df[COLUMN_MAPPING['borough']].str.lower()

    valid_zip_codes = citywide_df[citywide_df[COLUMN_MAPPING['borough']] == borough.lower(
    )][COLUMN_MAPPING['zip_code']]

    validated_borough_df = borough_df[borough_df[COLUMN_MAPPING['zip_code']].isin(
        valid_zip_codes)]

    return validated_borough_df


def create_interactive_heatmap(borough: str, decile_table, shapefile_path=SHAPEFILE_PATH):
    """
    Create an interactive heatmap for the selected borough or citywide using the decile table and NYC's shapefile.
    """
    try:
        nyc_gdf = gpd.read_file(shapefile_path)
        nyc_gdf['ZIPCODE'] = nyc_gdf['modzcta'].astype(str).str.strip()

        decile_table['Zip Code'] = decile_table['Zip Code'].apply(
            lambda x: str(int(x)).zfill(5)).str.strip()

        if borough.lower() != "citywide":
            decile_table = decile_table[decile_table['Borough'].str.lower(
            ) == borough.lower()]
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
            fill_color='OrRd',
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
            tooltip_text = f"Zip Code: {zip_code}<br>Accidents: {accidents}"

            folium.Marker(
                location=[centroid.y, centroid.x],
                icon=None,
                tooltip=tooltip_text
            ).add_to(m)

        return m

    except Exception as e:
        print(f"An error occurred in create_interactive_heatmap: {e}")


def save_heatmap(heatmap, borough):
    """
    Save the generated heatmap to the heatmap directory.
    """
    heatmap_dir = os.path.join('static', borough)
    os.makedirs(heatmap_dir, exist_ok=True)
    heatmap.save(os.path.join(heatmap_dir, 'interactive_heatmap.html'))


def main(borough: str, k: int):
    """
    Main function to execute the accident data processing pipeline or load precomputed data.
    Automatically generates and saves a heatmap if one does not exist.

    Returns:
    - total_accidents: Total number of accidents in the borough.
    - average_accidents_per_zip: The average number of accidents per zip code.
    - master_table: The final processed DataFrame containing accident data.
    """
    # Check if the master table already exists in processed_data
    master_table = load_master_table(borough)

    if master_table is not None:
        print(f"Loaded precomputed master table for {borough}.")
    else:
        # If no precomputed master table is found, process the data
        print(f"No precomputed master table found for {borough}. Starting pipeline...")

        file_name = get_latest_csv(borough)
        df = load_accident_data(file_name)

        # citywide_file_name = get_latest_csv('citywide')
        # citywide_df = load_accident_data(citywide_file_name)

        df_zip_lat_long, df_no_zip_lat_long, df_zip_no_lat_long, df_no_zip_no_lat_long, df_null_crash_count = filter_accidents(
            df)

        knn_crashlist = assign_zip_codes_knn(
            df_zip_lat_long, df_no_zip_lat_long, k=k)
        combined_df = create_combined_dataframe(
            df_zip_lat_long, knn_crashlist, df_zip_no_lat_long)

        master_table = group_and_rank_accidents(combined_df)

        print(f"Pipeline completed for {borough}.")
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        print(master_table)

        # Save the computed master table to processed_data
        save_master_table(master_table, borough)

    # Calculate total accidents and average accidents per zip code
    total_accidents = master_table['Accident Count'].sum()
    average_accidents_per_zip = master_table['Accident Count'].mean()

    # Generate and save the heatmap
    heatmap_dir = os.path.join(BASE_DIR, borough, 'heatmap')
    heatmap_file = os.path.join(heatmap_dir, 'interactive_heatmap.html')

    if os.path.exists(heatmap_file):
        print(f"Heatmap already exists for {borough}.")
    else:
        print(f"Generating heatmap for {borough}...")
        heatmap = create_interactive_heatmap(
            BOROUGH_MAPPING[borough], master_table)
        save_heatmap(heatmap, borough)
        print(f"Heatmap saved for {borough}.")

    # Return total accidents, average accidents per zip code, and the master table
    return total_accidents, round(average_accidents_per_zip, 2), master_table





app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Set the base directory where borough datasets are stored

# List of available borough directories
DIRECTORIES = ['brooklyn', 'citywide', 'manhattan',
               'queens', 'staten_island', 'the_bronx']

# Allowable file extensions for uploads
ALLOWED_EXTENSIONS = {'csv'}

K = 3  # Number of neighbors to check for accidents with no zip code

# Cache to store computed tables
cached_tables = {}


def allowed_file(filename):
    """
    Check if the uploaded file is allowed. 
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """ Display the available boroughs and datasets. """
    return render_template('index.html')


@app.route('/view/<area>')
def view_data(area):
    """
    Display the selected area (borough or citywide) and dataset.
    """
    # Check if the table for this area (borough or citywide) is already cached
    if area not in cached_tables:
        # Call main to compute the table if not cached
        total_accidents, average_accidents_per_zip, decile_table = main(
            area, k=K)

        # Cache the computed values
        cached_tables[area] = {
            'total_accidents': total_accidents,
            'average_accidents_per_zip': average_accidents_per_zip,
            'decile_table': decile_table
        }

    # Retrieve cached values
    cached_data = cached_tables[area]
    total_accidents = cached_data['total_accidents']
    average_accidents_per_zip = cached_data['average_accidents_per_zip']
    decile_table = cached_data['decile_table']

    # Get sort parameters from query string
    sort_by = request.args.get('sort_by', 'Accident Count')
    order = request.args.get('order', 'desc')  # Default to descending order

    ascending = True if order == 'asc' else False
    decile_table = decile_table.sort_values(by=sort_by, ascending=ascending)

    # Render the unified template
    return render_template(
        'view_area.html',
        area=area,
        total_accidents=total_accidents,
        average_accidents_per_zip=average_accidents_per_zip,
        decile_table=decile_table
    )

@app.route('/heatmap/<area>')
def view_heatmap(area):
    """
    Display the heatmap for the selected area (borough or citywide).
    """
    return render_template('view_map.html', area=area)

def delete_files(path_pattern):
    """Delete all files matching the given path pattern."""
    for filepath in glob.glob(path_pattern):
        try:
            os.remove(filepath)
        except Exception as e:
            print(f"Error deleting {filepath}: {e}")

@app.route('/upload/<area>', methods=['POST'])
def upload_csv(area):
    # Remove the cached table for the area, if it exists
    cached_tables.pop(area, None)

    # Delete all CSV files for the area in unprocessed_data and processed_data directories
    delete_files(f'borough_assets/{area}/unprocessed_data/*.csv')
    delete_files(f'borough_assets/{area}/processed_data/*.csv')

    # Delete the heatmap for the area, if it exists
    heatmap_path = f'static/{area}/interactive_heatmap.html'
    if os.path.exists(heatmap_path):
        os.remove(heatmap_path)

    # Handle the file upload
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)

    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    if file and file.filename.endswith('.csv'):
        save_path = os.path.join(f'borough_assets/{area}/unprocessed_data', file.filename)
        file.save(save_path)
        flash('File successfully uploaded')

    return redirect(url_for('view_data', area=area))

def open_browser():
    """Open the default web browser to the app's home page."""
    webbrowser.open_new("http://127.0.0.1:5000/")

def run_app():
    """Run the Flask app in a background thread."""
    app.run(debug=False, use_reloader=False)

if __name__ == '__main__':
    run_app()
    Timer(1, open_browser).start()
