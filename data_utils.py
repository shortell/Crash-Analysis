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
    #Load the CSV data into a pandas DataFrame
    df = pd.read_csv(file_name)

    #Split the data into two groups: with zip codes and without zip codes
    with_zip = df[df['zip_code'].notna() & (df['zip_code'] != '')
                  ]  #Accidents with valid zip codes
    #Accidents missing zip codes
    without_zip = df[df['zip_code'].isna() | (df['zip_code'] == '')]

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
    #Ensure both DataFrames have the necessary latitude and longitude columns
    if 'latitude' not in with_zip.columns or 'longitude' not in with_zip.columns:
        raise ValueError(
            "with_zip dataframe must contain 'latitude' and 'longitude' columns")
    if 'latitude' not in without_zip.columns or 'longitude' not in without_zip.columns:
        raise ValueError(
            "without_zip dataframe must contain 'latitude' and 'longitude' columns")

    #Extract the features (latitude and longitude) and target (zip_code) from the with_zip DataFrame
    X_with_zip = with_zip[['latitude', 'longitude']]  #Features for training
    y_with_zip = with_zip['zip_code']  #Target variable (zip codes)

    #Extract the features (latitude and longitude) from the without_zip DataFrame
    #Features for prediction
    X_without_zip = without_zip[['latitude', 'longitude']]

    #Initialize the KNeighborsClassifier with k neighbors
    knn = KNeighborsClassifier(n_neighbors=k)

    #Fit the model using the accidents with zip codes
    knn.fit(X_with_zip, y_with_zip)

    #Predict zip codes for accidents without zip codes
    predicted_zip_codes = knn.predict(X_without_zip)

    #Assign the predicted zip codes to the without_zip DataFrame
    without_zip['zip_code'] = predicted_zip_codes

    #Concatenate the with_zip and modified without_zip DataFrames
    all_accidents = pd.concat([with_zip, without_zip], ignore_index=True)

    #Return the concatenated DataFrame containing all accidents
    return all_accidents


def count_accidents_per_zipcode(all_accidents):
    """
    Count the number of accidents per zip code and calculate the average number of persons injured
    and/or killed per accident per zip code.

    Parameters:
    - all_accidents (DataFrame): A DataFrame containing accident data with zip codes.

    Returns:
    - accidents_per_zipcode (DataFrame): A DataFrame with 'zip_code', 'accident_count', and
      'average_persons_injured_or_killed' columns.
    - average_accidents_per_zip (float): The average number of accidents per zip code.
    """
    #Count the number of accidents per zip code
    accidents_per_zipcode = all_accidents['zip_code'].value_counts(
    ).reset_index()
    accidents_per_zipcode.columns = [
        'zip_code', 'accident_count']  #Rename columns for clarity

    #Calculate the total number of persons injured and killed for each accident
    all_accidents['total_persons'] = all_accidents['number_of_persons_injured'] + \
        all_accidents['number_of_persons_killed']

    #Calculate the total persons injured and killed per zip code
    total_persons_per_zip = all_accidents.groupby(
        'zip_code')['total_persons'].sum().reset_index()

    #Merge with accidents_per_zipcode
    accidents_per_zipcode = accidents_per_zipcode.merge(
        total_persons_per_zip, on='zip_code', how='left').fillna(0)

    #Calculate the average number of persons injured or killed per accident
    accidents_per_zipcode['average_persons_injured_or_killed'] = accidents_per_zipcode['total_persons'] / \
        accidents_per_zipcode['accident_count']

    #Calculate the average number of accidents per zip code
    average_accidents_per_zip = accidents_per_zipcode['accident_count'].mean()

    return accidents_per_zipcode[['zip_code', 'accident_count', 'average_persons_injured_or_killed']], average_accidents_per_zip


def split_zipcodes_into_deciles(accidents_per_zipcode, average_accidents_per_zip):
    """
    Split zip codes into deciles based on the number of accidents, and calculate the multiplier relative to the average.

    Parameters:
    - accidents_per_zipcode (DataFrame): A DataFrame containing 'zip_code', 'accident_count', and 'average_persons_injured_or_killed'.
    - average_accidents_per_zip (float): The average number of accidents per zip code.

    Returns:
    - decile_table (DataFrame): A DataFrame with 'Decile', 'Zip Code', 'Accident Count', 'Multiplier'.
    """
    #Create deciles based on accident counts
    accidents_per_zipcode['decile'] = pd.qcut(
        accidents_per_zipcode['accident_count'], q=10, labels=False) + 1

    #Initialize a list to store the new rows
    rows = []

    #Iterate over each decile
    for decile, group in accidents_per_zipcode.groupby('decile'):
        for _, row in group.iterrows():
            #Append each zip code with its accident count and Accident Likelihood Factor
            #Calculate Accident Likelihood Factor
            accident_likelihood_factor = row['accident_count'] / \
                average_accidents_per_zip
            rows.append({
                'Decile': decile,
                'Zip Code': row['zip_code'],
                'Accident Count': row['accident_count'],
                #Optionally include this info
                'Average Persons Injured/Killed': row['average_persons_injured_or_killed'],
                'Accident Likelihood Factor': accident_likelihood_factor,
            })

    #Create a new DataFrame from the rows list
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
    #Set Pandas display options to show all rows and columns
    pd.set_option('display.max_rows', None)  #Show all rows
    pd.set_option('display.max_columns', None)  #Show all columns

    #Split the accidents into those with and without zip codes
    with_zip, without_zip = split_accidents_by_zipcode(file_name)

    #Assign zip codes to accidents without zip codes
    all_accidents = assign_zipcodes_knn(with_zip, without_zip, k=k)

    #Count accidents per zip code and calculate the average
    accidents_per_zipcode, average_accidents_per_zip = count_accidents_per_zipcode(
        all_accidents)

    #Calculate total number of accidents
    total_accidents = all_accidents.shape[0]

    #Split zip codes into deciles based on accidents
    decile_table = split_zipcodes_into_deciles(
        accidents_per_zipcode, average_accidents_per_zip)

    #Sort the decile table by Accident Count in descending order
    decile_table_sorted = decile_table.sort_values(
        by='Accident Count', ascending=False).reset_index(drop=True)

    return total_accidents, average_accidents_per_zip, decile_table_sorted

# import pandas as pd
# from sklearn.neighbors import KNeighborsClassifier

#def split_accidents_by_zipcode(file_name):
#     """
#     Load accident data from a CSV file and split into two DataFrames:
#     one with valid zip codes and one without.

#     Parameters:
#     - file_name (str): The file path of the CSV file containing accident data.

#     Returns:
#     - with_zip (DataFrame): DataFrame containing accidents with zip codes.
#     - without_zip (DataFrame): DataFrame containing accidents without zip codes.
#     """
#     # Load the CSV data into a pandas DataFrame
#     df = pd.read_csv(file_name)

#     # Remove records that do not contain (latitude, longitude) AND zip_code
#     df = df[df[['latitude', 'longitude', 'zip_code']].notna().all(axis=1) & (df['zip_code'] != '')]

#     # Split the data into two groups: with zip codes and without zip codes
#     with_zip = df[df['zip_code'].notna() & (df['zip_code'] != '')]  # Accidents with valid zip codes
#     without_zip = df[df['zip_code'].isna() | (df['zip_code'] == '')]  # Accidents missing zip codes

#     return with_zip, without_zip


# def assign_zipcodes_knn(with_zip, without_zip, k=1):
#     """
#     Assign zip codes to accidents missing them using K-Nearest Neighbors (KNN).

#     Parameters:
#     - with_zip (DataFrame): DataFrame containing accidents with valid zip codes.
#     - without_zip (DataFrame): DataFrame containing accidents without zip codes.
#     - k (int): Number of neighbors to consider for KNN. Default is 1.

#     Returns:
#     - all_accidents (DataFrame): Combined DataFrame with all accidents and assigned zip codes.
#     """
#     # Ensure both DataFrames have the necessary latitude and longitude columns
#     if 'latitude' not in with_zip.columns or 'longitude' not in with_zip.columns:
#         raise ValueError("with_zip dataframe must contain 'latitude' and 'longitude' columns")
#     if 'latitude' not in without_zip.columns or 'longitude' not in without_zip.columns:
#         raise ValueError("without_zip dataframe must contain 'latitude' and 'longitude' columns")

#     # Extract the features (latitude and longitude) and target (zip_code) from the with_zip DataFrame
#     X_with_zip = with_zip[['latitude', 'longitude']]  # Features for training
#     y_with_zip = with_zip['zip_code']  # Target variable (zip codes)

#     # Extract the features (latitude and longitude) from the without_zip DataFrame
#     # Features for prediction
#     X_without_zip = without_zip[['latitude', 'longitude']]

#     # Initialize the KNeighborsClassifier with k neighbors
#     knn = KNeighborsClassifier(n_neighbors=k)

#     # Fit the model using the accidents with zip codes
#     knn.fit(X_with_zip, y_with_zip)

#     # Predict zip codes for accidents without zip codes
#     predicted_zip_codes = knn.predict(X_without_zip)

#     # Assign the predicted zip codes to the without_zip DataFrame
#     without_zip['zip_code'] = predicted_zip_codes

#     # Concatenate the with_zip and modified without_zip DataFrames
#     all_accidents = pd.concat([with_zip, without_zip], ignore_index=True)

#     # Return the concatenated DataFrame containing all accidents
#     return all_accidents

# def split_accidents_by_zipcode(file_name):
#     """
#     Load accident data from a CSV file and split into two DataFrames:
#     one with valid zip codes and one without zip codes.

#     Parameters:
#     - file_name (str): The file path of the CSV file containing accident data.

#     Returns:
#     - with_zip (DataFrame): DataFrame containing accidents with valid zip codes.
#     - without_zip (DataFrame): DataFrame containing accidents with latitude and longitude but no zip code.
#     """
#     # Load the CSV data into a pandas DataFrame
#     df = pd.read_csv(file_name)

#     # Select only the relevant columns and drop rows with NaN values in these columns
#     df = df[['latitude', 'longitude', 'borough', 'zip_code', 'crash_count', 
#              'number_of_persons_injured', 'number_of_persons_killed']]
    
#     # Remove records that do not contain (latitude, longitude) AND zip_code
#     df = df[df['latitude'].notna() & df['longitude'].notna() & df['zip_code'].notna()]

#     # Split the data into two groups: 
#     # 1. with_zip: contains accidents with valid zip codes
#     # 2. without_zip: contains accidents with latitude and longitude but no zip code
#     with_zip = df[df['zip_code'].notna() & (df['zip_code'] != '')]
#     without_zip = df[(df['zip_code'].isna() | (df['zip_code'] == ''))]

#     return with_zip, without_zip


# def assign_zipcodes_knn(with_zip, without_zip, k=1):
#     """
#     Assign zip codes to accidents missing them using K-Nearest Neighbors (KNN).

#     Parameters:
#     - with_zip (DataFrame): DataFrame containing accidents with valid zip codes.
#     - without_zip (DataFrame): DataFrame containing accidents without zip codes.
#     - k (int): Number of neighbors to consider for KNN. Default is 1.

#     Returns:
#     - all_accidents (DataFrame): Combined DataFrame with all accidents and assigned zip codes.
#     """
#     # Ensure both DataFrames have the necessary latitude and longitude columns
#     if 'latitude' not in with_zip.columns or 'longitude' not in with_zip.columns:
#         raise ValueError("with_zip dataframe must contain 'latitude' and 'longitude' columns")
#     if 'latitude' not in without_zip.columns or 'longitude' not in without_zip.columns:
#         raise ValueError("without_zip dataframe must contain 'latitude' and 'longitude' columns")

#     # Extract the features (latitude and longitude) and target (zip_code) from the with_zip DataFrame
#     X_with_zip = with_zip[['latitude', 'longitude']]  # Features for training
#     y_with_zip = with_zip['zip_code']  # Target variable (zip codes)

#     # Extract the features (latitude and longitude) from the without_zip DataFrame
#     # Features for prediction
#     X_without_zip = without_zip[['latitude', 'longitude']]

#     # Check if there are records to predict
#     if X_without_zip.empty:
#         print("No records to predict zip codes for.")
#         without_zip['zip_code'] = None  # Set zip_code to None if no predictions
#     else:
#         # Initialize the KNeighborsClassifier with k neighbors
#         knn = KNeighborsClassifier(n_neighbors=k)

#         # Fit the model using the accidents with zip codes
#         knn.fit(X_with_zip, y_with_zip)

#         # Predict zip codes for accidents without zip codes
#         predicted_zip_codes = knn.predict(X_without_zip)

#         # Assign the predicted zip codes to the without_zip DataFrame
#         without_zip['zip_code'] = predicted_zip_codes

#     # Concatenate the with_zip and modified without_zip DataFrames
#     all_accidents = pd.concat([with_zip, without_zip], ignore_index=True)

#     # Return the concatenated DataFrame containing all accidents
#     return all_accidents


# def count_accidents_per_zipcode(all_accidents):
#     """
#     Count the number of accidents per zip code and calculate the average number of persons injured
#     and/or killed per accident per zip code.

#     Parameters:
#     - all_accidents (DataFrame): A DataFrame containing accident data with zip codes.

#     Returns:
#     - accidents_per_zipcode (DataFrame): A DataFrame with 'zip_code', 'accident_count', and
#       'average_persons_injured_or_killed' columns.
#     - average_accidents_per_zip (float): The average number of accidents per zip code.
#     """
#     # Count the number of accidents per zip code
#     accidents_per_zipcode = all_accidents['zip_code'].value_counts().reset_index()
#     accidents_per_zipcode.columns = ['zip_code', 'accident_count']  # Rename columns for clarity

#     # Calculate the total number of persons injured and killed for each accident
#     all_accidents['total_persons'] = all_accidents['number_of_persons_injured'] + all_accidents['number_of_persons_killed']

#     # Calculate the total persons injured and killed per zip code
#     total_persons_per_zip = all_accidents.groupby('zip_code')['total_persons'].sum().reset_index()

#     # Merge with accidents_per_zipcode
#     accidents_per_zipcode = accidents_per_zipcode.merge(total_persons_per_zip, on='zip_code', how='left').fillna(0)

#     # Calculate the average number of persons injured or killed per accident
#     accidents_per_zipcode['average_persons_injured_or_killed'] = accidents_per_zipcode['total_persons'] / accidents_per_zipcode['accident_count']

#     # Calculate the average number of accidents per zip code
#     average_accidents_per_zip = accidents_per_zipcode['accident_count'].mean()

#     return accidents_per_zipcode[['zip_code', 'accident_count', 'average_persons_injured_or_killed']], average_accidents_per_zip


# def split_zipcodes_into_deciles(accidents_per_zipcode, average_accidents_per_zip):
#     """
#     Split zip codes into deciles based on the number of accidents, and calculate the multiplier relative to the average.

#     Parameters:
#     - accidents_per_zipcode (DataFrame): A DataFrame containing 'zip_code', 'accident_count', and 'average_persons_injured_or_killed'.
#     - average_accidents_per_zip (float): The average number of accidents per zip code.

#     Returns:
#     - decile_table (DataFrame): A DataFrame with 'Decile', 'Zip Code', 'Accident Count', 'Multiplier'.
#     """
#     # Create deciles based on accident counts
#     accidents_per_zipcode['decile'] = pd.qcut(accidents_per_zipcode['accident_count'], q=10, labels=False) + 1

#     # Initialize a list to store the new rows
#     rows = []

#     # Iterate over each decile
#     for decile, group in accidents_per_zipcode.groupby('decile'):
#         for _, row in group.iterrows():
#             # Append each zip code with its accident count and Accident Likelihood Factor
#             # Calculate Accident Likelihood Factor
#             accident_likelihood_factor = row['accident_count'] / average_accidents_per_zip
#             rows.append({
#                 'Decile': decile,
#                 'Zip Code': row['zip_code'],
#                 'Accident Count': row['accident_count'],
#                 # Optionally include this info
#                 'Average Persons Injured/Killed': row['average_persons_injured_or_killed'],
#                 'Accident Likelihood Factor': accident_likelihood_factor,
#             })

#     # Create a new DataFrame from the rows list
#     decile_table = pd.DataFrame(rows)

#     return decile_table


# # def main(file_name, k):
# #     """
# #     Main function to execute the accident data processing pipeline.

# #     Parameters:
# #     - file_name (str): The file path of the CSV file containing accident data.
# #     - k (int): Number of neighbors to use for KNN when assigning missing zip codes.

# #     Returns:
# #     - total_accidents (int): The total number of accidents in the dataset.
# #     - average_accidents_per_zip (float): The average number of accidents per zip code.
# #     - decile_table_sorted (DataFrame): A DataFrame containing 'Decile', 'Zip Code', 'Accident Count', 'Multiplier'.
# #     """
# #     # Set Pandas display options to show all rows and columns
# #     pd.set_option('display.max_rows', None)  # Show all rows
# #     pd.set_option('display.max_columns', None)  # Show all columns

# #     # Split the accidents into those with and without zip codes
# #     with_zip, without_zip = split_accidents_by_zipcode(file_name)

# #     # Assign zip codes to accidents without zip codes
# #     all_accidents = assign_zipcodes_knn(with_zip, without_zip, k=k)

# #     # Count accidents per zip code and calculate the average
# #     accidents_per_zipcode, average_accidents_per_zip = count_accidents_per_zipcode(all_accidents)

# #     # Calculate total number of accidents
# #     total_accidents = all_accidents.shape[0]

# #     # Split zip codes into deciles based on accidents
# #     decile_table = split_zipcodes_into_deciles(accidents_per_zipcode, average_accidents_per_zip)

# #     # Sort the decile table by Accident Count in descending order
# #     decile_table_sorted = decile_table.sort_values(by='Accident Count', ascending=False).reset_index(drop=True)

# #     return total_accidents, average_accidents_per_zip, decile_table_sorted

# def split_accidents_by_zipcode(file_name, borough=None):
#     """
#     Load accident data from a CSV file and split into two DataFrames:
#     one with valid zip codes and one without zip codes.

#     Parameters:
#     - file_name (str): The file path of the CSV file containing accident data.
#     - borough (str): Optional; specify a borough to filter by (e.g., 'Queens'). If None, process citywide.

#     Returns:
#     - with_zip (DataFrame): DataFrame containing accidents with valid zip codes.
#     - without_zip (DataFrame): DataFrame containing accidents with latitude and longitude but no zip code.
#     """
#     # Load the CSV data into a pandas DataFrame
#     df = pd.read_csv(file_name)

#     # Check if borough filtering is needed
#     if borough:
#         df = df[df['borough'].str.lower() == borough.lower()]

#     # Select only the relevant columns and drop rows with NaN values in these columns
#     df = df[['latitude', 'longitude', 'zip_code', 'crash_count', 
#              'number_of_persons_injured', 'number_of_persons_killed']]
    
#     # Remove records that do not contain (latitude, longitude) AND zip_code
#     df = df[df['latitude'].notna() & df['longitude'].notna()]

#     # Split the data into two groups: 
#     # 1. with_zip: contains accidents with valid zip codes
#     # 2. without_zip: contains accidents with latitude and longitude but no zip code
#     with_zip = df[df['zip_code'].notna() & (df['zip_code'] != '')]
#     without_zip = df[(df['zip_code'].isna() | (df['zip_code'] == ''))]

#     return with_zip, without_zip


# def main(file_name, k, borough=None):
#     """
#     Main function to execute the accident data processing pipeline.

#     Parameters:
#     - file_name (str): The file path of the CSV file containing accident data.
#     - k (int): Number of neighbors to use for KNN when assigning missing zip codes.
#     - borough (str): Optional; specify a borough to filter by (e.g., 'Queens'). If None, process citywide.

#     Returns:
#     - total_accidents (int): The total number of accidents in the dataset.
#     - average_accidents_per_zip (float): The average number of accidents per zip code.
#     - decile_table_sorted (DataFrame): A DataFrame containing 'Decile', 'Zip Code', 'Accident Count', 'Multiplier'.
#     """
#     # Set Pandas display options to show all rows and columns
#     pd.set_option('display.max_rows', None)  # Show all rows
#     pd.set_option('display.max_columns', None)  # Show all columns

#     # Split the accidents into those with and without zip codes
#     with_zip, without_zip = split_accidents_by_zipcode(file_name, borough)

#     # Assign zip codes to accidents without zip codes
#     all_accidents = assign_zipcodes_knn(with_zip, without_zip, k=k)

#     # Count accidents per zip code and calculate the average
#     accidents_per_zipcode, average_accidents_per_zip = count_accidents_per_zipcode(all_accidents)

#     # Calculate total number of accidents
#     total_accidents = all_accidents.shape[0]

#     # Split zip codes into deciles based on accidents
#     decile_table = split_zipcodes_into_deciles(accidents_per_zipcode, average_accidents_per_zip)

#     # Sort the decile table by Accident Count in descending order
#     decile_table_sorted = decile_table.sort_values(by='Accident Count', ascending=False).reset_index(drop=True)

#     return total_accidents, average_accidents_per_zip, decile_table_sorted

