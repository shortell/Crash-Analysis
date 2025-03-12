import time

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from main_pipeline import fetch_and_aggregate_crash_data, process_and_format_crash_data
from zip_code_search import get_all_unique_zip_codes, search_zip_code
from heatmap_generation import create_interactive_heatmap


app = Flask(__name__)
app.secret_key = 'supersecretkey'

K = 5  # Number of neighbors to check for accidents with no zip code


cached_raw_data = None

cached_formatted_data = None


def set_cached_raw_data(data):
    global cached_raw_data
    cached_raw_data = data


def set_cached_formatted_data(data):
    global cached_formatted_data
    cached_formatted_data = data


def get_default_start_end_dates():
    """Get the default start and end dates for the dataset."""
    start_year = int(time.strftime('%Y'))
    start_month = int(time.strftime('%m'))

    # start month should be 2 months before the current month
    if start_month == 1:
        start_month = 11
        start_year = start_year - 1
    elif start_month == 2:
        start_month = 12
        start_year = start_year - 1
    else:
        start_month = start_month - 2

    end_month = start_month
    end_year = start_year

    return start_month, start_year, end_month, end_year


def download_default_data():
    start_month, start_year, end_month, end_year = get_default_start_end_dates()
    agg_df = fetch_and_aggregate_crash_data(
        start_month, start_year, end_month, end_year, K)
    if agg_df is not None:
        set_cached_raw_data(agg_df)


@app.route('/')
def index():
    """ Display the available boroughs and datasets. """
    if cached_raw_data is None:
        download_default_data()
    return render_template('index.html')


@app.route('/view/<area>')
def view_data(area):
    """
    Display the selected area (borough or citywide) and dataset.
    """
    if cached_raw_data is None:
        download_default_data()
    total_crashes, average_crashes_per_zip, formatted_df_by_area = process_and_format_crash_data(
        cached_raw_data, area)

    set_cached_formatted_data(formatted_df_by_area)
    return render_template(
        'view_area.html',
        area=area,
        total_accidents=total_crashes,
        average_accidents_per_zip=average_crashes_per_zip,
        decile_table=formatted_df_by_area
    )


@app.route('/view_map/<area>')
def view_map(area):
    # Create the heatmap using your function.
    heatmap = create_interactive_heatmap(area, cached_formatted_data)
    if not heatmap:
        flash("Error generating heatmap")
        return redirect(url_for("index"))

    heatmap_html = heatmap.get_root().render()  # Render the heatmap to HTML.
    if not heatmap_html.strip():  # Check if the HTML content is empty.
        flash("Heatmap HTML is empty")
        return redirect(url_for("index"))

    return render_template('view_map.html', area=area, heatmap_html=heatmap_html)


@app.route('/download', methods=['GET'])
def download_crash_data():
    # Retrieve required parameters
    start_month = request.args.get('start_month')
    start_year = request.args.get('start_year')
    end_month = request.args.get('end_month')
    end_year = request.args.get('end_year')

    # Check for missing parameters
    missing = [
        param for param, val in [
            ('start_month', start_month),
            ('start_year', start_year),
            ('end_month', end_month),
            ('end_year', end_year)
        ] if not val
    ]
    if missing:
        return jsonify({'error': f'Missing required parameters: {", ".join(missing)}'}), 400

    agg_df = fetch_and_aggregate_crash_data(
        start_month, start_year, end_month, end_year, K)

    if agg_df is not None:
        set_cached_raw_data(agg_df)
    # Continue with data handling...


@app.route('/autocomplete_zipcode')
def autocomplete_zipcode():
    if cached_raw_data is None:
        download_default_data()
    query = request.args.get('query', '')
    zipcodes = get_all_unique_zip_codes(
        cached_raw_data)  # Fetch all unique zip codes
    matches = [int(zipcode)
               for zipcode in zipcodes if str(zipcode).startswith(query)]
    return jsonify(matches)


@app.route('/search', methods=['GET'])
def search_zip():
    if cached_raw_data is None:
        download_default_data()
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
    valid_zip_codes = get_all_unique_zip_codes(cached_raw_data)
    if zip_code not in valid_zip_codes:

        # Redirect to index if zip code is not found in the dataset
        return redirect(url_for('index'))

    # Call the search_zip_code function to retrieve data
    # _, _, formatted_df_by_area = process_and_format_crash_data(cached_raw_data)
    # print(formatted_df_by_area)
    result = search_zip_code(cached_raw_data, zip_code)

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
