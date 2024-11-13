import os

BASE_DIR = "borough_assets"
AREA_DIRECTORIES = ['brooklyn', 'citywide', 'manhattan', 'queens', 'staten_island', 'the_bronx']
DATA_DIRECTORIES = ['unprocessed_data', 'processed_data', 'heatmap']
SHAPEFILE_PATH = "data/nyc_shapefile/nyc_zip_code_map.shp"

COLUMN_MAPPING = {
    'zip_code': 'Zip Code',
    'borough': 'Borough',
    'accident_count': 'Accident Count',
    'latitude': 'Latitude',
    'longitude': 'Longitude',
    'crash_count': 'Crash Count'
}

BOROUGH_MAPPING = {
    'brooklyn': 'Brooklyn',
    'manhattan': 'Manhattan',
    'queens': 'Queens',
    'staten_island': 'Staten Island',
    'the_bronx': 'Bronx',
    'citywide': 'Citywide'
}

REVERSED_BOROUGH_MAPPING = {v: k for k, v in BOROUGH_MAPPING.items()}
