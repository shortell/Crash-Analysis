import tracemalloc
import pandas as pd
import time

from src.data_loading import get_zip_lat_long_borough, get_zip_lat_long_no_borough, get_zip_no_lat_long_borough, get_zip_no_lat_long_no_borough, get_no_zip_lat_long_borough, get_no_zip_lat_long_no_borough, get_no_zip_no_lat_long_borough, get_no_zip_no_lat_long_no_borough
from src.data_processing import assign_zip_codes_kdtree, create_zip_to_borough_dict, update_boroughs, aggregate_crashes_by_zip
from src.data_formatting import filter_by_borough, rank_by_crash_count, create_crash_likelihood_column, get_total_crashes, get_average_crashes_per_zip, group_into_deciles, rename_columns, rename_bronx_to_the_bronx
from src.data_fetching import fetch_crash_data


def preprocess_dataframe(df):
    """
    Preprocesses the dataframe by converting columns to the correct data types

    Parameters:
    df (pd.DataFrame): The dataframe to preprocess

    Returns:
    pd.DataFrame: The preprocessed dataframe
    """
    df["zip_code"] = pd.to_numeric(
        df["zip_code"], errors='coerce').astype('Int32')
    df["borough"] = df["borough"].astype(pd.StringDtype())
    df["latitude"] = df["latitude"].astype("float32")
    df["longitude"] = df["longitude"].astype("float32")
    return df


def split_dataframe_by_conditions(df):
    """
    Splits the dataframe into parts based on zip code, latitude/longitude, and borough conditions.

    Parameters: 
    df (pd.DataFrame): The dataframe to split

    Returns:
    dict: A dictionary containing the split dataframes
    """
    return {
        "df_zip_lat_long_borough": get_zip_lat_long_borough(df),
        "df_zip_lat_long_no_borough": get_zip_lat_long_no_borough(df),
        "df_zip_no_lat_long_borough": get_zip_no_lat_long_borough(df),
        "df_zip_no_lat_long_no_borough": get_zip_no_lat_long_no_borough(df),
        "df_no_zip_lat_long_borough": get_no_zip_lat_long_borough(df),
        "df_no_zip_lat_long_no_borough": get_no_zip_lat_long_no_borough(df),
    }


def assign_missing_zip_codes(df_parts, k):
    """
    Assigns zip codes to rows missing them using k-d tree.

    Parameters:
    df_parts (dict): A dictionary containing the split dataframes
    k (int): The number of nearest neighbors to consider when assigning zip codes

    Returns:
    dict: A dictionary containing the updated dataframes with missing zip codes filled in
    """
    if not df_parts["df_no_zip_lat_long_borough"].empty:
        df_parts["df_no_zip_lat_long_borough"] = assign_zip_codes_kdtree(
            df_parts["df_zip_lat_long_borough"], df_parts["df_no_zip_lat_long_borough"], k
        )
    if not df_parts["df_no_zip_lat_long_no_borough"].empty:
        df_parts["df_no_zip_lat_long_no_borough"] = assign_zip_codes_kdtree(
            df_parts["df_zip_lat_long_borough"], df_parts["df_no_zip_lat_long_no_borough"], k
        )
    return df_parts


def combine_dataframes(df_parts):
    """
    Combines all dataframe parts into a single dataframe.

    Parameters:
    df_parts (dict): A dictionary containing the split dataframes

    Returns:
    pd.DataFrame: The combined dataframe
    """
    return pd.concat([
        df_parts["df_zip_lat_long_borough"],
        df_parts["df_zip_lat_long_no_borough"],
        df_parts["df_zip_no_lat_long_borough"],
        df_parts["df_zip_no_lat_long_no_borough"],
        df_parts["df_no_zip_lat_long_borough"],
        df_parts["df_no_zip_lat_long_no_borough"]
    ])


def fill_missing_data(df, k):
    """
    Fills in missing data in the dataframe by assigning zip codes to rows that are missing them.

    Parameters:
    df (pd.DataFrame): The dataframe to fill missing data in
    k (int): The number of nearest neighbors to consider when assigning zip codes

    Returns:
    pd.DataFrame: The dataframe with missing data filled in
    """
    # Split the dataframe into parts

    df_parts = split_dataframe_by_conditions(df)

    # Create a mapping of zip codes to boroughs

    zip_borough_map = create_zip_to_borough_dict(
        df_parts["df_zip_lat_long_borough"])

    # Assign missing zip codes
    start = time.perf_counter()
    df_parts = assign_missing_zip_codes(df_parts, k)
    end = time.perf_counter()
    print(f"Zip code assignment took {end - start:0.4f} seconds")

    # Combine all dataframes into one

    combined_df = combine_dataframes(df_parts)

    # Update boroughs in the combined dataframe
    combined_df = update_boroughs(combined_df, zip_borough_map)

    return combined_df


def aggregate_and_format_data(df):
    agg_df = aggregate_crashes_by_zip(df)
    agg_df = rename_bronx_to_the_bronx(agg_df)
    return agg_df


def fetch_and_aggregate_crash_data(start_month, start_year, end_month, end_year, k):
    """
    Fetches and aggregates crash data for a given time period.

    Parameters:
    start_month (int): The starting month
    start_year (int): The starting year
    end_month (int): The ending month
    end_year (int): The ending year
    k (int): The number of nearest neighbors to consider when assigning zip codes

    Returns:
    pd.DataFrame: The aggregated crash
    """

    start = time.perf_counter()
    tracemalloc.start()
    data = fetch_crash_data(start_month, start_year, end_month, end_year)
    if data is None or len(data) == 0:
        return None

    df = pd.DataFrame(data)
    end = time.perf_counter()
    print(f"Data fetching took {end - start:0.4f} seconds")

    df = preprocess_dataframe(df)
    # start = time.perf_counter()
    df = fill_missing_data(df, k)
    # end = time.perf_counter()
    # print(f"Data filling took {end - start:0.4f} seconds")

    agg_df = aggregate_and_format_data(df)

    # Your code here
    current, peak = tracemalloc.get_traced_memory()
    print(f"Current memory usage: {current / 10**6} MB; Peak: {peak / 10**6} MB")
    tracemalloc.stop()
    return agg_df


def process_and_format_crash_data(agg_df, area=None):
    """
    Processes and formats the crash data for a given area.

    Parameters:
    agg_df (pd.DataFrame): The aggregated crash data
    area (str): The area to filter the data by

    Returns:
    int: The total number of crashes in the area
    float: The average number of crashes per zip code in the area
    pd.DataFrame: The formatted crash data for the area
    """
    formatted_df_by_area = filter_by_borough(agg_df, area)
    total_crashes = get_total_crashes(formatted_df_by_area)
    average_crashes_per_zip = get_average_crashes_per_zip(formatted_df_by_area)
    formatted_df_by_area = rank_by_crash_count(formatted_df_by_area)
    formatted_df_by_area = create_crash_likelihood_column(
        formatted_df_by_area, average_crashes_per_zip)
    formatted_df_by_area = group_into_deciles(formatted_df_by_area)
    formatted_df_by_area = rename_columns(formatted_df_by_area)

    return total_crashes, average_crashes_per_zip, formatted_df_by_area
