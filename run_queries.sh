#!/bin/bash
# Rec League Manager: rebuilds the database and runs the Deliverable 4 files.
# Usage: put all five files in one folder and run   bash run_queries.sh
# Needs the sqlite3 command line tool (Ubuntu or WSL: sudo apt install sqlite3).
#
# Flags used:
#   -bail          stop at the first error
#   -header        show column names
#   -column        line results up in columns
#   -echo          print each query and its comment above its results, so it's
#                  clear which requirement each result belongs to

DB="rec_league.db"

# Run from the folder this script is in, so the .sql files are found
cd "$(dirname "$0")" || exit 1

if ! command -v sqlite3 > /dev/null; then
    echo "sqlite3 was not found. Install it first (Ubuntu or WSL: sudo apt install sqlite3)."
    exit 1
fi

echo "Recreating database..."

rm -f "$DB"

if ! sqlite3 -bail "$DB" < schema.sql; then
    echo "schema.sql failed. Stopping."
    exit 1
fi

if ! sqlite3 -bail "$DB" < insert_data.sql; then
    echo "insert_data.sql failed. Stopping."
    exit 1
fi

echo
echo "Running queries..."
echo

sqlite3 -header -column -echo "$DB" < queries.sql

echo
echo "Running transaction..."
echo

sqlite3 -bail -header -column -echo "$DB" < transaction.sql
status=$?

echo
if [ "$status" -eq 0 ]; then
    echo "Transaction completed successfully."
else
    echo "Transaction failed."
    echo "Uncommitted changes were rolled back."
fi

echo
echo "Done."
