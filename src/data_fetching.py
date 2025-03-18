import requests
from datetime import datetime

# the earliest date possible is August 2011
EARLIEST_DATE = datetime(2011, 8, 1)


def get_current_month():
    """
    Returns the current month as an integer (1-12).
    """
    return datetime.now().month


def get_current_year():
    """
    Returns the current year as an integer (YYYY).
    """
    return datetime.now().year


def get_latest_date():
    """
    Returns the latest end date that can be selected by the user.
    """
    current_month = get_current_month()
    current_year = get_current_year()
    end_date = datetime(current_year, current_month, 1)
    return end_date


def get_valid_years():
    """
    returns an int list starting from the current year all the way to 2011
    as that is the earliest year available from https://crashmapper.org/
    """
    current_year = get_current_year()
    return list(range(current_year, EARLIEST_DATE.year - 1, -1))


def is_start_date_before_end_date(start_month, start_year, end_month, end_year):
    """
    Check if the start date is before the end date.
    
    Parameters:
    start_month (int): The starting month
    start_year (int): The starting year
    end_month (int): The ending month
    end_year (int): The ending year
    
    Returns:
    bool: True if the start date is before the end date, False otherwise
    """
    start_date = datetime(start_year, start_month, 1)
    end_date = datetime(end_year, end_month, 1)
    return start_date <= end_date


def is_date_in_valid_range(month, year):
    """
    Check if the date is within the valid range.

    Parameters:
    month (int): The month
    year (int): The year

    Returns:
    bool: True if the date is within the valid range, False otherwise
    """
    latest_date = get_latest_date()
    entered_date = datetime(year, month, 1)
    return EARLIEST_DATE <= entered_date <= latest_date


def is_date_range_valid(start_month, start_year, end_month, end_year):
    """
    Check if the date range is valid.
    
    Parameters:
    start_month (int): The starting month
    start_year (int): The starting year
    end_month (int): The ending month
    end_year (int): The ending year
    
    Returns:
    bool: True if the date range is valid, False otherwise
    """
    if is_date_in_valid_range(start_month, start_year) and is_date_in_valid_range(end_month, end_year):
        return is_start_date_before_end_date(start_month, start_year, end_month, end_year)
    return False


def fetch_crash_data(start_month, start_year, end_month, end_year):
    """
    Fetch crash data from the API for a given date range.
    :param start_month: Start month (1-12)
    :param start_year: Start year (YYYY)
    :param end_month: End month (1-12)
    :param end_year: End year (YYYY)
    :return: List of crash records
    """
    url = ("https://chekpeds.carto.com/api/v2/sql?q="
           "SELECT c.zip_code, c.borough, c.crash_count, c.latitude, c.longitude "
           "FROM crashes_all_prod c "
           f"WHERE (year::text || LPAD(month::text, 2, '0') >= '{start_year}{str(start_month).zfill(2)}' "
           f"AND year::text || LPAD(month::text, 2, '0') <= '{end_year}{str(end_month).zfill(2)}')")

    response = requests.get(url)
    if response.status_code == 200:
        data = response.json().get('rows', [])
        if data == []:
            return None
        for i, record in enumerate(data):
            record['id'] = i  # Assign incremental ID starting from 0
        return data
    else:
        print(f"Failed to fetch data. Status code: {response.status_code}")
        return None
