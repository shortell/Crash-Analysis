import pandas as pd
from sklearn.neighbors import KNeighborsClassifier

def split_accidents_by_zipcode(file_name):
    """
    Load accident data from a CSV file and split into two DataFrames:
    one with valid zip codes and one without.

    Parameters:
    - file_name (str): The file path of the CSV file containing accident data.

    Returns:
    - with_zip (DataFrame): DataFrame containing accidents with zip codes.
    - without_zip (DataFrame): DataFrame containing accidents without zip codes.
    """
    # Load the CSV data into a pandas DataFrame
    df = pd.read_csv(file_name)

    # Split the data into two groups: with zip codes and without zip codes
    with_zip = df[df['zip_code'].notna() & (df['zip_code'] != '')]  # Accidents with valid zip codes
    without_zip = df[df['zip_code'].isna() | (df['zip_code'] == '')]  # Accidents missing zip codes

    return with_zip, without_zip


def assign_zipcodes_knn(with_zip, without_zip, k=1):
    """
    Assign zip codes to accidents missing them using K-Nearest Neighbors (KNN).

    Parameters:
    - with_zip (DataFrame): DataFrame containing accidents with valid zip codes.
    - without_zip (DataFrame): DataFrame containing accidents without zip codes.
    - k (int): Number of neighbors to consider for KNN. Default is 1.

    Returns:
    - all_accidents (DataFrame): Combined DataFrame with all accidents and assigned zip codes.
    """
    # Ensure both DataFrames have the necessary latitude and longitude columns
    if 'latitude' not in with_zip.columns or 'longitude' not in with_zip.columns:
        raise ValueError("with_zip dataframe must contain 'latitude' and 'longitude' columns")
    if 'latitude' not in without_zip.columns or 'longitude' not in without_zip.columns:
        raise ValueError("without_zip dataframe must contain 'latitude' and 'longitude' columns")

    # Extract the features (latitude and longitude) and target (zip_code) from the with_zip DataFrame
    X_with_zip = with_zip[['latitude', 'longitude']]  # Features for training
    y_with_zip = with_zip['zip_code']  # Target variable (zip codes)

    # Extract the features (latitude and longitude) from the without_zip DataFrame
    X_without_zip = without_zip[['latitude', 'longitude']]  # Features for prediction

    # Initialize the KNeighborsClassifier with k neighbors
    knn = KNeighborsClassifier(n_neighbors=k)

    # Fit the model using the accidents with zip codes
    knn.fit(X_with_zip, y_with_zip)

    # Predict zip codes for accidents without zip codes
    predicted_zip_codes = knn.predict(X_without_zip)

    # Assign the predicted zip codes to the without_zip DataFrame
    without_zip['zip_code'] = predicted_zip_codes

    # Concatenate the with_zip and modified without_zip DataFrames
    all_accidents = pd.concat([with_zip, without_zip], ignore_index=True)

    # Return the concatenated DataFrame containing all accidents
    return all_accidents


def count_accidents_per_zipcode(all_accidents):
    """
    Count the number of accidents per zip code and calculate the average number of accidents per zip code.

    Parameters:
    - all_accidents (DataFrame): A DataFrame containing accident data with zip codes.

    Returns:
    - accidents_per_zipcode (DataFrame): A DataFrame with 'zip_code' and 'accident_count' columns.
    - average_accidents_per_zip (float): The average number of accidents per zip code.
    """
    # Count the number of accidents per zip code
    accidents_per_zipcode = all_accidents['zip_code'].value_counts().reset_index()
    accidents_per_zipcode.columns = ['zip_code', 'accident_count']  # Rename columns for clarity

    # Calculate the average number of accidents per zip code
    average_accidents_per_zip = accidents_per_zipcode['accident_count'].mean()

    return accidents_per_zipcode, average_accidents_per_zip


def split_zipcodes_into_deciles(accidents_per_zipcode, average_accidents_per_zip):
    """
    Split zip codes into deciles based on the number of accidents, and calculate the multiplier relative to the average.

    Parameters:
    - accidents_per_zipcode (DataFrame): A DataFrame containing 'zip_code' and 'accident_count'.
    - average_accidents_per_zip (float): The average number of accidents per zip code.

    Returns:
    - decile_table (DataFrame): A DataFrame with 'Decile', 'Zip Code', 'Accident Count', 'Multiplier'.
    """
    # Create deciles based on accident counts
    accidents_per_zipcode['decile'] = pd.qcut(accidents_per_zipcode['accident_count'], q=10, labels=False) + 1

    # Initialize a list to store the new rows
    rows = []

    # Iterate over each decile
    for decile, group in accidents_per_zipcode.groupby('decile'):
        for index, row in group.iterrows():
            # Append each zip code with its accident count and multiplier
            multiplier = row['accident_count'] / average_accidents_per_zip  # Calculate multiplier
            rows.append({
                'Decile': decile,
                'Zip Code': row['zip_code'],
                'Accident Count': row['accident_count'],
                'Multiplier': multiplier
            })

    # Create a new DataFrame from the rows list
    decile_table = pd.DataFrame(rows)

    return decile_table


def main(file_name, k):
    """
    Main function to execute the accident data processing pipeline.

    Parameters:
    - file_name (str): The file path of the CSV file containing accident data.
    - k (int): Number of neighbors to use for KNN when assigning missing zip codes.

    Returns:
    - total_accidents (int): The total number of accidents in the dataset.
    - average_accidents_per_zip (float): The average number of accidents per zip code.
    - decile_table_sorted (DataFrame): A DataFrame containing 'Decile', 'Zip Code', 'Accident Count', 'Multiplier'.
    """
    # Set Pandas display options to show all rows and columns
    pd.set_option('display.max_rows', None)  # Show all rows
    pd.set_option('display.max_columns', None)  # Show all columns

    # Split the accidents into those with and without zip codes
    with_zip, without_zip = split_accidents_by_zipcode(file_name)

    # Assign zip codes to accidents without zip codes
    all_accidents = assign_zipcodes_knn(with_zip, without_zip, k=k)

    # Count accidents per zip code and calculate the average
    accidents_per_zipcode, average_accidents_per_zip = count_accidents_per_zipcode(all_accidents)

    # Calculate total number of accidents
    total_accidents = all_accidents.shape[0]

    # Split zip codes into deciles based on accidents
    decile_table = split_zipcodes_into_deciles(accidents_per_zipcode, average_accidents_per_zip)

    # Sort the decile table by Accident Count in descending order
    decile_table_sorted = decile_table.sort_values(by='Accident Count', ascending=False).reset_index(drop=True)

    return total_accidents, average_accidents_per_zip, decile_table_sorted[['Decile', 'Zip Code', 'Accident Count', 'Multiplier']]
