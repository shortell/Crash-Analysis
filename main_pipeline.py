import os
import pandas as pd
from settings import BASE_DIR, BOROUGH_MAPPING

from data_loading import get_latest_csv, load_accident_data
from data_processing import filter_accidents, assign_zip_codes_knn, create_combined_dataframe, group_and_rank_accidents, add_accident_likelihood_column, cleanse_data
from data_storage import load_master_table, save_master_table
from heatmap_generation import create_interactive_heatmap, save_heatmap


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

        master_table = add_accident_likelihood_column(master_table)

        master_table = cleanse_data(master_table)

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
