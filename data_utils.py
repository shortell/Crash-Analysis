import os
import glob
import pandas as pd
from sklearn.neighbors import KNeighborsClassifier

# Base directory where the borough datasets are stored
BASE_DIR = "data/nyc_csv/"
# List of boroughs that users can view/upload
DIRECTORIES = ['brooklyn', 'citywide', 'manhattan',
               'queens', 'staten_island', 'the_bronx']


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


def split_accidents_by_zip_code(file_name):
    """
    Load accident data from a CSV file and split into two DataFrames:
    one with valid zip codes and one without zip codes.

    Parameters:
    - file_name (str): The file path of the CSV file containing accident data.

    Returns:
    - with_zip (DataFrame): DataFrame containing accidents with valid zip codes.
    - without_zip (DataFrame): DataFrame containing accidents with latitude and longitude but no zip code.
    """
    # Load the CSV data into a pandas DataFrame
    try:
        df = pd.read_csv(file_name)

        # Select only the relevant columns
        df = df[['latitude', 'longitude', 'borough', 'zip_code', 'crash_count',]]

        # Split the data into two groups:
        # 1. with_zip: contains accidents with valid zip codes
        # 2. without_zip: contains accidents with latitude and longitude but no zip code

        with_zip = df[df['zip_code'].notna() & (df['zip_code'] != '')]
        without_zip = df[(df['zip_code'].isna() | (df['zip_code'] == ''))]

        # Remove rows with NaN values in critical columns for the with_zip DataFrame
        critical_columns = ['latitude', 'longitude', 'crash_count',]
        with_zip = with_zip.dropna(subset=critical_columns, how='any')

        # For the without_zip DataFrame, keep only rows with valid latitude and longitude
        without_zip = without_zip[without_zip['latitude'].notna(
        ) & without_zip['longitude'].notna()]

        return with_zip, without_zip
    except Exception as e:
        print(f"An error occurred in split accidents by zipcode: {e}")
        return None, None


def assign_zip_codes_knn(with_zip, without_zip, k=1):
    """
    Assign zip codes to accidents missing them using K-Nearest Neighbors (KNN).

    Parameters:
    - with_zip (DataFrame): DataFrame containing accidents with valid zip codes.
    - without_zip (DataFrame): DataFrame containing accidents without zip codes.
    - k (int): Number of neighbors to consider for KNN. Default is 1.

    Returns:
    - all_accidents (DataFrame): Combined DataFrame with all accidents and assigned zip codes.
    """
    try:
        # Ensure both DataFrames have the necessary latitude and longitude columns
        if 'latitude' not in with_zip.columns or 'longitude' not in with_zip.columns:
            raise ValueError(
                "with_zip dataframe must contain 'latitude' and 'longitude' columns")
        if 'latitude' not in without_zip.columns or 'longitude' not in without_zip.columns:
            raise ValueError(
                "without_zip dataframe must contain 'latitude' and 'longitude' columns")

        # Extract the features (latitude and longitude) and target (zip_code) from the with_zip DataFrame
        # Features for training
        X_with_zip = with_zip[['latitude', 'longitude']]
        y_with_zip = with_zip['zip_code']  # Target variable (zip codes)

        # Extract the features (latitude and longitude) from the without_zip DataFrame
        X_without_zip = without_zip[['latitude', 'longitude']]

        # Initialize the KNeighborsClassifier with k neighbors
        knn = KNeighborsClassifier(n_neighbors=k)

        # Fit the model using the accidents with zip codes
        knn.fit(X_with_zip, y_with_zip)

        # Predict zip codes for accidents without zip codes
        predicted_zip_codes = knn.predict(X_without_zip)

        # Assign the predicted zip codes to the without_zip DataFrame
        without_zip['zip_code'] = predicted_zip_codes

        # Concatenate the 'borough' column to the without_zip DataFrame to preserve the information
        without_zip['borough'] = without_zip['borough']

        # Concatenate the with_zip and modified without_zip DataFrames
        all_accidents = pd.concat([with_zip, without_zip], ignore_index=True)

        # Return the concatenated DataFrame containing all accidents
        return all_accidents
    except Exception as e:
        print(f"An error occurred in assign zipcodes knn: {e}")
        return None


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


def split_zip_codes_into_deciles(accidents_per_zipcode, average_accidents_per_zip):
    try:
        # Sort by accident count in descending order
        accidents_per_zipcode = accidents_per_zipcode.sort_values(
            by='accident_count', ascending=False).reset_index(drop=True)

        # Add a rank column based on sorted accident counts
        accidents_per_zipcode['rank'] = accidents_per_zipcode.index + 1

        # Create deciles based on unique ranks
        num_unique_ranks = len(accidents_per_zipcode['rank'].unique())
        accidents_per_zipcode['decile'] = pd.qcut(accidents_per_zipcode['rank'], q=min(
            num_unique_ranks, 10), labels=range(10, 0, -1))

        # Calculate accident likelihood factor
        accidents_per_zipcode['Accident Likelihood Factor'] = round(
            accidents_per_zipcode['accident_count'] / average_accidents_per_zip, 2)

        # Select relevant columns
        decile_table = accidents_per_zipcode[[
            'rank', 'decile', 'zip_code', 'borough', 'accident_count', 'Accident Likelihood Factor']].copy()

        # Rename columns to match desired output
        decile_table.rename(columns={'rank': 'Rank', 'decile': 'Decile', 'zip_code': 'Zip Code',
                            'borough': 'Borough', 'accident_count': 'Accident Count'}, inplace=True)

        return decile_table
    except Exception as e:
        print(f"An error occurred in split zipcodes into deciles: {e}")
        return None


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
    # Fetch the latest CSV file for the specified borough
    file_name = get_latest_csv(borough)

    # Split the accidents into those with and without zip codes
    with_zip, without_zip = split_accidents_by_zip_code(file_name)

    # Assign zip codes to accidents without zip codes
    all_accidents = assign_zip_codes_knn(with_zip, without_zip, k=k)

    # Count accidents per zip code and calculate the average
    accidents_per_zipcode, average_accidents_per_zip = count_accidents_per_zipcode(
        all_accidents)

    # Calculate total number of accidents
    total_accidents = all_accidents.shape[0]

    # Split zip codes into deciles based on accidents
    decile_table = split_zip_codes_into_deciles(
        accidents_per_zipcode, average_accidents_per_zip)

    # Sort the decile table by Accident Count in descending order
    decile_table_sorted = decile_table.sort_values(
        by='Accident Count', ascending=False).reset_index(drop=True)

    return total_accidents, average_accidents_per_zip, decile_table_sorted


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
