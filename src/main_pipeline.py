import pandas as pd

from src.data_loading import get_zip_lat_long_borough, get_zip_lat_long_no_borough, get_zip_no_lat_long_borough, get_zip_no_lat_long_no_borough, get_no_zip_lat_long_borough, get_no_zip_lat_long_no_borough, get_no_zip_no_lat_long_borough, get_no_zip_no_lat_long_no_borough
from src.data_processing import assign_zip_codes_kdtree, create_zip_to_borough_dict, update_boroughs, create_combined_dataframe, aggregate_crashes_by_zip
from src.data_formatting import filter_by_borough, rank_by_crash_count, create_crash_likelihood_column, get_total_crashes, get_average_crashes_per_zip, group_into_deciles, rename_columns, rename_bronx_to_the_bronx
from src.data_fetching import fetch_crash_data


# def fetch_and_aggregate_crash_data(start_month, start_year, end_month, end_year, k):
#     data = fetch_crash_data(start_month, start_year, end_month, end_year)

#     if len(data) == 0:
#         return None
#     df = pd.DataFrame(data)

#     df["zip_code"] = pd.to_numeric(
#         df["zip_code"], errors='coerce').astype('Int64')
#     df["borough"] = df["borough"].astype(pd.StringDtype())

#     df_zip_lat_long_borough = get_zip_lat_long_borough(df)
#     df_zip_lat_long_no_borough = get_zip_lat_long_no_borough(df)
#     df_zip_no_lat_long_borough = get_zip_no_lat_long_borough(df)
#     df_zip_no_lat_long_no_borough = get_zip_no_lat_long_no_borough(df)
#     df_no_zip_lat_long_borough = get_no_zip_lat_long_borough(df)
#     df_no_zip_lat_long_no_borough = get_no_zip_lat_long_no_borough(df)

#     zip_borough_map = create_zip_to_borough_dict(df_zip_lat_long_borough)

#     df_no_zip_lat_long_borough = assign_zip_codes_kdtree(
#         df_zip_lat_long_borough, df_no_zip_lat_long_borough, k)
#     df_no_zip_lat_long_no_borough = assign_zip_codes_kdtree(
#         df_zip_lat_long_borough, df_no_zip_lat_long_no_borough, k)

#     # corrects any zip code to borough mismatches
#     df_zip_lat_long_borough = update_boroughs(
#         df_zip_lat_long_borough, zip_borough_map)
#     df_zip_lat_long_no_borough = update_boroughs(
#         df_zip_lat_long_no_borough, zip_borough_map)  # borough missing necessary to fill
#     # corrects any zip code to borough mismatches
#     df_zip_no_lat_long_borough = update_boroughs(
#         df_zip_no_lat_long_borough, zip_borough_map)
#     df_zip_no_lat_long_no_borough = update_boroughs(
#         # borough missing necessary to fill
#         df_zip_no_lat_long_no_borough, zip_borough_map)
#     # corrects any zip code to borough mismatches
#     df_no_zip_lat_long_borough = update_boroughs(
#         df_no_zip_lat_long_borough, zip_borough_map)
#     df_no_zip_lat_long_no_borough = update_boroughs(
#         # borough missing necessary to fill
#         df_no_zip_lat_long_no_borough, zip_borough_map)

#     combined_df = create_combined_dataframe(
#         df_zip_lat_long_borough,
#         df_zip_lat_long_no_borough,
#         df_zip_no_lat_long_borough,
#         df_zip_no_lat_long_no_borough,
#         df_no_zip_lat_long_borough,
#         df_no_zip_lat_long_no_borough)

#     agg_df = aggregate_crashes_by_zip(combined_df)
#     agg_df = rename_bronx_to_the_bronx(agg_df)

#     return agg_df

def preprocess_dataframe(df):
    df["zip_code"] = pd.to_numeric(
        df["zip_code"], errors='coerce').astype('Int64')
    df["borough"] = df["borough"].astype(pd.StringDtype())
    return df


def fill_missing_data(df, k):
    df_zip_lat_long_borough = get_zip_lat_long_borough(df)
    df_zip_lat_long_no_borough = get_zip_lat_long_no_borough(df)
    df_zip_no_lat_long_borough = get_zip_no_lat_long_borough(df)
    df_zip_no_lat_long_no_borough = get_zip_no_lat_long_no_borough(df)
    df_no_zip_lat_long_borough = get_no_zip_lat_long_borough(df)
    df_no_zip_lat_long_no_borough = get_no_zip_lat_long_no_borough(df)

    # print the length of each dataframe
    print(f"df_zip_lat_long_borough: {len(df_zip_lat_long_borough)}")
    print(f"df_zip_lat_long_no_borough: {len(df_zip_lat_long_no_borough)}")
    print(f"df_zip_no_lat_long_borough: {len(df_zip_no_lat_long_borough)}")
    print(f"df_zip_no_lat_long_no_borough: {len(df_zip_no_lat_long_no_borough)}")
    print(f"df_no_zip_lat_long_borough: {len(df_no_zip_lat_long_borough)}")
    print(f"df_no_zip_lat_long_no_borough: {len(df_no_zip_lat_long_no_borough)}")

    zip_borough_map = create_zip_to_borough_dict(df_zip_lat_long_borough)

    if not df_no_zip_lat_long_borough.empty:
        df_no_zip_lat_long_borough = assign_zip_codes_kdtree(
            df_zip_lat_long_borough, df_no_zip_lat_long_borough, k)
    if not df_no_zip_lat_long_no_borough.empty:
        df_no_zip_lat_long_no_borough = assign_zip_codes_kdtree(
            df_zip_lat_long_borough, df_no_zip_lat_long_no_borough, k)

    df_zip_lat_long_borough = update_boroughs(
        df_zip_lat_long_borough, zip_borough_map)
    df_zip_lat_long_no_borough = update_boroughs(
        df_zip_lat_long_no_borough, zip_borough_map)
    df_zip_no_lat_long_borough = update_boroughs(
        df_zip_no_lat_long_borough, zip_borough_map)
    df_zip_no_lat_long_no_borough = update_boroughs(
        df_zip_no_lat_long_no_borough, zip_borough_map)
    df_no_zip_lat_long_borough = update_boroughs(
        df_no_zip_lat_long_borough, zip_borough_map)
    df_no_zip_lat_long_no_borough = update_boroughs(
        df_no_zip_lat_long_no_borough, zip_borough_map)

    return {
        "df_zip_lat_long_borough": df_zip_lat_long_borough,
        "df_zip_lat_long_no_borough": df_zip_lat_long_no_borough,
        "df_zip_no_lat_long_borough": df_zip_no_lat_long_borough,
        "df_zip_no_lat_long_no_borough": df_zip_no_lat_long_no_borough,
        "df_no_zip_lat_long_borough": df_no_zip_lat_long_borough,
        "df_no_zip_lat_long_no_borough": df_no_zip_lat_long_no_borough
    }


def create_combined_dataframe_from_parts(df_parts):
    return create_combined_dataframe(
        df_parts["df_zip_lat_long_borough"],
        df_parts["df_zip_lat_long_no_borough"],
        df_parts["df_zip_no_lat_long_borough"],
        df_parts["df_zip_no_lat_long_no_borough"],
        df_parts["df_no_zip_lat_long_borough"],
        df_parts["df_no_zip_lat_long_no_borough"]
    )


def aggregate_and_format_data(df):
    agg_df = aggregate_crashes_by_zip(df)
    agg_df = rename_bronx_to_the_bronx(agg_df)
    return agg_df


def fetch_and_aggregate_crash_data(start_month, start_year, end_month, end_year, k):
    data = fetch_crash_data(start_month, start_year, end_month, end_year)
    print(data is None or len(data) == 0)
    if data is None or len(data) == 0:
        return None

    df = pd.DataFrame(data)
    df = preprocess_dataframe(df)
    df = fill_missing_data(df, k)
    combined_df = create_combined_dataframe_from_parts(df)
    agg_df = aggregate_and_format_data(combined_df)

    return agg_df


def process_and_format_crash_data(agg_df, area=None):
    formatted_df_by_area = filter_by_borough(agg_df, area)
    total_crashes = get_total_crashes(formatted_df_by_area)
    average_crashes_per_zip = get_average_crashes_per_zip(formatted_df_by_area)
    formatted_df_by_area = rank_by_crash_count(formatted_df_by_area)
    formatted_df_by_area = create_crash_likelihood_column(
        formatted_df_by_area, average_crashes_per_zip)
    formatted_df_by_area = group_into_deciles(formatted_df_by_area)
    formatted_df_by_area = rename_columns(formatted_df_by_area)

    return total_crashes, average_crashes_per_zip, formatted_df_by_area


# agg_df = fetch_and_aggregate_crash_data(1, 2022, 12, 2022, 10)

# total_crashes, average_crashes_per_zip, filtered_df = process_and_format_crash_data(agg_df)

# total_crashes, average_crashes_per_zip, filtered_df = process_and_format_crash_data(agg_df, 'Queens')


# def main(borough: str, k: int):
#     """
#     Main function to execute the accident data processing pipeline or load precomputed data.
#     Automatically generates and saves a heatmap if one does not exist.

#     Returns:
#     - total_accidents: Total number of accidents in the borough.
#     - average_accidents_per_zip: The average number of accidents per zip code.
#     - master_table: The final processed DataFrame containing accident data.
#     """
#     # Check if the master table already exists in processed_data
#     master_table = load_master_table(borough)

#     if master_table is not None:
#         print(f"Loaded precomputed master table for {borough}.")
#     else:
#         # If no precomputed master table is found, process the data
#         print(f"No precomputed master table found for {borough}. Starting pipeline...")

#         file_name = get_latest_csv(borough)
#         df = load_accident_data(file_name)

#         # citywide_file_name = get_latest_csv('citywide')
#         # citywide_df = load_accident_data(citywide_file_name)

#         df_zip_lat_long, df_no_zip_lat_long, df_zip_no_lat_long, df_no_zip_no_lat_long, df_null_crash_count = filter_accidents(
#             df)

#         knn_crashlist = assign_zip_codes_knn(
#             df_zip_lat_long, df_no_zip_lat_long, k=k)
#         combined_df = create_combined_dataframe(
#             df_zip_lat_long, knn_crashlist, df_zip_no_lat_long)

#         master_table = group_and_rank_accidents(combined_df)

#         master_table = add_accident_likelihood_column(master_table)

#         master_table = cleanse_data(master_table)

#         # Save the computed master table to processed_data
#         save_master_table(master_table, borough)

#     # Calculate total accidents and average accidents per zip code
#     total_accidents = master_table['Accident Count'].sum()
#     average_accidents_per_zip = master_table['Accident Count'].mean()

#     # Generate and save the heatmap
#     heatmap_dir = os.path.join(BASE_DIR, borough, 'heatmap')
#     heatmap_file = os.path.join(heatmap_dir, 'interactive_heatmap.html')

#     if os.path.exists(heatmap_file):
#         print(f"Heatmap already exists for {borough}.")
#     else:
#         print(f"Generating heatmap for {borough}...")
#         heatmap = create_interactive_heatmap(
#             BOROUGH_MAPPING[borough], master_table)
#         save_heatmap(heatmap, borough)
#         print(f"Heatmap saved for {borough}.")

#     # Return total accidents, average accidents per zip code, and the master table
#     return total_accidents, round(average_accidents_per_zip, 2), master_table
