from main_pipeline import process_and_format_crash_data


def get_all_unique_zip_codes(df):
    """
    Get all unique zip codes from the citywide dataset.
    """
    return df['zip_code'].unique()


def search_zip_code(df, zip_code):
    _, _, citywide_df = process_and_format_crash_data(df)
    citywide_record = citywide_df[citywide_df['Zip Code'] == zip_code]

    if citywide_record.empty:
        return None, None, None, None

    # Extract values as plain data types
    citywide_highest_rank = int(citywide_df['Rank'].max())
    accident_count = int(citywide_record['Accident Count'].values[0])
    citywide_rank = int(citywide_record['Rank'].values[0])
    citywide_decile = int(citywide_record['Decile'].values[0])
    citywide_accident_likelihood = float(
        citywide_record['Accident Likelihood'].values[0])

    # Retrieve and map the borough for the zip code
    borough = citywide_record['Borough'].values[0]
    # Assuming REVERSED_BOROUGH_MAPPING is defined

    _, _, borough_df = process_and_format_crash_data(df, borough)

    borough_record = borough_df[borough_df['Zip Code'] == zip_code]

    borough_highest_rank = int(borough_df['Rank'].max())
    borough_rank = int(borough_record['Rank'].values[0])
    borough_decile = int(borough_record['Decile'].values[0])
    borough_accident_likelihood = float(
        borough_record['Accident Likelihood'].values[0])

    return {
        "citywide_record": {
            "rank": citywide_rank,
            "highest_rank": citywide_highest_rank,
            "decile": citywide_decile,
            "accident_likelihood": citywide_accident_likelihood,
            "accident_count": accident_count,
            "borough": borough  # Include borough name here
        },
        "borough_record": {
            "rank": borough_rank,
            "highest_rank": borough_highest_rank,
            "decile": borough_decile,
            "accident_likelihood": borough_accident_likelihood
        }
    }
