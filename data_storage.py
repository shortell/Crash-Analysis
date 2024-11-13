import os
import pandas as pd
from settings import BASE_DIR, COLUMN_MAPPING


def save_master_table(df, borough):
    """
    Sort the DataFrame by Accident Count in descending order and save it to a CSV file in the processed_data directory.
    """
    processed_dir = os.path.join(BASE_DIR, borough, 'processed_data')
    # Ensure the processed_data directory exists
    os.makedirs(processed_dir, exist_ok=True)

    # Sort the DataFrame by Accident Count in descending order
    df = df.sort_values(by=COLUMN_MAPPING['accident_count'], ascending=False)

    # Save the sorted DataFrame to a CSV file
    df.to_csv(os.path.join(processed_dir, f"{borough}_master_table.csv"), index=False)



def load_master_table(borough):
    """
    Load the master table from the processed_data directory if it exists.
    """
    processed_dir = os.path.join(BASE_DIR, borough, 'processed_data')
    master_file = os.path.join(processed_dir, f"{borough}_master_table.csv")
    if os.path.exists(master_file):
        return pd.read_csv(master_file)
    return None
