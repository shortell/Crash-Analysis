from flask import Flask, render_template, request, redirect, url_for, flash
from pipeline_v3 import main
import os
import glob
from threading import Timer
import webbrowser


app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Set the base directory where borough datasets are stored

# List of available borough directories
DIRECTORIES = ['brooklyn', 'citywide', 'manhattan',
               'queens', 'staten_island', 'the_bronx']

# Allowable file extensions for uploads
ALLOWED_EXTENSIONS = {'csv'}

K = 3  # Number of neighbors to check for accidents with no zip code

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

@app.route('/upload/<area>', methods=['POST'])
def upload_csv(area):
    # Remove the cached table for the area, if it exists
    cached_tables.pop(area, None)

    # Delete all CSV files for the area in unprocessed_data and processed_data directories
    delete_files(f'borough_assets/{area}/unprocessed_data/*.csv')
    delete_files(f'borough_assets/{area}/processed_data/*.csv')

    # Delete the heatmap for the area, if it exists
    heatmap_path = f'static/{area}/interactive_heatmap.html'
    if os.path.exists(heatmap_path):
        os.remove(heatmap_path)

    # Handle the file upload
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)

    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    if file and file.filename.endswith('.csv'):
        save_path = os.path.join(f'borough_assets/{area}/unprocessed_data', file.filename)
        file.save(save_path)
        flash('File successfully uploaded')

    return redirect(url_for('view_data', area=area))


if __name__ == '__main__':
    app.run(debug=True)
