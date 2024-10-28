from setuptools import setup
import os

APP = ['app.py']  # Your main Python script
DATA_FILES = []  # Initialize data files

# Function to recursively add directories and their contents
def include_dir(path):
    paths = []
    for root, _, files in os.walk(path):
        for file in files:
            full_path = os.path.join(root, file)
            paths.append((root, [full_path]))
    return paths

# Include non-Python directories and files
DATA_FILES.extend(include_dir('borough_assets'))
DATA_FILES.extend(include_dir('data'))
DATA_FILES.extend(include_dir('static'))
DATA_FILES.extend(include_dir('templates'))

OPTIONS = {
    'argv_emulation': True,  # Emulates argv behavior for your script
    'packages': ['your_required_package'],  # Include any required packages
    'includes': ['pipeline_v3'],  # Ensure dependencies like pipeline_v3.py are included
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
