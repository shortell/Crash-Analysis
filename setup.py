from setuptools import setup
import os

# Main entry point for your application
APP = ['app.py']

# Function to recursively include directories and their contents
def include_dir(path):
    paths = []
    for root, _, files in os.walk(path):
        for file in files:
            full_path = os.path.join(root, file)
            # Include files relative to the root path
            paths.append((os.path.relpath(root, '.'), [full_path]))
    return paths

# Collect all necessary data files
DATA_FILES = (
    include_dir('borough_assets') +
    include_dir('static') +
    include_dir('data') +
    include_dir('templates')
)

# Options for py2app
OPTIONS = {
    'argv_emulation': True,  # Enables better command-line behavior
    'includes': [
        'pipeline_v3',  # Internal dependency
        'os', 'glob', 'threading', 'webbrowser'  # Standard library modules (optional)
    ],
    'packages': [],  # Add external packages if needed, e.g., ['pandas', 'requests']
}

# Setup configuration
setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
