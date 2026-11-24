"""Settings for Rec League Manager.

The defaults work as they are, so no setup is needed. The database path,
port, and secret key can be changed with environment variables or a .env
file (copy .env.example to .env). See README.md.
"""
import os

try:
    from dotenv import load_dotenv
except ImportError:
    # python-dotenv isn't installed yet (for example, running init_db.py before
    # "pip install -r requirements.txt"). Settings then come only from
    # environment variables, and the defaults still work.
    load_dotenv = None

# Folder that holds this file. Every path below is built from it, so the app
# finds its files no matter which folder it is started from.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Read optional settings from .env in this folder, if the file exists.
# Variables already set in the terminal win over the file.
# .env is listed in .gitignore, so local settings are never committed.
if load_dotenv is not None:
    load_dotenv(os.path.join(BASE_DIR, '.env'))

# SQLite database file. Set REC_LEAGUE_DB to use a different file.
# A relative path is taken from BASE_DIR.
DB_PATH = os.path.join(BASE_DIR, os.environ.get('REC_LEAGUE_DB', '').strip() or 'rec_league.db')

# The SQL files init_db.py runs to build the database.
SCHEMA_FILE = os.path.join(BASE_DIR, 'schema.sql')
DATA_FILE = os.path.join(BASE_DIR, 'insert_data.sql')

# The app only listens on this computer, so nobody else on the network can reach it.
HOST = '127.0.0.1'
DEFAULT_PORT = 5050


def get_port():
    """Port from the PORT environment variable, or 5050 if it isn't set or isn't valid."""
    raw = os.environ.get('PORT', '').strip()
    if raw.isdigit() and 1 <= int(raw) <= 65535:
        return int(raw)
    return DEFAULT_PORT
