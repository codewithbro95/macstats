from setuptools import setup

APP = ['main.py']
APP_NAME = 'MacStats'
DATA_FILES = []
OPTIONS = {
    'argv_emulation': True,
    'iconfile': 'assets/app-icon.icns',
    'plist': {
        'CFBundleName': APP_NAME,
        'LSUIElement': True,  # run as agent (no dock icon)
    },
    'packages': ['rumps','psutil'],
}

setup(
    app=APP,
    name=APP_NAME,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
)
