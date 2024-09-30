from flask import Flask, request, render_template, redirect, url_for, flash
import os
from data_utils import main

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Set a secret key for session management

# Update the folders to be inside the data directory
# Folder to store uploaded files
UPLOAD_FOLDER = os.path.join('data', 'uploads')
# Create the folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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

    # Get the selected borough from the form
    # borough = request.form.get('borough')  # Get borough from the form
    # Call the main function to get accident data
    total_accidents, average_accidents_per_zip, decile_table = main(file_path, k=3)

    # Adjust columns as needed
    decile_table['Zip Code'] = decile_table['Zip Code'].astype(int)
    decile_table['Accident Count'] = decile_table['Accident Count'].astype(int)
    decile_table['Accident Likelihood Factor'] = decile_table['Accident Likelihood Factor'].round(2)
    decile_table['Average Persons Injured/Killed'] = decile_table['Average Persons Injured/Killed'].round(4)

    # Store results in the dictionary with the filename as the key
    uploaded_files[filename] = {
        'decile_table': decile_table,
        'total_accidents': total_accidents,
        'average_accidents_per_zip': average_accidents_per_zip
    }

    return redirect(url_for('index'))

@app.route('/view/<filename>')
def view_file(filename):
    if filename not in uploaded_files:
        flash('File not found')
        return redirect(request.url)

    # Retrieve the results stored during file upload
    file_data = uploaded_files[filename]
    decile_table = file_data['decile_table']
    total_accidents = file_data['total_accidents']
    average_accidents_per_zip = file_data['average_accidents_per_zip']

    # Get sort parameters from query string
    sort_by = request.args.get('sort_by', 'Accident Count')  # Default to Accident Count
    order = request.args.get('order', 'asc')  # Default to ascending order

    # Handle mapping for proper column names in DataFrame
    column_mapping = {
        'Decile': 'Decile',
        'Zip Code': 'Zip Code',  # Replace with the correct column name in your DataFrame
        'Accident Count': 'Accident Count',  # Replace with actual column name if different
        'Average Persons Injured/Killed': 'Average Persons Injured/Killed',
        'Accident Likelihood Factor': 'Accident Likelihood Factor'
    }

    # Sort the DataFrame
    if sort_by in column_mapping:
        ascending = True if order == 'asc' else False
        decile_table = decile_table.sort_values(by=column_mapping[sort_by], ascending=ascending)

    return render_template(
        'view.html',
        decile_table=decile_table,
        total_accidents=total_accidents,
        average_accidents_per_zip=average_accidents_per_zip,
        filename=filename
    )


if __name__ == '__main__':
    app.run(debug=True)
