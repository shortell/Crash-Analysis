from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from main_pipeline import main
from zip_code_search import get_all_unique_zip_codes, search_zip_code
import os
import glob
import pandas as pd


app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Set the base directory where borough datasets are stored

# List of available borough directories
DIRECTORIES = ['brooklyn', 'citywide', 'manhattan',
               'queens', 'staten_island', 'the_bronx']

# Allowable file extensions for uploads
ALLOWED_EXTENSIONS = {'csv'}

K = 3  # Number of neighbors to check for accidents with no zip code

# Define required headers
REQUIRED_HEADERS = [
    'the_geom', 'cartodb_id', 'socrata_id', 'on_street_name', 'cross_street_name',
    'date_time', 'latitude', 'longitude', 'borough', 'zip_code', 'crash_count',
    'number_of_cyclist_injured', 'number_of_cyclist_killed', 'number_of_motorist_injured',
    'number_of_motorist_killed', 'number_of_pedestrian_injured', 'number_of_pedestrian_killed',
    'number_of_persons_injured', 'number_of_persons_killed', 'contributing_factors', 'vehicle_types'
]


# Cache to store computed tables
cached_tables = {}


def allowed_file(filename):
    """
    Check if the uploaded file is allowed. 
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """ Display the available boroughs and datasets. """
    return render_template('index.html')


@app.route('/view/<area>')
def view_data(area):
    """
    Display the selected area (borough or citywide) and dataset.
    """
    # Check if the table for this area (borough or citywide) is already cached
    if area not in cached_tables:
        # Call main to compute the table if not cached
        total_accidents, average_accidents_per_zip, decile_table = main(
            area, k=K)

        # Cache the computed values
        cached_tables[area] = {
            'total_accidents': total_accidents,
            'average_accidents_per_zip': average_accidents_per_zip,
            'decile_table': decile_table
        }

    # Retrieve cached values
    cached_data = cached_tables[area]
    total_accidents = cached_data['total_accidents']
    average_accidents_per_zip = cached_data['average_accidents_per_zip']
    decile_table = cached_data['decile_table']

    # Get sort parameters from query string
    sort_by = request.args.get('sort_by', 'Accident Count')
    order = request.args.get('order', 'desc')  # Default to descending order

    ascending = True if order == 'asc' else False
    decile_table = decile_table.sort_values(by=sort_by, ascending=ascending)

    # Render the unified template
    return render_template(
        'view_area.html',
        area=area,
        total_accidents=total_accidents,
        average_accidents_per_zip=average_accidents_per_zip,
        decile_table=decile_table
    )


@app.route('/heatmap/<area>')
def view_heatmap(area):
    """
    Display the heatmap for the selected area (borough or citywide).
    """
    return render_template('view_map.html', area=area)


def delete_files(path_pattern):
    """Delete all files matching the given path pattern."""
    for filepath in glob.glob(path_pattern):
        try:
            os.remove(filepath)
        except Exception as e:
            print(f"Error deleting {filepath}: {e}")


def check_file_in_request():
    if 'file' not in request.files:
        flash('No file part')
        return False
    return True

# Helper function to check if a file is selected


def check_file_selected(file):
    if file.filename == '':
        flash('No selected file')
        return False
    return True

# Helper function to check if the file is a CSV and has required headers


def check_csv_headers(file):
    try:
        df = pd.read_csv(file)
        missing_headers = [
            header for header in REQUIRED_HEADERS if header not in df.columns]

        if missing_headers:
            flash(f'Missing required headers: {", ".join(missing_headers)}')
            return False

        # Reset file pointer to the beginning after reading
        file.seek(0)
        return True

    except Exception as e:
        flash(f'Error reading CSV file: {e}')
        return False

# Helper function to delete cached data, files, and heatmaps for the area


def clear_cached_data(area):
    cached_tables.pop(area, None)
    delete_files(f'borough_assets/{area}/unprocessed_data/*.csv')
    delete_files(f'borough_assets/{area}/processed_data/*.csv')
    heatmap_path = f'static/{area}/interactive_heatmap.html'
    if os.path.exists(heatmap_path):
        os.remove(heatmap_path)


@app.route('/upload/<area>', methods=['POST'])
def upload_csv(area):
    # Check if file is in request
    if not check_file_in_request():
        return redirect(url_for('view_data', area=area))

    file = request.files['file']

    # Check if file is selected
    if not check_file_selected(file):
        return redirect(url_for('view_data', area=area))

    # Check if the file is a CSV with the required headers
    if file and file.filename.endswith('.csv'):
        if not check_csv_headers(file):
            return redirect(url_for('view_data', area=area))

        # Clear cached data and old files only after all checks have passed
        clear_cached_data(area)

        # Save the file
        save_path = os.path.join(
            f'borough_assets/{area}/unprocessed_data', file.filename)
        file.save(save_path)
        flash('File successfully uploaded')

    else:
        flash('Invalid file type. Only CSV files are allowed.')
        return redirect(url_for('view_data', area=area))

    return redirect(url_for('view_data', area=area))


@app.route('/autocomplete_zipcode')
def autocomplete_zipcode():
    query = request.args.get('query', '')
    zipcodes = get_all_unique_zip_codes()  # Fetch all unique zip codes
    matches = [zipcode for zipcode in zipcodes if str(
        zipcode).startswith(query)]
    return jsonify(matches)


@app.route('/search', methods=['GET'])
def search_zip():
    # Check if `zipcode` parameter is provided in the request
    zip_code = request.args.get('zipcode')
    if not zip_code:
        # Redirect to index if no zip code is provided
        return redirect(url_for('index'))

    # Try converting `zip_code` to an integer and handle any conversion errors
    try:
        zip_code = int(zip_code)
    except ValueError:
        # Redirect to index if zip code is not a valid integer
        return redirect(url_for('index'))

    # Validate the zip code by checking if it exists in the unique zip codes
    valid_zip_codes = get_all_unique_zip_codes()
    if zip_code not in valid_zip_codes:
        # Redirect to index if zip code is not found in the dataset
        return redirect(url_for('index'))

    # Call the search_zip_code function to retrieve data
    result = search_zip_code(zip_code)

    # Check if result is None or citywide_record is missing
    if result is None or result.get("citywide_record") is None:
        # Redirect to index if no data found for the zip code
        return redirect(url_for('index'))

    # Extract borough name safely from the citywide record
    borough = result["citywide_record"].get("borough", "Unknown")

    # Check if borough_record exists; if not, redirect back to index
    if result.get("borough_record") is None:
        return redirect(url_for('index'))

    # If all data is valid, render the template with all values
    return render_template(
        'view_search.html',
        zip_code=zip_code,
        citywide_record=result["citywide_record"],
        borough_record=result["borough_record"],
        borough_highest_rank=result["borough_record"].get("highest_rank"),
        borough_name=borough,
        error=None
    )


if __name__ == '__main__':
    app.run(debug=True)
