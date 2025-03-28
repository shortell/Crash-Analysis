import pandas as pd


def filter_by_borough(df, borough_name):
    """
    Filters the DataFrame to include only rows from the specified borough.

    :param df: DataFrame with 'borough' column
    :param borough_name: Name of the borough to filter by ['Citywide', Brooklyn', 'Manhattan', 'Queens', 'Staten Island', 'The Bronx']
    :return: Filtered DataFrame with only rows from the specified borough
    """
    if borough_name == 'Citywide' or borough_name == None:
        return df
    filtered_df = df[df['borough'] == borough_name]
    return filtered_df


def get_total_crashes(df):
    """
    using the returned DataFrame from aggregate_crashes_by_zip, calculate the total number of crashes in the DataFrame.

    Parameters:
    df (pd.DataFrame): The DataFrame returned from aggregate_crashes_by_zip
    
    Returns:
    int: The total number of crashes in the DataFrame
    """
    total = df['total_crashes'].sum()
    return total


def get_average_crashes_per_zip(df):
    """
    using the returned DataFrame from aggregate_crashes_by_zip, calculate the average number of crashes per zip code. rounded to 2 decimal places.
    
    Parameters:
    df (pd.DataFrame): The DataFrame returned from aggregate_crashes_by_zip

    Returns:
    float: The average number of crashes per zip code in the DataFrame rounded to 2 decimal places
    """
    average = df['total_crashes'].mean()
    return round(average, 2)


def rank_by_crash_count(df):
    """
    Rank zip codes by crash count in descending order.

    Parameters:
    df (pd.DataFrame): The DataFrame returned from aggregate_crashes_by_zip

    Returns:
    pd.DataFrame: The DataFrame with an additional 'rank' column that ranks zip codes by crash count in descending order
    """
    df = df.copy()  # Create a copy to avoid SettingWithCopyWarning
    df['rank'] = df['total_crashes'].rank(
        method='first', ascending=False).astype(int)
    return df


def create_crash_likelihood_column(df, average_crashes_per_zip):
    """
    Create a new column 'Crash Likelihood' that calculates the likelihood of a crash in a zip code as a multiple of the average crashes per zip code.
    
    
    Parameters:
    df (pd.DataFrame): The DataFrame returned from aggregate_crashes_by_zip
    average_crashes_per_zip (float): The average number of crashes per zip code in the DataFrame
    
    Returns:
    pd.DataFrame: The DataFrame with an additional 'crash_likelihood' column that calculates the likelihood of a crash in a zip code as a quotient of the total crashes in the zip code and the average crashes per zip code
    """
    df = df.copy()  # Create a copy to avoid SettingWithCopyWarning
    df['crash_likelihood'] = round(
        (df['total_crashes'] / average_crashes_per_zip), 2)
    return df


def group_into_deciles(df):
    """
    Groups zip codes into 10 groups based on rank each group having a roughly equal number of zip codes.

    Deciles should start from 1 to 10.

    Parameters:
    df (pd.DataFrame): The DataFrame returned from aggregate_crashes_by_zip

    Returns:
    pd.DataFrame: The DataFrame with an additional 'decile' column that groups zip codes into 10 groups based on rank
    """
    df['decile'] = pd.qcut(df['rank'], 10, labels=False) + 1
    return df


def rename_columns(df):
    """
    Rename columns to match the expected output format.

    Parameters:
    df (pd.DataFrame): The DataFrame returned from aggregate_crashes_by_zip

    Returns:
    pd.DataFrame: The DataFrame with renamed columns
    """
    df = df.rename(columns={
        'zip_code': 'Zip Code',
        'borough': 'Borough',
        'total_crashes': 'Accident Count',
        'rank': 'Rank',
        'crash_likelihood': 'Accident Likelihood',
        'decile': 'Decile'
    })
    return df


def rename_bronx_to_the_bronx(df):
    """
    Rename 'Bronx' to 'The Bronx' in the 'borough' column.

    Parameters:
    df (pd.DataFrame): The DataFrame returned from fetch_crash_data

    Returns:
    pd.DataFrame: The DataFrame with 'Bronx' renamed to 'The Bronx' in the 'borough' column
    """
    df['borough'] = df['borough'].replace('Bronx', 'The Bronx')
    return df
