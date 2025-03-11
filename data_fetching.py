import requests
import csv
import pandas as pd

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
           "SELECT c.cartodb_id, c.socrata_id, c.the_geom, c.on_street_name, "
           "c.cross_street_name, c.date_val AS date_time, c.latitude, c.longitude, "
           "c.borough, c.zip_code, c.crash_count, c.number_of_cyclist_injured, "
           "c.number_of_cyclist_killed, c.number_of_motorist_injured, "
           "c.number_of_motorist_killed, c.number_of_pedestrian_injured, "
           "c.number_of_pedestrian_killed, c.number_of_persons_injured, "
           "c.number_of_persons_killed, "
           "array_to_string(c.contributing_factor, ',') as contributing_factors, "
           "array_to_string(c.vehicle_type, ',') as vehicle_types "
           "FROM crashes_all_prod c "
           f"WHERE (year::text || LPAD(month::text, 2, '0') >= '{start_year}{str(start_month).zfill(2)}' "
           f"AND year::text || LPAD(month::text, 2, '0') <= '{end_year}{str(end_month).zfill(2)}')")
    
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('rows', [])
    else:
        print(f"Failed to fetch data. Status code: {response.status_code}")
        return []
    
def process_crash_data(rows):
    """Process raw crash data into a structured format."""
    return [
        {
            "latitude": row.get("latitude"),
            "longitude": row.get("longitude"),
            "borough": row.get("borough"),
            "zip_code": row.get("zip_code"),
            "crash_count": row.get("crash_count"),
        }
        for row in rows
    ]

def save_to_csv(data, filename):
    """Save processed data to a CSV file."""
    csv_columns = [
        "latitude", "longitude", "borough", "zip_code", "crash_count",
        "cyclist_injured", "cyclist_killed", "motorist_injured", "motorist_killed",
        "pedestrian_injured", "pedestrian_killed", "total_injured", "total_killed",
        "contributing_factors", "vehicle_types"
    ]
    try:
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=csv_columns)
            writer.writeheader()
            writer.writerows(data)
        print(f"Data saved successfully to {filename}")
    except Exception as e:
        print(f"Error saving CSV: {e}")

def main(start_month, start_year, end_month, end_year):
    """Pipeline to fetch, process, and save crash data."""
    raw_data = fetch_crash_data(start_month, start_year, end_month, end_year)
    processed_data = process_crash_data(raw_data)
    # create a file name based off the start month and year and end month and year
    output_file = f"crash_data_{start_month}_{start_year}-{end_month}_{end_year}.csv"
    save_to_csv(processed_data, output_file)