"""SQLite connection and transaction helpers.

Each web request opens one connection the first time it needs the database,
and close_db (registered in app.py) closes it when the request ends.
"""
import os
import sqlite3
from contextlib import contextmanager

from flask import g

from config import DB_PATH

# Every table and view the app reads from. Used to check the database was built.
REQUIRED_OBJECTS = (
    'seasons', 'divisions', 'teams', 'players', 'rosters', 'venues',
    'time_slots', 'games', 'referees', 'game_referees', 'player_game_stats',
    'division_standings',
)


class DatabaseNotReady(Exception):
    """The database file is missing, so init_db.py hasn't been run yet."""


def connect(path=DB_PATH):
    """Open a connection with foreign keys on and rows readable by column name."""
    # sqlite3.connect quietly creates an empty file if none exists, which would
    # lead to confusing "no such table" errors later. Checking first gives a
    # clear message instead.
    if not os.path.exists(path):
        raise DatabaseNotReady(
            f'No database found at {path}. Run "python init_db.py" to build it.'
        )
    # isolation_level=None turns off Python's automatic transactions. Each
    # statement is saved as soon as it runs, unless it runs inside
    # transaction() below, which keeps every multi-step change explicit.
    conn = sqlite3.connect(path, isolation_level=None, timeout=5)
    conn.row_factory = sqlite3.Row
    # SQLite only enforces foreign keys when this is on, and only for this connection.
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def get_db():
    """The connection for the current request, opened on first use."""
    if 'db' not in g:
        g.db = connect()
    return g.db


def close_db(exception=None):
    """Close the request's connection, if one was opened."""
    conn = g.pop('db', None)
    if conn is not None:
        conn.close()


@contextmanager
def transaction(conn):
    """Run several statements as one unit. Either all of them are saved or none are.

    Usage:
        with transaction(conn):
            conn.execute(...)
            conn.execute(...)
    """
    # IMMEDIATE takes the write lock at the start, so two people saving at the
    # same moment wait their turn instead of failing halfway through.
    conn.execute('BEGIN IMMEDIATE')
    try:
        yield conn
    except BaseException:
        if conn.in_transaction:
            conn.execute('ROLLBACK')
        raise
    conn.execute('COMMIT')


def missing_objects(path=DB_PATH):
    """Names from REQUIRED_OBJECTS that aren't in the database. An empty list means it's ready."""
    conn = connect(path)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
        ).fetchall()
    finally:
        conn.close()
    present = {row['name'] for row in rows}
    return [name for name in REQUIRED_OBJECTS if name not in present]
