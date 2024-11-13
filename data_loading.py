import os
import glob
import pandas as pd
from settings import BASE_DIR, COLUMN_MAPPING


def get_latest_csv(borough: str) -> str:
    """
    Get the CSV file from the specified borough's unprocessed data directory.
    """
    borough_dir = os.path.join(BASE_DIR, borough, 'unprocessed_data')
    if not os.path.isdir(borough_dir):
        raise FileNotFoundError(f"The directory for {borough} does not exist.")

    csv_files = glob.glob(os.path.join(borough_dir, "*.csv"))
    if not csv_files:
        raise FileNotFoundError(
            f"No CSV file found in the directory for {borough}.")

    return csv_files[0]


def load_accident_data(csv_filename):
    """
    Load the CSV file into a DataFrame and standardize column names.
    """
    df = pd.read_csv(csv_filename)
    df.rename(columns=COLUMN_MAPPING, inplace=True)
    return df
