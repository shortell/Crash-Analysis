from setuptools import setup

APP = ['app.py']  # Entry point of the app
DATA_FILES = [
    ('templates', ['templates/index.html']),
    ('static', []),  # Include static files if any
    ('borough_assets', []),  # Include any CSV files or directories
]
OPTIONS = {
    'argv_emulation': True,  # Ensures the app opens correctly when double-clicked
    'packages': ['flask'],  # Include Flask and other dependencies
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
