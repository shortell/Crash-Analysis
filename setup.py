from setuptools import setup

APP = ['app.py']
DATA_FILES = [
    ('templates', ['templates/index.html']),
    ('static', []),
    ('borough_assets', []),
]
OPTIONS = {
    'argv_emulation': True,
    'packages': ['flask', 'requests'],  # Include necessary packages explicitly
    'includes': ['flask', 'requests'],  # Force inclusion of modules
    'excludes': ['tkinter'],  # Optional: Exclude unnecessary modules
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
