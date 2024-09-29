# from flask import Flask, request, render_template, redirect, url_for, flash
# import os
# import matplotlib.pyplot as plt
# import geopandas as gpd
# import datetime
# import fiona


# # Assuming your functions are defined in a module named `accident_analysis`
# from data_utils import main

# app = Flask(__name__)
# app.secret_key = 'your_secret_key'  # Set a secret key for session management

# # Update the folders to be inside the data directory
# UPLOAD_FOLDER = os.path.join('data', 'uploads')  # Folder to store uploaded files
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Create the folder if it doesn't exist

# HEATMAP_FOLDER = os.path.join('data', 'heatmaps')  # Directory to store heatmap images
# os.makedirs(HEATMAP_FOLDER, exist_ok=True)  # Create the folder if it doesn't exist

# uploaded_files = {}  # Dictionary to store uploaded files and their results

# @app.route('/')
# def index():
#     return render_template('index.html', files=uploaded_files.keys())

# @app.route('/upload', methods=['POST'])
# def upload_file():
#     if 'file' not in request.files:
#         flash('No file part')
#         return redirect(request.url)

#     file = request.files['file']
#     if file.filename == '':
#         flash('No selected file')
#         return redirect(request.url)

#     filename = file.filename
#     file_path = os.path.join(UPLOAD_FOLDER, filename)
#     file.save(file_path)

#     total_accidents, average_accidents_per_zip, decile_table = main(file_path, k=3)

#     # Remove the .0 from zip codes and accident counts, round multipliers to 2 decimal places
#     decile_table['Zip Code'] = decile_table['Zip Code'].astype(int)
#     decile_table['Accident Count'] = decile_table['Accident Count'].astype(int)
#     decile_table['Multiplier'] = decile_table['Multiplier'].round(2)

#     # Create a new column for displaying decile labels
#     decile_table['Decile Display'] = decile_table['Decile']
#     decile_table['Decile Display'] = decile_table.groupby('Decile Display')['Decile Display'].transform(lambda x: x.where(x.index == x.index.min(), ''))

#     # Store results in the dictionary with the filename as the key
#     uploaded_files[filename] = decile_table

#     return redirect(url_for('index'))

# @app.route('/view/<filename>')
# def view_file(filename):
#     if filename not in uploaded_files:
#         flash('File not found')
#         return redirect(url_for('index'))

#     decile_table = uploaded_files[filename]
#     return render_template('view.html', decile_table=decile_table)

# @app.route('/heatmap/<filename>')
# def heatmap(filename):
#     if filename not in uploaded_files:
#         flash('File not found')
#         return redirect(url_for('index'))

#     # Retrieve the decile table for the specified file
#     decile_table = uploaded_files[filename]

#     # Load the zip code shape file from the specified path
#     shapefile_path = os.path.join('data', 'shapefiles', 'nyc_shapefile.shp')  # Path to your shapefile
#     if not os.path.exists(shapefile_path):
#         flash('Shapefile not found. Please ensure the correct path is provided.')
#         return redirect(url_for('index'))

#     # Check if the shapefile can be read with fiona
#     try:
#         with fiona.open(shapefile_path) as src:
#             print(src.schema)  # Print schema for debugging
#             for feature in src:
#                 print(feature)  # Print each feature for debugging
#     except Exception as e:
#         flash(f'Error reading shapefile: {e}')
#         return redirect(url_for('index'))

#     # If the shapefile is valid, proceed to read it with GeoPandas
#     try:
#         zip_geo = gpd.read_file(shapefile_path)
#         print("Shapefile columns:", zip_geo.columns)  # Add this line to see the columns
#     except Exception as e:
#         flash(f'Error reading shapefile: {e}')
#         return redirect(url_for('index'))

#     # Merge the geo DataFrame with your accident data
#     heatmap_data = zip_geo.merge(decile_table[['Zip Code', 'Decile']], left_on='ZIPCODE', right_on='Zip Code', how='left')

#     # Create a color map for the deciles
#     cmap = plt.get_cmap('YlGnBu', decile_table['Decile'].nunique())  # Adjust color map as needed

#     # Create the heatmap
#     fig, ax = plt.subplots(1, 1, figsize=(10, 10))
#     heatmap_data.plot(column='Decile', cmap=cmap, linewidth=0.8, ax=ax, edgecolor='0.8', legend=True)

#     # Set title and remove axis
#     plt.title('Accident Deciles by Zip Code', fontsize=15)
#     plt.axis('off')

#     # Create a filename for the heatmap image
#     heatmap_filename = f"{filename.split('.')[0]}_heatmap_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
#     heatmap_path = os.path.join(HEATMAP_FOLDER, heatmap_filename)

#     # Save the heatmap to the specified directory
#     plt.savefig(heatmap_path, bbox_inches='tight')
#     plt.close(fig)

#     return render_template('heatmap.html', heatmap_path=heatmap_filename)

# if __name__ == '__main__':
#     app.run(debug=True)
from flask import Flask, request, render_template, redirect, url_for, flash
import os
import matplotlib.pyplot as plt
import geopandas as gpd
import datetime
from data_utils import main

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Set a secret key for session management

# Update the folders to be inside the data directory
UPLOAD_FOLDER = os.path.join('data', 'uploads')  # Folder to store uploaded files
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Create the folder if it doesn't exist

HEATMAP_FOLDER = os.path.join('data', 'heatmaps')  # Directory to store heatmap images
os.makedirs(HEATMAP_FOLDER, exist_ok=True)  # Create the folder if it doesn't exist

uploaded_files = {}  # Dictionary to store uploaded files and their results

@app.route('/')
def index():
    return render_template('index.html', files=uploaded_files.keys())

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)

    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    filename = file.filename
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)

    total_accidents, average_accidents_per_zip, decile_table = main(file_path, k=3)

    # Remove the .0 from zip codes and accident counts, round multipliers to 2 decimal places
    decile_table['Zip Code'] = decile_table['Zip Code'].astype(int)
    decile_table['Accident Count'] = decile_table['Accident Count'].astype(int)
    decile_table['Multiplier'] = decile_table['Multiplier'].round(2)

    # Create a new column for displaying decile labels
    decile_table['Decile Display'] = decile_table['Decile']
    decile_table['Decile Display'] = decile_table.groupby('Decile Display')['Decile Display'].transform(lambda x: x.where(x.index == x.index.min(), ''))

    # Store results in the dictionary with the filename as the key
    uploaded_files[filename] = decile_table

    return redirect(url_for('index'))

@app.route('/view/<filename>')
def view_file(filename):
    if filename not in uploaded_files:
        flash('File not found')
        return redirect(request.url)

    decile_table = uploaded_files[filename]
    return render_template('view.html', decile_table=decile_table)

@app.route('/heatmap/<filename>')
def heatmap(filename):
    if filename not in uploaded_files:
        flash('File not found')
        return redirect(request.url)

    # Retrieve the decile table for the specified file
    decile_table = uploaded_files[filename]

    # Load the zip code shape file from the specified path
    shapefile_path = os.path.join('data', 'shapefiles', 'nyc_shapefile.shp')  # Path to your shapefile
    if not os.path.exists(shapefile_path):
        flash('Shapefile not found. Please ensure the correct path is provided.')
        return redirect(url_for('index'))

    try:
        # Read the shapefile using GeoPandas
        zip_geo = gpd.read_file(shapefile_path)
        print("Shapefile columns:", zip_geo.columns)  # Print the columns of the shapefile
    except Exception as e:
        flash(f'Error reading shapefile: {e}')
        return redirect(url_for('index'))

    # Identify the correct column name for ZIP codes
    zip_code_column = None
    for column in zip_geo.columns:
        if "zip" in column.lower():  # Check for common patterns in ZIP code columns
            zip_code_column = column
            break

    if zip_code_column is None:
        flash('No ZIP code column found in the shapefile.')
        return redirect(url_for('index'))

    # Print columns in decile_table for debugging
    print("Decile table columns:", decile_table.columns)  # Print columns in decile_table

    # Check the contents of the DataFrames
    print(zip_geo.head())  # Print first few rows of zip_geo
    print(decile_table.head())  # Print first few rows of decile_table

    # Attempt to merge the datasets
    try:
        heatmap_data = zip_geo.merge(decile_table[['Zip Code', 'Decile']], left_on=zip_code_column, right_on='Zip Code', how='left')
    except KeyError as e:
        flash(f'Error merging data: {e}')
        return redirect(url_for('index'))

    # Create a color map for the deciles
    cmap = plt.get_cmap('YlGnBu', decile_table['Decile'].nunique())  # Adjust color map as needed

    # Create the heatmap
    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    heatmap_data.plot(column='Decile', cmap=cmap, linewidth=0.8, ax=ax, edgecolor='0.8', legend=True)

    # Set title and remove axis
    plt.title('Accident Deciles by Zip Code', fontsize=15)
    plt.axis('off')

    # Create a filename for the heatmap image
    heatmap_filename = f"{filename.split('.')[0]}_heatmap_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    heatmap_path = os.path.join(HEATMAP_FOLDER, heatmap_filename)

    # Save the heatmap to the specified directory
    plt.savefig(heatmap_path, bbox_inches='tight')
    plt.close(fig)

    return render_template('heatmap.html', heatmap_path=heatmap_filename)

if __name__ == '__main__':
    app.run(debug=True)

