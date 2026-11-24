"""Build (or rebuild) the Rec League Manager database.

Runs schema.sql and then insert_data.sql. Running it again resets the
database to the sample data, so any changes made in the app are lost.

Usage:  python init_db.py
"""
import sqlite3
import sys

from config import DATA_FILE, DB_PATH, SCHEMA_FILE

ROW_COUNT_SQL = """
    SELECT 'seasons', COUNT(*) FROM seasons
    UNION ALL SELECT 'divisions', COUNT(*) FROM divisions
    UNION ALL SELECT 'teams', COUNT(*) FROM teams
    UNION ALL SELECT 'players', COUNT(*) FROM players
    UNION ALL SELECT 'rosters', COUNT(*) FROM rosters
    UNION ALL SELECT 'venues', COUNT(*) FROM venues
    UNION ALL SELECT 'time_slots', COUNT(*) FROM time_slots
    UNION ALL SELECT 'games', COUNT(*) FROM games
    UNION ALL SELECT 'referees', COUNT(*) FROM referees
    UNION ALL SELECT 'game_referees', COUNT(*) FROM game_referees
    UNION ALL SELECT 'player_game_stats', COUNT(*) FROM player_game_stats
"""


def read_file(path):
    with open(path, encoding='utf-8') as sql_file:
        return sql_file.read()


def main():
    try:
        schema_sql = read_file(SCHEMA_FILE)
        data_sql = read_file(DATA_FILE)
    except OSError as error:
        print(f'Could not read the SQL files: {error}')
        return 1

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        # executescript runs every statement in the file in order, like the
        # sqlite3 .read command. Both files turn foreign keys on first.
        conn.executescript(schema_sql)
        conn.executescript(data_sql)
        counts = conn.execute(ROW_COUNT_SQL).fetchall()
    except sqlite3.Error as error:
        print(f'Building the database failed: {error}')
        print('If the app is running, stop it (Ctrl+C) and try again.')
        return 1
    finally:
        if conn is not None:
            conn.close()

    total = sum(count for _, count in counts)
    print(f'Built {DB_PATH}')
    print(f'{total} rows in {len(counts)} tables.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
