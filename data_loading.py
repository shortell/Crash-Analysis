
"""
Since there are 3 (longitude and latitude are useless if one value or the other is missing so they are counted at 1 to reduce combination complexity) 
types of locational data and each value can either be present or missing, there are 8 possible combinations. 2^3

Here is the following truth table for the 8 possible combinations:

Zip code (present), Lat/Long (present), Borough (present)
Zip code (present), Lat/Long (present), Borough (missing) 
Zip code (present), Lat/Long (missing), Borough (present) 
Zip code (present), Lat/Long (missing), Borough (missing) 
Zip code (missing), Lat/Long (present), Borough (present) 
Zip code (missing), Lat/Long (present), Borough (missing) 
Zip code (missing), Lat/Long (missing), Borough (present) 
Zip code (missing), Lat/Long (missing), Borough (missing)
"""


def get_zip_lat_long_borough(df):  # no filling needed
    """
    Returns records where zip_code, latitude, longitude, and borough are all present.
    Zip code (present), Lat/Long (present), Borough (present)
    """
    return df[df["zip_code"].notna() & df["latitude"].notna() & df["longitude"].notna() & df["borough"].notna()]


def get_zip_lat_long_no_borough(df):  # can fill borough with zip code
    """
    Returns records where zip_code, latitude, and longitude are present, but borough is missing.
    Zip code (present), Lat/Long (present), Borough (missing)
    """
    return df[df["zip_code"].notna() & df["latitude"].notna() & df["longitude"].notna() & df["borough"].isna()]


def get_zip_no_lat_long_borough(df):  # no filling needed
    """
    Returns records where zip_code is present, latitude and longitude are missing, and borough is present.
    Zip code (present), Lat/Long (missing), Borough (present)
    """
    return df[df["zip_code"].notna() & df["latitude"].isna() & df["longitude"].isna() & df["borough"].notna()]


# zip code can determine borough # usually has 0 records
def get_zip_no_lat_long_no_borough(df):
    """
    Returns records where zip_code is present, latitude and longitude are missing, and borough is missing.
    Zip code (present), Lat/Long (missing), Borough (missing)
    """
    return df[df["zip_code"].notna() & df["latitude"].isna() & df["longitude"].isna() & df["borough"].isna()]


def get_no_zip_lat_long_borough(df):  # lat/long can determine zip code
    """
    Returns records where zip_code is missing, latitude and longitude are present, and borough is present.
    Zip code (missing), Lat/Long (present), Borough (present)
    """
    return df[df["zip_code"].isna() & df["latitude"].notna() & df["longitude"].notna() & df["borough"].notna()]


# lat/long can determine zip code, zip code can determine borough
def get_no_zip_lat_long_no_borough(df):
    """
    Returns records where zip_code is missing, latitude and longitude are present, and borough is missing.
    Zip code (missing), Lat/Long (present), Borough (missing)
    """
    return df[df["zip_code"].isna() & df["latitude"].notna() & df["longitude"].notna() & df["borough"].isna()]


# usually has 0 records # can not be filled
def get_no_zip_no_lat_long_borough(df):
    """
    Returns records where zip_code and latitude/longitude are missing, and borough is present.
    Zip code (missing), Lat/Long (missing), Borough (present)
    """
    return df[df["zip_code"].isna() & df["latitude"].isna() & df["longitude"].isna() & df["borough"].notna()]


def get_no_zip_no_lat_long_no_borough(df):  # can not be filled
    """
    Returns records where zip_code and latitude/longitude are missing, and borough is missing.
    Zip code (missing), Lat/Long (missing), Borough (missing)
    """
    return df[df["zip_code"].isna() & df["latitude"].isna() & df["longitude"].isna() & df["borough"].isna()]


def get_null_crash_count(df):  # usually has 0 records
    return df[df["crash_count"].isna()]
