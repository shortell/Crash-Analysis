import requests


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
        for i, record in enumerate(data):
            record['id'] = i  # Assign incremental ID starting from 0
        return data
    else:
        print(f"Failed to fetch data. Status code: {response.status_code}")
        return []
