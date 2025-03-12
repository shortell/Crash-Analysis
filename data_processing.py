import pandas as pd
import numpy as np
from sklearn.neighbors import KDTree


def create_zip_to_borough_dict(df):
    """
    Return a dictionary of zip code to borough mapping.

    If there are multiple boroughs for a zip code, the borough with the highest count is selected.
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
    """
    # Create a mapping series from the dictionary
    zip_to_borough = pd.Series(zip_to_borough_dict)

    # Iterate over each row in the DataFrame
    for idx, row in df.iterrows():
        zip_code = row['zip_code']
        current_borough = row['borough']
        mapped_borough = zip_to_borough.get(zip_code, None)

        # Check if the borough is NaN or does not match the mapping
        if pd.isna(current_borough) or current_borough != mapped_borough:
            df.at[idx, 'borough'] = mapped_borough

    return df


def assign_zip_codes_kdtree(df_with_zip, df_without_zip, n_neighbors):
    """
    Assign zip codes using KD-Tree for faster nearest neighbor search.
    """
    X_train = df_with_zip[["latitude", "longitude"]].values
    y_train = df_with_zip["zip_code"].values
    X_test = df_without_zip[["latitude", "longitude"]].values

    # KD-Tree with Euclidean distance
    tree = KDTree(X_train, metric="euclidean")
    distances, indices = tree.query(X_test, k=n_neighbors)

    # Assign the most common zip code among neighbors
    nearest_zips = y_train[indices]
    df_without_zip.loc[:, "zip_code"] = [
        np.bincount(zips).argmax() for zips in nearest_zips]

    return df_without_zip


def create_combined_dataframe(df_zip_lat_long_borough,
                              df_zip_lat_long_no_borough,
                              df_zip_no_lat_long_borough,
                              df_zip_no_lat_long_no_borough,
                              df_no_zip_lat_long_borough,
                              df_no_zip_lat_long_no_borough):
    """
    Combine the accident DataFrames with known and predicted zip codes.
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
