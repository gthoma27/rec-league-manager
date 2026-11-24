-- Rec League Manager
-- schema.sql: creates all tables, the standings view, and the time slot index.
-- DBMS: SQLite 3
-- Run this first, then insert_data.sql.

-- SQLite ignores foreign keys unless this is turned on for the connection.
PRAGMA foreign_keys = ON;

-- Cleanup so the database can be rebuilt from scratch.
-- Child tables are dropped before the tables they point to.
DROP VIEW IF EXISTS division_standings;
DROP INDEX IF EXISTS idx_time_slots_date;
DROP TABLE IF EXISTS player_game_stats;
DROP TABLE IF EXISTS game_referees;
DROP TABLE IF EXISTS games;
DROP TABLE IF EXISTS referees;
DROP TABLE IF EXISTS time_slots;
DROP TABLE IF EXISTS venues;
DROP TABLE IF EXISTS rosters;
DROP TABLE IF EXISTS players;
DROP TABLE IF EXISTS teams;
DROP TABLE IF EXISTS divisions;
DROP TABLE IF EXISTS seasons;


-- Dates are stored as TEXT in YYYY-MM-DD format and times as TEXT in HH:MM (24 hour).
-- That format sorts and compares correctly as text, so the date checks below
-- make sure every date is written that way. date() returns NULL for anything
-- that isn't a real date, and comparing date(x) to x catches the wrong format.
-- Booleans are INTEGER 0 or 1.

CREATE TABLE seasons (
    season_id   INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    start_date  TEXT NOT NULL CHECK (date(start_date) IS NOT NULL AND date(start_date) = start_date),
    end_date    TEXT NOT NULL CHECK (date(end_date) IS NOT NULL AND date(end_date) = end_date),
    CHECK (end_date > start_date)
);

CREATE TABLE divisions (
    division_id INTEGER PRIMARY KEY,
    season_id   INTEGER NOT NULL,
    name        TEXT NOT NULL,
    FOREIGN KEY (season_id) REFERENCES seasons (season_id),
    UNIQUE (season_id, name)        -- no two "Open" divisions in the same season
);

CREATE TABLE teams (
    team_id     INTEGER PRIMARY KEY,
    division_id INTEGER NOT NULL,
    name        TEXT NOT NULL,
    FOREIGN KEY (division_id) REFERENCES divisions (division_id),
    UNIQUE (division_id, name)      -- a name can come back next season, but not twice in one division
);

CREATE TABLE players (
    player_id   INTEGER PRIMARY KEY,
    first_name  TEXT NOT NULL,
    last_name   TEXT NOT NULL,
    email       TEXT NOT NULL UNIQUE,
    phone       TEXT                -- optional
);

-- Junction table for players and teams (many-to-many).
-- NOT NULL is needed on the key columns because SQLite allows NULLs in a composite primary key.
CREATE TABLE rosters (
    team_id       INTEGER NOT NULL,
    player_id     INTEGER NOT NULL,
    jersey_number INTEGER NOT NULL CHECK (jersey_number BETWEEN 0 AND 99),
    is_captain    INTEGER NOT NULL DEFAULT 0 CHECK (is_captain IN (0, 1)),
    PRIMARY KEY (team_id, player_id),
    FOREIGN KEY (team_id) REFERENCES teams (team_id),
    FOREIGN KEY (player_id) REFERENCES players (player_id),
    UNIQUE (team_id, jersey_number) -- two players on one team can't wear the same number
);

CREATE TABLE venues (
    venue_id    INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    address     TEXT NOT NULL
);

-- Each row is one bookable time at one venue. A slot with no game is an open slot.
CREATE TABLE time_slots (
    slot_id     INTEGER PRIMARY KEY,
    venue_id    INTEGER NOT NULL,
    slot_date   TEXT NOT NULL CHECK (date(slot_date) IS NOT NULL AND date(slot_date) = slot_date),
    -- HH:MM with a real 24 hour time (00:00 to 23:59)
    start_time  TEXT NOT NULL CHECK (start_time GLOB '[0-2][0-9]:[0-5][0-9]' AND start_time < '24:00'),
    FOREIGN KEY (venue_id) REFERENCES venues (venue_id),
    -- the same venue, date, and time can't be entered as two slots,
    -- otherwise two games could end up at the same place and time
    UNIQUE (venue_id, slot_date, start_time)
);

CREATE TABLE games (
    game_id      INTEGER PRIMARY KEY,
    slot_id      INTEGER NOT NULL UNIQUE,   -- one game per slot, so a venue can't be double booked
    home_team_id INTEGER NOT NULL,
    away_team_id INTEGER NOT NULL,
    status       TEXT NOT NULL DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'completed')),
    home_score   INTEGER CHECK (home_score >= 0),
    away_score   INTEGER CHECK (away_score >= 0),
    FOREIGN KEY (slot_id) REFERENCES time_slots (slot_id),
    FOREIGN KEY (home_team_id) REFERENCES teams (team_id),
    FOREIGN KEY (away_team_id) REFERENCES teams (team_id),
    CHECK (home_team_id <> away_team_id),   -- a team can't play itself
    -- scores stay NULL until the game is completed, then both scores are required
    CHECK (
        (status = 'scheduled' AND home_score IS NULL AND away_score IS NULL)
        OR (status = 'completed' AND home_score IS NOT NULL AND away_score IS NOT NULL)
    )
);

CREATE TABLE referees (
    referee_id  INTEGER PRIMARY KEY,
    first_name  TEXT NOT NULL,
    last_name   TEXT NOT NULL,
    email       TEXT NOT NULL UNIQUE,
    phone       TEXT                -- optional
);

-- Junction table for referees and games (many-to-many).
-- ON DELETE CASCADE: canceling (deleting) a game also removes its ref assignments.
CREATE TABLE game_referees (
    game_id     INTEGER NOT NULL,
    referee_id  INTEGER NOT NULL,
    role        TEXT NOT NULL DEFAULT 'center' CHECK (role IN ('center', 'assistant')),
    PRIMARY KEY (game_id, referee_id),
    FOREIGN KEY (game_id) REFERENCES games (game_id) ON DELETE CASCADE,
    FOREIGN KEY (referee_id) REFERENCES referees (referee_id)
);

-- One player's stat line for one game.
CREATE TABLE player_game_stats (
    game_id     INTEGER NOT NULL,
    player_id   INTEGER NOT NULL,
    goals       INTEGER NOT NULL DEFAULT 0 CHECK (goals >= 0),
    assists     INTEGER NOT NULL DEFAULT 0 CHECK (assists >= 0),
    fouls       INTEGER NOT NULL DEFAULT 0 CHECK (fouls >= 0),
    PRIMARY KEY (game_id, player_id),
    FOREIGN KEY (game_id) REFERENCES games (game_id) ON DELETE CASCADE,
    FOREIGN KEY (player_id) REFERENCES players (player_id)
);


-- Index for looking up slots by date, like pulling every booked and open slot
-- for one week (proposal question 4).
-- The automatic index from UNIQUE (venue_id, slot_date, start_time) can't help
-- with a date range across all venues because venue_id comes first in it.
CREATE INDEX idx_time_slots_date ON time_slots (slot_date);


-- Standings for every team in every division.
-- Only completed games count. Each completed game is turned into two rows,
-- one from the home team's side and one from the away team's side, so every
-- team's goals for and against line up the same way.
-- LEFT JOIN keeps teams that haven't played yet (they show all zeros).
-- Points use the usual soccer rule: 3 for a win, 1 for a tie.
CREATE VIEW division_standings AS
SELECT
    s.name   AS season,
    d.name   AS division,
    t.team_id,
    t.name   AS team,
    COUNT(r.game_id) AS games_played,
    SUM(CASE WHEN r.goals_for > r.goals_against THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN r.goals_for < r.goals_against THEN 1 ELSE 0 END) AS losses,
    SUM(CASE WHEN r.goals_for = r.goals_against THEN 1 ELSE 0 END) AS ties,
    COALESCE(SUM(r.goals_for), 0)     AS goals_for,
    COALESCE(SUM(r.goals_against), 0) AS goals_against,
    COALESCE(SUM(r.goals_for - r.goals_against), 0) AS goal_diff,
    SUM(CASE WHEN r.goals_for > r.goals_against THEN 3
             WHEN r.goals_for = r.goals_against THEN 1
             ELSE 0 END) AS points
FROM teams t
JOIN divisions d ON d.division_id = t.division_id
JOIN seasons s   ON s.season_id = d.season_id
LEFT JOIN (
    SELECT game_id, home_team_id AS team_id, home_score AS goals_for, away_score AS goals_against
    FROM games
    WHERE status = 'completed'
    UNION ALL
    SELECT game_id, away_team_id, away_score, home_score
    FROM games
    WHERE status = 'completed'
) r ON r.team_id = t.team_id
GROUP BY s.name, d.name, t.team_id, t.name;
