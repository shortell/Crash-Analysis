from io import StringIO

import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_session import Session

from src.data_cleaning import fetch_and_aggregate_crash_data, process_and_format_crash_data
from src.zip_code_search import get_all_unique_zip_codes, search_zip_code
from src.heatmap_generation import create_interactive_heatmap
from src.data_fetching import is_date_range_valid, get_valid_years, get_current_month, get_current_year
from src.data_storage import delete_all_files_in_data_dir, create_file_name, fetch_csv_file, save_dataframe_to_csv

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Configure Flask-Session
# You can use 'redis' for Redis-based sessions
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

K = 5  # Number of neighbors to check for accidents with no zip code

INT_TO_MONTH = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December"
}


def get_session_cached_raw_data():
    return pd.read_json(StringIO(session['cached_raw_data']))


def get_session_cached_formatted_data():
    formatted_df_by_area = pd.read_json(
        StringIO(session['cached_formatted_data']))
    total_crashes = session['total_crashes']
    average_crashes_per_zip = session['average_crashes_per_zip']

    return total_crashes, average_crashes_per_zip, formatted_df_by_area


def get_session_area():
    return session['area']


def get_session_date_range():
    return session['start_month'], session['start_year'], session['end_month'], session['end_year']


def set_session_date_range(start_month, start_year, end_month, end_year):
    session['start_month'] = start_month
    session['start_year'] = start_year
    session['end_month'] = end_month
    session['end_year'] = end_year


def set_session_cached_raw_data(agg_df):
    session['cached_raw_data'] = agg_df.to_json()


def set_session_cached_formatted_data(formatted_df_by_area, total_crashes, average_crashes_per_zip):
    session['cached_formatted_data'] = formatted_df_by_area.to_json()
    session['total_crashes'] = total_crashes
    session['average_crashes_per_zip'] = average_crashes_per_zip


def set_session_area(area):
    session['area'] = area


def get_latest_month_year():
    current_month = get_current_month()
    current_year = get_current_year()

    if current_month == 1:
        current_month = 12
        current_year = current_year - 1

    else:
        current_month = current_month - 1

    return current_month, current_year


def get_default_data():
    start_month, start_year = get_latest_month_year()
    end_month, end_year = get_latest_month_year()

    filename = create_file_name(
        start_month, start_year, end_month, end_year)

    agg_df = fetch_csv_file(filename)
    if agg_df is None:
        agg_df = fetch_and_aggregate_crash_data(
            start_month, start_year, end_month, end_year, K)
        if agg_df is not None:
            delete_all_files_in_data_dir()
            save_dataframe_to_csv(agg_df, filename)

    set_session_cached_raw_data(agg_df)
    set_session_date_range(start_month, start_year, end_month, end_year)


@app.route('/')
def index():
    """ Display the available boroughs and datasets. """
    if 'cached_raw_data' not in session:
        get_default_data()
    return render_template('index.html')


@app.route('/view/<area>')
def view_data(area):
    """
    Display the selected area (borough or citywide) and dataset.
    """

    if 'cached_raw_data' not in session:
        get_default_data()
    cached_raw_data = get_session_cached_raw_data()
    total_crashes, average_crashes_per_zip, formatted_df_by_area = process_and_format_crash_data(
        cached_raw_data, area)

    set_session_area(area)
    set_session_cached_formatted_data(
        formatted_df_by_area, total_crashes, average_crashes_per_zip)

    # Ensure the session date range is set
    if 'start_month' not in session or 'start_year' not in session or 'end_month' not in session or 'end_year' not in session:
        start_month, start_year = get_latest_month_year()
        end_month, end_year = get_latest_month_year()
        set_session_date_range(start_month, start_year, end_month, end_year)
    else:
        start_month, start_year, end_month, end_year = get_session_date_range()

    return render_template(
        'view_area.html',
        area=area,
        total_accidents=total_crashes,
        average_accidents_per_zip=average_crashes_per_zip,
        decile_table=formatted_df_by_area,
        years=get_valid_years(),
        start_year=start_year,
        end_year=end_year,
        start_month_name=INT_TO_MONTH[int(start_month)],
        end_month_name=INT_TO_MONTH[int(end_month)]
    )


@app.route('/download', methods=['POST'])
def download_crash_data():
    start_month = request.form.get('start_month')
    start_year = request.form.get('start_year')
    end_month = request.form.get('end_month')
    end_year = request.form.get('end_year')

    area = get_session_area()
    agg_df = get_session_cached_raw_data()
    if is_date_range_valid(int(start_month), int(start_year), int(end_month), int(end_year)):
        agg_df = fetch_and_aggregate_crash_data(
            start_month, start_year, end_month, end_year, K)
        set_session_cached_raw_data(agg_df)
        total_crashes, average_crashes_per_zip, formatted_df_by_area = process_and_format_crash_data(
            agg_df, area)
        set_session_cached_formatted_data(
            formatted_df_by_area, total_crashes, average_crashes_per_zip)
        set_session_date_range(start_month, start_year, end_month, end_year)
        return render_template(
            'view_area.html',
            area=area,
            total_accidents=total_crashes,
            average_accidents_per_zip=average_crashes_per_zip,
            decile_table=formatted_df_by_area,
            years=get_valid_years(),
            start_year=start_year,
            end_year=end_year,
            start_month_name=INT_TO_MONTH[int(start_month)],
            end_month_name=INT_TO_MONTH[int(end_month)]
        )
    else:
        start_month, start_year, end_month, end_year = get_session_date_range()
        total_crashes, average_crashes_per_zip, formatted_df_by_area = get_session_cached_formatted_data()
        return render_template(
            'view_area.html',
            area=area,
            total_accidents=total_crashes,
            average_accidents_per_zip=average_crashes_per_zip,
            decile_table=formatted_df_by_area,
            years=get_valid_years(),
            start_month=start_month,
            start_year=start_year,
            end_month=end_month,
            end_year=end_year,
            start_month_name=INT_TO_MONTH[int(start_month)],
            end_month_name=INT_TO_MONTH[int(end_month)]
        )


@app.route('/years')
def get_years():
    return jsonify(get_valid_years())


@app.route('/view_map/<area>')
def view_map(area):
    # Create the heatmap using your function.
    if 'cached_formatted_data' not in session:
        flash("Error generating heatmap")
        return redirect(url_for("view_data", area=area))

    cached_formatted_data = pd.read_json(
        StringIO(session['cached_formatted_data']))
    heatmap = create_interactive_heatmap(area, cached_formatted_data)
    if not heatmap:
        flash("Error generating heatmap")
        return redirect(url_for("view_data", area=area))

    heatmap_html = heatmap.get_root().render()  # Render the heatmap to HTML.
    if not heatmap_html.strip():  # Check if the HTML content is empty.
        flash("Heatmap HTML is empty")
        return redirect(url_for("view_data", area=area))

    return render_template('view_map.html', area=area, heatmap_html=heatmap_html)


@app.route('/autocomplete_zipcode')
def autocomplete_zipcode():
    if 'cached_raw_data' not in session:
        get_default_data()
    cached_raw_data = get_session_cached_raw_data()
    query = request.args.get('query', '')
    zipcodes = get_all_unique_zip_codes(
        cached_raw_data)  # Fetch all unique zip codes
    matches = [int(zipcode)
               for zipcode in zipcodes if str(zipcode).startswith(query)]
    return jsonify(matches)


@app.route('/search', methods=['GET'])
def search_zip():
    if 'cached_raw_data' not in session:
        get_default_data()
    cached_raw_data = get_session_cached_raw_data()
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
