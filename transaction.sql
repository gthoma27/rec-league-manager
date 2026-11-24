-- Rec League Manager
-- transaction.sql: entering a final score and player stats (proposal operation 5)
-- DBMS: SQLite 3. Run after schema.sql and insert_data.sql.
--
-- Game 16, Northside United (home) vs Riverside Rovers (away) on Oct 24,
-- ended 3 to 1. Recording it takes two related changes:
--   1. UPDATE games to mark it completed with the final score
--   2. INSERT a stat row for each player who played
-- These have to succeed or fail together. If only the score saved, the
-- standings would count the game but the scoring leaders would be missing its
-- goals. If only the stats saved, the goals would count toward the scoring
-- leaders for a game the standings still show as not played.
--
-- This demo ends with ROLLBACK so the sample data is left exactly as it was.
-- In real use the last step would be COMMIT.
--
-- SQLite difference: if one statement inside a transaction fails, SQLite only
-- undoes that statement and leaves the transaction open. Without -bail, the
-- sqlite3 tool would skip the failed statement and keep going, so a COMMIT at
-- the end would save the score without its stats. run_queries.sh runs this file
-- with -bail, so the first error stops the script before COMMIT, and SQLite
-- rolls back the unfinished transaction when sqlite3 exits.

PRAGMA foreign_keys = ON;

-- Before: game 16 is scheduled with no score
SELECT game_id, status, home_score, away_score
FROM games
WHERE game_id = 16;

-- Before: standings for the two teams
SELECT team, games_played AS gp, wins, losses, ties, points
FROM division_standings
WHERE team_id IN (4, 5)
ORDER BY points DESC;

BEGIN TRANSACTION;

-- Change 1: final score
UPDATE games
SET status = 'completed',
    home_score = 3,
    away_score = 1
WHERE game_id = 16;

-- Change 2: player stats (goals for each team add up to its score)
INSERT INTO player_game_stats (game_id, player_id, goals, assists, fouls) VALUES
    -- Northside United: 3 goals
    (16, 6, 1, 1, 0), (16, 7, 0, 1, 1), (16, 8, 0, 0, 2), (16, 17, 2, 0, 0), (16, 18, 0, 0, 0),
    -- Riverside Rovers: 1 goal
    (16, 1, 0, 1, 1), (16, 2, 1, 0, 0), (16, 3, 0, 0, 0), (16, 4, 0, 0, 1), (16, 16, 0, 0, 0);

-- Inside the transaction: the score and the stats agree (3 + 1 = 4 goals)
SELECT g.status,
       g.home_score + g.away_score AS final_score_total,
       (SELECT COUNT(*) FROM player_game_stats WHERE game_id = 16) AS stat_rows,
       (SELECT SUM(goals) FROM player_game_stats WHERE game_id = 16) AS goals_in_stats
FROM games g
WHERE g.game_id = 16;

-- Inside the transaction: standings now include the game
SELECT team, games_played AS gp, wins, losses, ties, points
FROM division_standings
WHERE team_id IN (4, 5)
ORDER BY points DESC;

ROLLBACK;

-- After ROLLBACK: game 16 is scheduled again and has no stat rows
SELECT g.game_id,
       g.status,
       g.home_score,
       g.away_score,
       (SELECT COUNT(*) FROM player_game_stats WHERE game_id = 16) AS stat_rows
FROM games g
WHERE g.game_id = 16;

-- After ROLLBACK: standings match the "before" results
SELECT team, games_played AS gp, wins, losses, ties, points
FROM division_standings
WHERE team_id IN (4, 5)
ORDER BY points DESC;
