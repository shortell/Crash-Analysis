import time
import pandas as pd
import numpy as np
from sklearn.neighbors import KDTree


def create_zip_to_borough_dict(df):
    """
    Return a dictionary of zip code to borough mapping.

    If there are multiple boroughs for a zip code, the borough with the highest count is selected.

    Parameters:
    df (pd.DataFrame): The DataFrame to create the mapping from

    Returns:
    dict: A dictionary of zip codes to boroughs
    """
    zip_borough_counts = df.groupby(
        ["zip_code", "borough"]).size().reset_index(name='accident_count')
    zip_borough_mapping = zip_borough_counts.loc[zip_borough_counts.groupby(
        "zip_code")["accident_count"].idxmax()].reset_index(drop=True)
    zip_to_borough = zip_borough_mapping.set_index("zip_code")["borough"]
    return zip_to_borough.to_dict()


def update_boroughs(df, zip_to_borough_dict):
    """
    Fill in all NaN values and update any record where the DataFrame has a different answer than the dictionary.
    Logs changes made to the DataFrame.

    Parameters:
    df (pd.DataFrame): The DataFrame to update
    zip_to_borough_dict (dict): The dictionary of zip codes to boroughs

    Returns:
    pd.DataFrame: The updated DataFrame
    """
    # Create a mapping series from the dictionary
    zip_to_borough = pd.Series(zip_to_borough_dict)

    # Map the zip codes to boroughs using the dictionary
    mapped_boroughs = df['zip_code'].map(zip_to_borough)

    # Update boroughs where they are NaN or do not match the mapped borough
    df['borough'] = df['borough'].where(
        ~df['borough'].isna() & (df['borough'] == mapped_boroughs),
        mapped_boroughs
    )

    return df


def assign_zip_codes_kdtree(df_with_zip, df_without_zip, n_neighbors):
    """
    Assign zip codes using KD-Tree for faster nearest neighbor search.

    Parameters:
    df_with_zip (pd.DataFrame): DataFrame with zip codes
    df_without_zip (pd.DataFrame): DataFrame without zip codes
    n_neighbors (int): Number of neighbors to consider

    Returns:
    pd.DataFrame: DataFrame with zip codes filled in
    """
    start_time = time.perf_counter()

    # Step 1: Extract training and testing data
    step1_start = time.perf_counter()
    X_train = df_with_zip[["latitude", "longitude"]].values
    y_train = df_with_zip["zip_code"].values
    X_test = df_without_zip[["latitude", "longitude"]].values
    step1_end = time.perf_counter()
    print(f"Step 1 (Data extraction): {step1_end - step1_start:.6f} seconds")

    # Step 2: Build KD-Tree
    step2_start = time.perf_counter()
    tree = KDTree(X_train, metric="euclidean")
    step2_end = time.perf_counter()
    print(f"Step 2 (KD-Tree construction): {step2_end - step2_start:.6f} seconds")

    # Step 3: Query KD-Tree for nearest neighbors
    step3_start = time.perf_counter()
    _, indices = tree.query(X_test, k=n_neighbors)
    step3_end = time.perf_counter()
    print(f"Step 3 (KD-Tree query): {step3_end - step3_start:.6f} seconds")

    # Step 4: Assign the most common zip code among neighbors
    step4_start = time.perf_counter()
    nearest_zips = y_train[indices]
    most_common_zips = np.apply_along_axis(
        lambda zips: np.bincount(zips).argmax(), axis=1, arr=nearest_zips
    )
    df_without_zip.loc[:, "zip_code"] = most_common_zips
    step4_end = time.perf_counter()
    print(f"Step 4 (Assign zip codes): {step4_end - step4_start:.6f} seconds")

    end_time = time.perf_counter()
    print(f"Total time: {end_time - start_time:.6f} seconds")

    return df_without_zip


def create_combined_dataframe(df_zip_lat_long_borough,
                              df_zip_lat_long_no_borough,
                              df_zip_no_lat_long_borough,
                              df_zip_no_lat_long_no_borough,
                              df_no_zip_lat_long_borough,
                              df_no_zip_lat_long_no_borough):
    """
    Combine the accident DataFrames with known and predicted zip codes.

    Parameters:
    df_zip_lat_long_borough (pd.DataFrame): DataFrame with zip code, latitude, longitude, and borough
    df_zip_lat_long_no_borough (pd.DataFrame): DataFrame with zip code, latitude, and longitude
    df_zip_no_lat_long_borough (pd.DataFrame): DataFrame with zip code and borough
    df_zip_no_lat_long_no_borough (pd.DataFrame): DataFrame with zip code
    df_no_zip_lat_long_borough (pd.DataFrame): DataFrame with latitude, longitude, and borough
    df_no_zip_lat_long_no_borough (pd.DataFrame): DataFrame with latitude and longitude

    Returns:
    pd.DataFrame: Combined DataFrame with all accident records
    """
    return pd.concat([
        df_zip_lat_long_borough,
        df_zip_lat_long_no_borough,
        df_zip_no_lat_long_borough,
        df_zip_no_lat_long_no_borough,
        df_no_zip_lat_long_borough,
        df_no_zip_lat_long_no_borough
    ], ignore_index=True).drop_duplicates()


def aggregate_crashes_by_zip(df):
    """
    Aggregates crash count by zip_code and borough, creating a new DataFrame with total crashes.

    :param df: DataFrame with 'id', 'zip_code', 'borough', 'crash_count', 'latitude', 'longitude'
    :return: DataFrame with 'zip_code', 'borough', 'total_crashes' sorted by total_crashes in descending order
    """
    # Group by 'zip_code' and 'borough' and aggregate crash counts
    aggregated_df = df.groupby(['zip_code', 'borough']).agg(
        total_crashes=('crash_count', 'sum')
    ).reset_index()

    # Sort by 'total_crashes' in descending order
    aggregated_df = aggregated_df.sort_values(
        by='total_crashes', ascending=False)

    return aggregated_df
