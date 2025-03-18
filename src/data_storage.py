import os
import pandas as pd

# data will be stored in data/nyc_csv

DATA_DIR = os.path.join(os.path.dirname(__file__), '../data/nyc_csv')

COLUMNS = ['zip_code', 'borough', 'total_crashes']


def create_file_name(start_month, start_year, end_month, end_year):
    """
    Create a file name based on the start and end dates.
    """
    return f"accidents_{start_month}_{start_year}-{end_month}_{end_year}.csv"

def fetch_csv_file(file_name: str) -> pd.DataFrame:
    """
    Fetch the CSV file with the given filename from the DATA_DIR.
    
    Parameters:
    file_name (str): The name of the file to fetch.
    
    Returns:
    pd.DataFrame: The DataFrame containing the CSV data, or None if the file is not found.
    """
    file_path = os.path.join(DATA_DIR, file_name)
    
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    else:
        return None
    
def delete_all_files_in_data_dir():
    """
    Delete all files in the DATA_DIR.
    """
    for file_name in os.listdir(DATA_DIR):
        file_path = os.path.join(DATA_DIR, file_name)
        if os.path.isfile(file_path):
            os.remove(file_path)

def save_dataframe_to_csv(df, file_name):
    """
    Save a DataFrame to a CSV file in the DATA_DIR with specified COLUMNS.
    
    Parameters:
    df (pd.DataFrame): The DataFrame to save.
    file_name (str): The name of the file to save the DataFrame to.
    """
    # Ensure the DataFrame contains only the specified columns
    df_to_save = df[COLUMNS]
    
    # Create the full file path
    file_path = os.path.join(DATA_DIR, file_name)
    
    # Save the DataFrame to a CSV file
    df_to_save.to_csv(file_path, index=False)



