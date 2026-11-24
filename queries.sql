-- Rec League Manager
-- queries.sql: Deliverable 4 queries. Run after schema.sql and insert_data.sql.
-- DBMS: SQLite 3
--
-- Proposal questions answered here:
--   Q1 standings (Req 9), Q2 top scorers (Req 6), Q3 team schedule (Req 4),
--   Q4 booked and open slots (Req 3), Q5 games that still need a ref (Req 7),
--   Q6 last season's players who haven't come back (Req 8)
--
-- Queries name the season directly ('Fall 2026') instead of using today's date,
-- so the results are the same no matter when this is run.
-- "Upcoming" means a game whose status is still 'scheduled'.


-- Requirement 1: Filtering and Sorting
-- Players with no phone number on file, so the league admin knows who to ask
-- for one before a rainout or schedule change.
SELECT first_name,
       last_name,
       email
FROM players
WHERE phone IS NULL
ORDER BY last_name, first_name;


-- Requirement 2: INNER JOIN
-- Riverside Rovers' Fall 2026 roster (team 4) with jersey numbers and contact
-- info, the list a captain uses to manage their team.
-- Team names repeat each season, so the team_id picks the Fall team.
SELECT r.jersey_number AS jersey,
       p.first_name || ' ' || p.last_name AS player,
       CASE WHEN r.is_captain = 1 THEN 'Yes' ELSE 'No' END AS captain,
       p.email,
       p.phone
FROM rosters r
INNER JOIN players p ON p.player_id = r.player_id
WHERE r.team_id = 4
ORDER BY r.is_captain DESC, r.jersey_number;


-- Requirement 3: LEFT JOIN (proposal Q4)
-- Every time slot for the week of Oct 25 to Oct 31, 2026, and whether it's
-- booked or still open. Open slots have no game, so the LEFT JOIN keeps them
-- with blank team names. The date range uses idx_time_slots_date from Deliverable 3.
SELECT ts.slot_date AS date,
       ts.start_time AS time,
       v.name AS venue,
       CASE WHEN g.game_id IS NULL THEN 'Open' ELSE 'Booked' END AS slot_status,
       h.name AS home_team,
       a.name AS away_team
FROM time_slots ts
INNER JOIN venues v ON v.venue_id = ts.venue_id
LEFT JOIN games g ON g.slot_id = ts.slot_id
LEFT JOIN teams h ON h.team_id = g.home_team_id
LEFT JOIN teams a ON a.team_id = g.away_team_id
WHERE ts.slot_date BETWEEN '2026-10-25' AND '2026-10-31'
ORDER BY ts.slot_date, ts.start_time, v.name;


-- Requirement 4: Three-Table Join (proposal Q3)
-- Northside United's full Fall 2026 schedule (team 5): date, venue, opponent,
-- and the result of every game already played.
-- The second join to teams finds the opponent, whichever side they were on.
SELECT ts.slot_date AS date,
       ts.start_time AS time,
       v.name AS venue,
       CASE WHEN g.home_team_id = t.team_id THEN 'Home' ELSE 'Away' END AS home_away,
       opp.name AS opponent,
       CASE WHEN g.home_team_id = t.team_id THEN g.home_score ELSE g.away_score END AS goals_for,
       CASE WHEN g.home_team_id = t.team_id THEN g.away_score ELSE g.home_score END AS goals_against,
       CASE
           WHEN g.status = 'scheduled' THEN 'Upcoming'
           WHEN g.home_score = g.away_score THEN 'Tie'
           WHEN g.home_team_id = t.team_id AND g.home_score > g.away_score THEN 'Win'
           WHEN g.away_team_id = t.team_id AND g.away_score > g.home_score THEN 'Win'
           ELSE 'Loss'
       END AS result
FROM teams t
INNER JOIN games g ON t.team_id IN (g.home_team_id, g.away_team_id)
INNER JOIN teams opp ON opp.team_id = CASE WHEN g.home_team_id = t.team_id
                                           THEN g.away_team_id
                                           ELSE g.home_team_id END
INNER JOIN time_slots ts ON ts.slot_id = g.slot_id
INNER JOIN venues v ON v.venue_id = ts.venue_id
WHERE t.team_id = 5
ORDER BY ts.slot_date, ts.start_time;


-- Requirement 5: Aggregate Query
-- Fall 2026 season so far: games completed, total goals, average goals per
-- game, and the most goals scored in one game.
-- A game's season comes from the home team's division.
SELECT COUNT(*) AS games_completed,
       SUM(g.home_score + g.away_score) AS total_goals,
       ROUND(AVG(g.home_score + g.away_score), 2) AS avg_goals_per_game,
       MAX(g.home_score + g.away_score) AS most_goals_in_a_game
FROM games g
INNER JOIN teams t ON t.team_id = g.home_team_id
INNER JOIN divisions d ON d.division_id = t.division_id
INNER JOIN seasons s ON s.season_id = d.season_id
WHERE s.name = 'Fall 2026'
  AND g.status = 'completed';


-- Requirement 6: GROUP BY and HAVING (proposal Q2)
-- Fall 2026 top scorers (3 or more goals) and how many goals they average per
-- game played. Each player is one group, and HAVING drops everyone under 3 goals.
-- A player only has a stat row for games they played, so AVG is per game played.
SELECT p.first_name || ' ' || p.last_name AS player,
       COUNT(*) AS games_played,
       SUM(ps.goals) AS goals,
       ROUND(AVG(ps.goals), 2) AS goals_per_game
FROM player_game_stats ps
INNER JOIN players p ON p.player_id = ps.player_id
INNER JOIN games g ON g.game_id = ps.game_id
INNER JOIN teams t ON t.team_id = g.home_team_id
INNER JOIN divisions d ON d.division_id = t.division_id
INNER JOIN seasons s ON s.season_id = d.season_id
WHERE s.name = 'Fall 2026'
GROUP BY p.player_id, p.first_name, p.last_name
HAVING SUM(ps.goals) >= 3
ORDER BY goals DESC, goals_per_game DESC, player;


-- Requirement 7: Subquery (proposal Q5)
-- Upcoming games that still need a ref, with when and where they are so the
-- admin can find someone. The subquery lists every game that already has a ref.
SELECT ts.slot_date AS date,
       ts.start_time AS time,
       v.name AS venue,
       h.name AS home_team,
       a.name AS away_team
FROM games g
INNER JOIN time_slots ts ON ts.slot_id = g.slot_id
INNER JOIN venues v ON v.venue_id = ts.venue_id
INNER JOIN teams h ON h.team_id = g.home_team_id
INNER JOIN teams a ON a.team_id = g.away_team_id
WHERE g.status = 'scheduled'
  AND g.game_id NOT IN (SELECT game_id FROM game_referees)
ORDER BY ts.slot_date, ts.start_time;


-- Requirement 8: Set Operation (proposal Q6)
-- Players who were on a Summer 2026 team but haven't joined a Fall 2026 team,
-- so the admin can reach out before the season fills up.
-- EXCEPT keeps the players in the first set (Summer) who aren't in the second (Fall).
SELECT p.player_id, p.first_name, p.last_name, p.email
FROM players p
INNER JOIN rosters r ON r.player_id = p.player_id
INNER JOIN teams t ON t.team_id = r.team_id
INNER JOIN divisions d ON d.division_id = t.division_id
INNER JOIN seasons s ON s.season_id = d.season_id
WHERE s.name = 'Summer 2026'
EXCEPT
SELECT p.player_id, p.first_name, p.last_name, p.email
FROM players p
INNER JOIN rosters r ON r.player_id = p.player_id
INNER JOIN teams t ON t.team_id = r.team_id
INNER JOIN divisions d ON d.division_id = t.division_id
INNER JOIN seasons s ON s.season_id = d.season_id
WHERE s.name = 'Fall 2026'
ORDER BY last_name, first_name;


-- Requirement 9: View (proposal Q1)
-- Current Fall 2026 standings for each division, ranked by points and then goal
-- differential. Without division_standings this would need the UNION ALL of home
-- and away results, a LEFT JOIN, and the win, loss, tie, and points math every
-- time. With the view it's a short SELECT.
SELECT division,
       team,
       games_played AS gp,
       wins,
       losses,
       ties,
       goals_for AS gf,
       goals_against AS ga,
       goal_diff AS gd,
       points
FROM division_standings
WHERE season = 'Fall 2026'
ORDER BY division, points DESC, goal_diff DESC, goals_for DESC;
