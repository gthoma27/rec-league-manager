"""All of the app's SQL.

Every function takes an open connection first. Values that come from the
user are always passed as ? parameters and never pasted into the SQL text.
Filtering, sorting, joining, and totals are all done here in SQL, not in Python.
"""
from db import transaction


class GameNotScheduledError(Exception):
    """The game was completed or canceled by someone else before the change was saved."""


# ---------------------------------------------------------------- seasons

def list_seasons(conn):
    return conn.execute("""
        SELECT season_id, name, start_date, end_date
        FROM seasons
        ORDER BY start_date
    """).fetchall()


def get_season(conn, season_id):
    return conn.execute("""
        SELECT season_id, name, start_date, end_date
        FROM seasons
        WHERE season_id = ?
    """, (season_id,)).fetchone()


def default_season(conn):
    """The latest season that has at least one game (Fall 2026 in the sample data).

    It's picked from the data instead of today's date, so pages show the same
    thing no matter when the app is run.
    """
    season = conn.execute("""
        SELECT s.season_id, s.name, s.start_date, s.end_date
        FROM seasons s
        JOIN divisions d ON d.season_id = s.season_id
        JOIN teams t     ON t.division_id = d.division_id
        JOIN games g     ON g.home_team_id = t.team_id
        ORDER BY s.start_date DESC
        LIMIT 1
    """).fetchone()
    if season is None:
        season = conn.execute("""
            SELECT season_id, name, start_date, end_date
            FROM seasons
            ORDER BY start_date DESC
            LIMIT 1
        """).fetchone()
    return season


# ---------------------------------------------------------------- players

def _like_pattern(text):
    """LIKE pattern that matches text anywhere. % and _ are escaped so they match literally."""
    escaped = text.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    return '%' + escaped + '%'


def search_players(conn, text):
    """Operation 1: players whose full name or email contains text. Blank text lists everyone.

    LIKE ignores upper and lower case for plain letters in SQLite.
    """
    pattern = _like_pattern(text)
    return conn.execute("""
        SELECT player_id, first_name, last_name, email, phone
        FROM players
        WHERE first_name || ' ' || last_name LIKE ? ESCAPE '\\'
           OR email LIKE ? ESCAPE '\\'
        ORDER BY last_name, first_name
    """, (pattern, pattern)).fetchall()


def get_player(conn, player_id):
    return conn.execute("""
        SELECT player_id, first_name, last_name, email, phone
        FROM players
        WHERE player_id = ?
    """, (player_id,)).fetchone()


def player_teams(conn, player_id):
    """Every team the player has been on, newest season first."""
    return conn.execute("""
        SELECT s.name AS season, d.name AS division, t.team_id, t.name AS team,
               r.jersey_number, r.is_captain
        FROM rosters r
        JOIN teams t     ON t.team_id = r.team_id
        JOIN divisions d ON d.division_id = t.division_id
        JOIN seasons s   ON s.season_id = d.season_id
        WHERE r.player_id = ?
        ORDER BY s.start_date DESC, d.name
    """, (player_id,)).fetchall()


def player_season_stats(conn, player_id):
    """The player's totals for each season they have stats in.

    A game's season comes from the home team's division (both teams are
    always in the same division).
    """
    return conn.execute("""
        SELECT s.name AS season,
               COUNT(*) AS games_played,
               SUM(ps.goals) AS goals,
               SUM(ps.assists) AS assists,
               SUM(ps.fouls) AS fouls
        FROM player_game_stats ps
        JOIN games g     ON g.game_id = ps.game_id
        JOIN teams t     ON t.team_id = g.home_team_id
        JOIN divisions d ON d.division_id = t.division_id
        JOIN seasons s   ON s.season_id = d.season_id
        WHERE ps.player_id = ?
        GROUP BY s.season_id, s.name, s.start_date
        ORDER BY s.start_date DESC
    """, (player_id,)).fetchall()


# ---------------------------------------------------------------- teams and rosters

def list_teams(conn, season_id):
    """Teams in a season with their player count and captain.

    LEFT JOINs keep teams that have no players yet (count 0, no captain).
    """
    return conn.execute("""
        SELECT t.team_id, t.name AS team, d.division_id, d.name AS division,
               COUNT(r.player_id) AS player_count,
               MAX(CASE WHEN r.is_captain = 1
                        THEN p.first_name || ' ' || p.last_name END) AS captain
        FROM teams t
        JOIN divisions d     ON d.division_id = t.division_id
        LEFT JOIN rosters r  ON r.team_id = t.team_id
        LEFT JOIN players p  ON p.player_id = r.player_id
        WHERE d.season_id = ?
        GROUP BY t.team_id, t.name, d.division_id, d.name
        ORDER BY d.name, t.name
    """, (season_id,)).fetchall()


def get_team(conn, team_id):
    return conn.execute("""
        SELECT t.team_id, t.name, t.division_id, d.name AS division,
               s.season_id, s.name AS season
        FROM teams t
        JOIN divisions d ON d.division_id = t.division_id
        JOIN seasons s   ON s.season_id = d.season_id
        WHERE t.team_id = ?
    """, (team_id,)).fetchone()


def team_roster(conn, team_id):
    """Operation 2: the team's players with jersey numbers and contact info."""
    return conn.execute("""
        SELECT r.player_id, r.jersey_number, r.is_captain,
               p.first_name, p.last_name, p.email, p.phone
        FROM rosters r
        JOIN players p ON p.player_id = r.player_id
        WHERE r.team_id = ?
        ORDER BY r.jersey_number
    """, (team_id,)).fetchall()


def team_schedule(conn, team_id):
    """Operation 2 (proposal Q3): the team's full schedule and the result of every game played.

    The second join to teams finds the opponent, whichever side they were on.
    """
    return conn.execute("""
        SELECT g.game_id,
               ts.slot_date,
               ts.start_time,
               v.name AS venue,
               CASE WHEN g.home_team_id = t.team_id THEN 'Home' ELSE 'Away' END AS home_away,
               opp.team_id AS opponent_id,
               opp.name AS opponent,
               g.status,
               CASE WHEN g.home_team_id = t.team_id THEN g.home_score ELSE g.away_score END AS goals_for,
               CASE WHEN g.home_team_id = t.team_id THEN g.away_score ELSE g.home_score END AS goals_against,
               CASE
                   WHEN g.status = 'scheduled' THEN 'Upcoming'
                   WHEN g.home_score = g.away_score THEN 'Tie'
                   WHEN (g.home_team_id = t.team_id) = (g.home_score > g.away_score) THEN 'Win'
                   ELSE 'Loss'
               END AS result
        FROM teams t
        JOIN games g       ON t.team_id IN (g.home_team_id, g.away_team_id)
        JOIN teams opp     ON opp.team_id = CASE WHEN g.home_team_id = t.team_id
                                                 THEN g.away_team_id
                                                 ELSE g.home_team_id END
        JOIN time_slots ts ON ts.slot_id = g.slot_id
        JOIN venues v      ON v.venue_id = ts.venue_id
        WHERE t.team_id = ?
        ORDER BY ts.slot_date, ts.start_time
    """, (team_id,)).fetchall()


def players_not_in_division(conn, division_id):
    """Players who aren't on any team in this division yet (the choices for operation 3)."""
    return conn.execute("""
        SELECT p.player_id, p.first_name, p.last_name, p.email
        FROM players p
        WHERE p.player_id NOT IN (
            SELECT r.player_id
            FROM rosters r
            JOIN teams t ON t.team_id = r.team_id
            WHERE t.division_id = ?
        )
        ORDER BY p.last_name, p.first_name
    """, (division_id,)).fetchall()


def player_team_in_division(conn, player_id, division_id):
    """The team this player is already on in the division, or None."""
    return conn.execute("""
        SELECT t.team_id, t.name
        FROM rosters r
        JOIN teams t ON t.team_id = r.team_id
        WHERE r.player_id = ? AND t.division_id = ?
    """, (player_id, division_id)).fetchone()


def jersey_owner(conn, team_id, jersey_number):
    """Who already wears this number on the team, or None."""
    return conn.execute("""
        SELECT p.first_name || ' ' || p.last_name AS player
        FROM rosters r
        JOIN players p ON p.player_id = r.player_id
        WHERE r.team_id = ? AND r.jersey_number = ?
    """, (team_id, jersey_number)).fetchone()


def team_captain(conn, team_id):
    return conn.execute("""
        SELECT p.first_name || ' ' || p.last_name AS player
        FROM rosters r
        JOIN players p ON p.player_id = r.player_id
        WHERE r.team_id = ? AND r.is_captain = 1
    """, (team_id,)).fetchone()


def add_roster_player(conn, team_id, player_id, jersey_number, is_captain):
    """Operation 3 (proposal operation 1): add a player to a team's roster."""
    conn.execute("""
        INSERT INTO rosters (team_id, player_id, jersey_number, is_captain)
        VALUES (?, ?, ?, ?)
    """, (team_id, player_id, jersey_number, is_captain))


# ---------------------------------------------------------------- games

def list_games(conn, season_id, status=None, needs_ref=False):
    """Games in a season, optionally only one status or only upcoming games with no ref (proposal Q5).

    A None status or a False needs_ref turns that filter off, so the SQL text
    never changes and every value stays a parameter.
    """
    return conn.execute("""
        SELECT g.game_id, ts.slot_date, ts.start_time, v.name AS venue, d.name AS division,
               g.home_team_id, h.name AS home_team, g.away_team_id, a.name AS away_team,
               g.status, g.home_score, g.away_score,
               COUNT(gr.referee_id) AS ref_count
        FROM games g
        JOIN time_slots ts         ON ts.slot_id = g.slot_id
        JOIN venues v              ON v.venue_id = ts.venue_id
        JOIN teams h               ON h.team_id = g.home_team_id
        JOIN teams a               ON a.team_id = g.away_team_id
        JOIN divisions d           ON d.division_id = h.division_id
        LEFT JOIN game_referees gr ON gr.game_id = g.game_id
        WHERE d.season_id = ?
          AND (? IS NULL OR g.status = ?)
        GROUP BY g.game_id, ts.slot_date, ts.start_time, v.name, d.name,
                 g.home_team_id, h.name, g.away_team_id, a.name,
                 g.status, g.home_score, g.away_score
        HAVING ? = 0 OR (g.status = 'scheduled' AND COUNT(gr.referee_id) = 0)
        ORDER BY ts.slot_date, ts.start_time, v.name
    """, (season_id, status, status, 1 if needs_ref else 0)).fetchall()


def get_game(conn, game_id):
    """One game with its teams, division, season, date, time, and venue."""
    return conn.execute("""
        SELECT g.game_id, g.slot_id, g.status, g.home_score, g.away_score,
               g.home_team_id, h.name AS home_team,
               g.away_team_id, a.name AS away_team,
               h.division_id, d.name AS division,
               s.season_id, s.name AS season,
               s.start_date AS season_start, s.end_date AS season_end,
               ts.slot_date, ts.start_time, v.name AS venue, v.address
        FROM games g
        JOIN teams h       ON h.team_id = g.home_team_id
        JOIN teams a       ON a.team_id = g.away_team_id
        JOIN divisions d   ON d.division_id = h.division_id
        JOIN seasons s     ON s.season_id = d.season_id
        JOIN time_slots ts ON ts.slot_id = g.slot_id
        JOIN venues v      ON v.venue_id = ts.venue_id
        WHERE g.game_id = ?
    """, (game_id,)).fetchone()


def game_box_score(conn, game_id):
    """Each player's stat line for a completed game, with the team they played for."""
    return conn.execute("""
        SELECT ps.player_id, p.first_name, p.last_name, r.team_id, r.jersey_number,
               ps.goals, ps.assists, ps.fouls
        FROM player_game_stats ps
        JOIN games g   ON g.game_id = ps.game_id
        JOIN players p ON p.player_id = ps.player_id
        JOIN rosters r ON r.player_id = ps.player_id
                      AND r.team_id IN (g.home_team_id, g.away_team_id)
        WHERE ps.game_id = ?
        ORDER BY r.jersey_number
    """, (game_id,)).fetchall()


def get_slot(conn, slot_id):
    """A time slot with its venue and the game booked in it (booked_game_id is None if open)."""
    return conn.execute("""
        SELECT ts.slot_id, ts.slot_date, ts.start_time, v.name AS venue,
               g.game_id AS booked_game_id
        FROM time_slots ts
        JOIN venues v     ON v.venue_id = ts.venue_id
        LEFT JOIN games g ON g.slot_id = ts.slot_id
        WHERE ts.slot_id = ?
    """, (slot_id,)).fetchone()


def open_slots(conn, start_date, end_date):
    """Slots between two dates with no game in them (proposal Q4).

    The LEFT JOIN keeps every slot, and open slots are the ones with no matching game.
    """
    return conn.execute("""
        SELECT ts.slot_id, ts.slot_date, ts.start_time, v.name AS venue
        FROM time_slots ts
        JOIN venues v     ON v.venue_id = ts.venue_id
        LEFT JOIN games g ON g.slot_id = ts.slot_id
        WHERE g.game_id IS NULL
          AND ts.slot_date BETWEEN ? AND ?
        ORDER BY ts.slot_date, ts.start_time, v.name
    """, (start_date, end_date)).fetchall()


def team_conflicts(conn, slot_id, home_team_id, away_team_id, ignore_game_id=0):
    """Games either team already has at the same date and time as slot_id, at any venue.

    ignore_game_id skips the game being rescheduled (0 skips nothing).
    """
    return conn.execute("""
        SELECT DISTINCT t.name AS team, g.game_id
        FROM time_slots target
        JOIN time_slots ts ON ts.slot_date = target.slot_date
                          AND ts.start_time = target.start_time
        JOIN games g       ON g.slot_id = ts.slot_id
        JOIN teams t       ON t.team_id IN (g.home_team_id, g.away_team_id)
        WHERE target.slot_id = ?
          AND t.team_id IN (?, ?)
          AND g.game_id <> ?
        ORDER BY t.name
    """, (slot_id, home_team_id, away_team_id, ignore_game_id)).fetchall()


def player_conflicts(conn, slot_id, home_team_id, away_team_id, ignore_game_id=0):
    """Players on either team who also play for another team with a game at the same date and time.

    This catches players who are on both an Open and a Coed team.
    """
    return conn.execute("""
        SELECT DISTINCT p.first_name || ' ' || p.last_name AS player,
               other.name AS other_team, g.game_id
        FROM rosters mine
        JOIN rosters theirs ON theirs.player_id = mine.player_id
                           AND theirs.team_id NOT IN (?, ?)
        JOIN teams other    ON other.team_id = theirs.team_id
        JOIN games g        ON theirs.team_id IN (g.home_team_id, g.away_team_id)
        JOIN time_slots ts  ON ts.slot_id = g.slot_id
        JOIN time_slots target ON target.slot_id = ?
        JOIN players p      ON p.player_id = mine.player_id
        WHERE mine.team_id IN (?, ?)
          AND ts.slot_date = target.slot_date
          AND ts.start_time = target.start_time
          AND g.game_id <> ?
        ORDER BY player
    """, (home_team_id, away_team_id, slot_id,
          home_team_id, away_team_id, ignore_game_id)).fetchall()


def schedule_game(conn, slot_id, home_team_id, away_team_id):
    """Extra operation (proposal operation 3): book a new game into an open slot.

    Status defaults to 'scheduled'. games.slot_id is UNIQUE, so the database
    itself refuses a second game in the same slot.
    """
    cursor = conn.execute("""
        INSERT INTO games (slot_id, home_team_id, away_team_id)
        VALUES (?, ?, ?)
    """, (slot_id, home_team_id, away_team_id))
    return cursor.lastrowid


def reschedule_game(conn, game_id, new_slot_id):
    """Operation 4 (proposal operation 6): move an upcoming game to another slot.

    Returns the number of rows changed. 0 means the game was completed or
    canceled after the page was opened.
    """
    cursor = conn.execute("""
        UPDATE games
        SET slot_id = ?
        WHERE game_id = ? AND status = 'scheduled'
    """, (new_slot_id, game_id))
    return cursor.rowcount


def cancel_game(conn, game_id):
    """Operation 4 (proposal operation 6): cancel an upcoming game.

    ON DELETE CASCADE removes its referee assignments, and its slot becomes
    open again. Completed games are never deleted. Returns rows deleted.
    """
    cursor = conn.execute("""
        DELETE FROM games
        WHERE game_id = ? AND status = 'scheduled'
    """, (game_id,))
    return cursor.rowcount


def record_result(conn, game_id, home_score, away_score, stat_rows):
    """Operation 6 (proposal operation 5): save the final score and every player's stats.

    The UPDATE and all of the INSERTs run in one transaction. If any of them
    fails, everything is rolled back, so a game is never left with a score
    but missing stats, or with stats but no score.
    stat_rows is a list of (player_id, goals, assists, fouls).
    """
    with transaction(conn):
        cursor = conn.execute("""
            UPDATE games
            SET status = 'completed', home_score = ?, away_score = ?
            WHERE game_id = ? AND status = 'scheduled'
        """, (home_score, away_score, game_id))
        # 0 rows means someone else completed or canceled the game after the
        # form was opened. Raising here rolls the transaction back.
        if cursor.rowcount != 1:
            raise GameNotScheduledError(game_id)
        conn.executemany("""
            INSERT INTO player_game_stats (game_id, player_id, goals, assists, fouls)
            VALUES (?, ?, ?, ?, ?)
        """, [(game_id, player_id, goals, assists, fouls)
              for player_id, goals, assists, fouls in stat_rows])


# ---------------------------------------------------------------- referees

def list_referees(conn):
    return conn.execute("""
        SELECT referee_id, first_name, last_name
        FROM referees
        ORDER BY last_name, first_name
    """).fetchall()


def get_referee(conn, referee_id):
    return conn.execute("""
        SELECT referee_id, first_name, last_name
        FROM referees
        WHERE referee_id = ?
    """, (referee_id,)).fetchone()


def game_referees(conn, game_id):
    """Referees on a game, center ref first."""
    return conn.execute("""
        SELECT r.referee_id, r.first_name, r.last_name, gr.role
        FROM game_referees gr
        JOIN referees r ON r.referee_id = gr.referee_id
        WHERE gr.game_id = ?
        ORDER BY gr.role = 'assistant', r.last_name
    """, (game_id,)).fetchall()


def referee_on_game(conn, game_id, referee_id):
    return conn.execute("""
        SELECT role
        FROM game_referees
        WHERE game_id = ? AND referee_id = ?
    """, (game_id, referee_id)).fetchone()


def game_has_center_ref(conn, game_id):
    row = conn.execute("""
        SELECT COUNT(*) AS centers
        FROM game_referees
        WHERE game_id = ? AND role = 'center'
    """, (game_id,)).fetchone()
    return row['centers'] > 0


def referee_conflict(conn, referee_id, game_id):
    """Another game this ref is already working at the same date and time, or None."""
    return conn.execute("""
        SELECT other.game_id
        FROM games this_game
        JOIN time_slots this_slot   ON this_slot.slot_id = this_game.slot_id
        JOIN time_slots other_slot  ON other_slot.slot_date = this_slot.slot_date
                                   AND other_slot.start_time = this_slot.start_time
        JOIN games other            ON other.slot_id = other_slot.slot_id
        JOIN game_referees gr       ON gr.game_id = other.game_id
        WHERE this_game.game_id = ?
          AND gr.referee_id = ?
          AND other.game_id <> this_game.game_id
        LIMIT 1
    """, (game_id, referee_id)).fetchone()


def count_game_referees(conn, game_id):
    row = conn.execute("""
        SELECT COUNT(*) AS refs
        FROM game_referees
        WHERE game_id = ?
    """, (game_id,)).fetchone()
    return row['refs']


def assign_referee(conn, game_id, referee_id, role):
    """Extra operation (proposal operation 4): assign a referee to a game."""
    conn.execute("""
        INSERT INTO game_referees (game_id, referee_id, role)
        VALUES (?, ?, ?)
    """, (game_id, referee_id, role))


# ---------------------------------------------------------------- reports

def season_summary(conn, season_id):
    """Operation 5: games played and upcoming, total goals, and average goals per game."""
    return conn.execute("""
        SELECT COALESCE(SUM(g.status = 'completed'), 0) AS games_completed,
               COALESCE(SUM(g.status = 'scheduled'), 0) AS games_upcoming,
               COALESCE(SUM(CASE WHEN g.status = 'completed'
                                 THEN g.home_score + g.away_score END), 0) AS total_goals,
               ROUND(AVG(CASE WHEN g.status = 'completed'
                              THEN g.home_score + g.away_score END), 2) AS avg_goals
        FROM games g
        JOIN teams t     ON t.team_id = g.home_team_id
        JOIN divisions d ON d.division_id = t.division_id
        WHERE d.season_id = ?
    """, (season_id,)).fetchone()


def standings(conn, season_name):
    """Operation 5 (proposal Q1): standings from the division_standings view."""
    return conn.execute("""
        SELECT division, team_id, team, games_played, wins, losses, ties,
               goals_for, goals_against, goal_diff, points
        FROM division_standings
        WHERE season = ?
        ORDER BY division, points DESC, goal_diff DESC, goals_for DESC, team
    """, (season_name,)).fetchall()


def top_scorers(conn, season_id, min_goals):
    """Operation 5 (proposal Q2): players with at least min_goals goals and their goals per game.

    A player only has a stat row for games they played, so AVG is per game played.
    """
    return conn.execute("""
        SELECT p.player_id,
               p.first_name || ' ' || p.last_name AS player,
               COUNT(*) AS games_played,
               SUM(ps.goals) AS goals,
               SUM(ps.assists) AS assists,
               ROUND(AVG(ps.goals), 2) AS goals_per_game
        FROM player_game_stats ps
        JOIN players p   ON p.player_id = ps.player_id
        JOIN games g     ON g.game_id = ps.game_id
        JOIN teams t     ON t.team_id = g.home_team_id
        JOIN divisions d ON d.division_id = t.division_id
        WHERE d.season_id = ?
        GROUP BY p.player_id, p.first_name, p.last_name
        HAVING SUM(ps.goals) >= ?
        ORDER BY goals DESC, goals_per_game DESC, player
    """, (season_id, min_goals)).fetchall()
