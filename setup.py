from setuptools import setup

APP = ['app.py']  # Replace with your main Python script
DATA_FILES = []  # Include any non-Python files you need
OPTIONS = {
    'argv_emulation': True,
    'packages': ['your_required_package'],  # Add any packages your app needs
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
