import pandas as pd
from sklearn.neighbors import KNeighborsClassifier
from settings import COLUMN_MAPPING


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


def cleanse_data(df):
    """
    Remove duplicate zip code entries, keeping the entry with the highest accident count for each zip code.
    Sort the resulting DataFrame by Accident Count in descending order.
    """
    # Sort by 'Zip Code' and 'Accident Count' in descending order so that highest accident counts come first
    df = df.sort_values(by=[COLUMN_MAPPING['zip_code'], COLUMN_MAPPING['accident_count']], ascending=[True, False])

    # Drop duplicates by 'Zip Code', keeping the first occurrence (highest accident count)
    cleaned_df = df.drop_duplicates(subset=[COLUMN_MAPPING['zip_code']], keep='first')

    return cleaned_df


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


def add_accident_likelihood_column(df):
    """
    Add a column to the DataFrame that calculates the likelihood of an accident 
    as a multiple of the average accident count per zip code, rounded to 2 decimal places.
    """
    average_accidents_per_zip = df['Accident Count'].mean()
    df['Accident Likelihood'] = (
        df['Accident Count'] / average_accidents_per_zip).round(2)
    return df
