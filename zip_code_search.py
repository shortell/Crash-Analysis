from data_storage import load_master_table
from settings import REVERSED_BOROUGH_MAPPING
import pandas as pd


def get_all_unique_zip_codes():
    """
    Get all unique zip codes from the citywide dataset.
    """
    citywide_df = load_master_table('citywide')
    return citywide_df['Zip Code'].unique()


# def search_zip_code(zip_code):
#     """
#     Searches for two records: one in the citywide dataset and one in the borough the zip code belongs to.
#     Also retrieves the highest rank value from each dataset as a comparison.
#     """
#     # Load the citywide dataset and search for the record with the given zip code
#     citywide_df = load_master_table('citywide')
#     citywide_record = citywide_df[citywide_df['Zip Code'] == zip_code]

#     # Get the highest rank value in the citywide dataset
#     citywide_highest_rank = citywide_df['Rank'].max()

#     # Find the borough based on the citywide record for the given zip code
#     borough = citywide_record['Borough'].values[0]
#     borough = REVERSED_BOROUGH_MAPPING[borough]

#     # Load the borough dataset and search for the record with the given zip code
#     borough_df = load_master_table(borough)
#     borough_record = borough_df[borough_df['Zip Code'] == zip_code]

#     # Get the highest rank value in the borough dataset
#     borough_highest_rank = borough_df['Rank'].max()

#     # return citywide_record, citywide_highest_rank, borough_record, borough_highest_rank
#     return citywide_record, citywide_highest_rank, borough_record, borough_highest_rank

# def search_zip_code(zip_code):
#     citywide_df = load_master_table('citywide')
#     citywide_record = citywide_df[citywide_df['Zip Code'] == zip_code]

#     if citywide_record.empty:
#         return None, None, None, None

#     # Extract values as plain data types
#     citywide_highest_rank = int(citywide_df['Rank'].max())
#     accident_count = int(citywide_record['Accident Count'].values[0])
#     citywide_rank = int(citywide_record['Rank'].values[0])
#     citywide_decile = int(citywide_record['Decile'].values[0])
#     citywide_accident_likelihood = float(citywide_record['Accident Likelihood'].values[0])

#     borough = citywide_record['Borough'].values[0]
#     borough = REVERSED_BOROUGH_MAPPING[borough]

#     borough_df = load_master_table(borough)
#     borough_record = borough_df[borough_df['Zip Code'] == zip_code]

#     if borough_record.empty:
#         return {
#             "citywide_record": {
#                 "rank": citywide_rank,
#                 "highest_rank": citywide_highest_rank,
#                 "decile": citywide_decile,
#                 "accident_likelihood": citywide_accident_likelihood,
#                 "accident_count": accident_count
#             },
#             "borough_record": None,
#             "borough_highest_rank": None
#         }

#     borough_highest_rank = int(borough_df['Rank'].max())
#     borough_rank = int(borough_record['Rank'].values[0])
#     borough_decile = int(borough_record['Decile'].values[0])
#     borough_accident_likelihood = float(borough_record['Accident Likelihood'].values[0])

#     return {
#         "citywide_record": {
#             "rank": citywide_rank,
#             "highest_rank": citywide_highest_rank,
#             "decile": citywide_decile,
#             "accident_likelihood": citywide_accident_likelihood,
#             "accident_count": accident_count
#         },
#         "borough_record": {
#             "rank": borough_rank,
#             "highest_rank": borough_highest_rank,
#             "decile": borough_decile,
#             "accident_likelihood": borough_accident_likelihood
#         }
#     }

def search_zip_code(zip_code):
    citywide_df = load_master_table('citywide')
    citywide_record = citywide_df[citywide_df['Zip Code'] == zip_code]

    if citywide_record.empty:
        return None, None, None, None

    # Extract values as plain data types
    citywide_highest_rank = int(citywide_df['Rank'].max())
    accident_count = int(citywide_record['Accident Count'].values[0])
    citywide_rank = int(citywide_record['Rank'].values[0])
    citywide_decile = int(citywide_record['Decile'].values[0])
    citywide_accident_likelihood = float(citywide_record['Accident Likelihood'].values[0])

    # Retrieve and map the borough for the zip code
    borough = citywide_record['Borough'].values[0]
    borough_name = REVERSED_BOROUGH_MAPPING[borough]  # Assuming REVERSED_BOROUGH_MAPPING is defined

    borough_df = load_master_table(borough_name)
    borough_record = borough_df[borough_df['Zip Code'] == zip_code]

    if borough_record.empty:
        return {
            "citywide_record": {
                "rank": citywide_rank,
                "highest_rank": citywide_highest_rank,
                "decile": citywide_decile,
                "accident_likelihood": citywide_accident_likelihood,
                "accident_count": accident_count,
                "borough": borough_name  # Include borough name in the citywide record
            },
            "borough_record": None,
            "borough_highest_rank": None
        }

    borough_highest_rank = int(borough_df['Rank'].max())
    borough_rank = int(borough_record['Rank'].values[0])
    borough_decile = int(borough_record['Decile'].values[0])
    borough_accident_likelihood = float(borough_record['Accident Likelihood'].values[0])

    return {
        "citywide_record": {
            "rank": citywide_rank,
            "highest_rank": citywide_highest_rank,
            "decile": citywide_decile,
            "accident_likelihood": citywide_accident_likelihood,
            "accident_count": accident_count,
            "borough": borough_name  # Include borough name here
        },
        "borough_record": {
            "rank": borough_rank,
            "highest_rank": borough_highest_rank,
            "decile": borough_decile,
            "accident_likelihood": borough_accident_likelihood
        }
    }




# a, b, c, d = search_zip_code(11103)
# print(f'Citywide record: {a}')
# print(f'Citywide highest rank: {b}')
# print(f'Borough record: {c}')
# print(f'Borough highest rank: {d}')

def count_duplicate_zip_codes(file_path):
    # Load the CSV file into a DataFrame
    df = pd.read_csv(file_path)
    
    # Check for duplicate zip codes
    duplicate_zipcodes = df[df.duplicated(subset=['Zip Code'], keep=False)]
    
    # Get unique duplicate zip codes and count them
    unique_duplicate_zipcodes = duplicate_zipcodes['Zip Code'].unique()
    num_unique_duplicates = len(unique_duplicate_zipcodes)
    
    return num_unique_duplicates, unique_duplicate_zipcodes


print(count_duplicate_zip_codes('borough_assets/manhattan/processed_data/manhattan_master_table.csv'))
