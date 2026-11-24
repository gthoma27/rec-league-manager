-- Rec League Manager
-- insert_data.sql: sample data. Run after schema.sql.
-- All people, emails, phone numbers, and addresses are made up.
-- Emails use the reserved example.com domain and phones use the fictional 555-01xx range.
--
-- What the data covers:
--   Summer 2026 is last season (finished). Fall 2026 is the current season,
--   with 3 weeks played and 2 weeks scheduled. Winter 2027 has teams signed up
--   but no players or games yet. Spring 2027 is set up with no divisions yet.

PRAGMA foreign_keys = ON;

-- ============ seasons ============
INSERT INTO seasons (season_id, name, start_date, end_date) VALUES
    (1, 'Summer 2026', '2026-06-10', '2026-07-15'),
    (2, 'Fall 2026',   '2026-10-03', '2026-11-21'),
    (3, 'Winter 2027', '2027-01-09', '2027-02-27'),
    (4, 'Spring 2027', '2027-03-20', '2027-05-22');

-- ============ divisions ============
INSERT INTO divisions (division_id, season_id, name) VALUES
    (1, 1, 'Open'),
    (2, 2, 'Open'),
    (3, 2, 'Coed'),
    (4, 3, 'Open');

-- ============ teams ============
-- Teams are per season, so a returning team gets a new row each season.
INSERT INTO teams (team_id, division_id, name) VALUES
    -- Summer 2026 Open
    (1,  1, 'Riverside Rovers'),
    (2,  1, 'Northside United'),
    (3,  1, 'Sunset Strikers'),
    -- Fall 2026 Open
    (4,  2, 'Riverside Rovers'),
    (5,  2, 'Northside United'),
    (6,  2, 'Old City Athletic'),
    (7,  2, 'Lakeview FC'),
    -- Fall 2026 Coed
    (8,  3, 'Net Gains'),
    (9,  3, 'Sole Mates'),
    (10, 3, 'The Hat Tricks'),
    -- Winter 2027 Open (signed up early, no roster yet)
    (11, 4, 'Riverside Rovers'),
    (12, 4, 'Lakeview FC');

-- ============ players ============
-- Players 38 and 39 are new to the league and aren't on any team yet.
INSERT INTO players (player_id, first_name, last_name, email, phone) VALUES
    (1,  'Marcus',  'Bell',     'marcus.bell@example.com',     '555-0101'),
    (2,  'Diego',   'Ramirez',  'diego.ramirez@example.com',   '555-0102'),
    (3,  'Hannah',  'Cole',     'hannah.cole@example.com',     '555-0103'),
    (4,  'Tyler',   'Brooks',   'tyler.brooks@example.com',    '555-0104'),
    (5,  'Owen',    'Pratt',    'owen.pratt@example.com',      NULL),
    (6,  'Jamal',   'Turner',   'jamal.turner@example.com',    '555-0106'),
    (7,  'Lucas',   'Meyer',    'lucas.meyer@example.com',     '555-0107'),
    (8,  'Ethan',   'Shaw',     'ethan.shaw@example.com',      '555-0108'),
    (9,  'Andre',   'Wilson',   'andre.wilson@example.com',    '555-0109'),
    (10, 'Kevin',   'Nguyen',   'kevin.nguyen@example.com',    '555-0110'),
    (11, 'Sam',     'Patel',    'sam.patel@example.com',       '555-0111'),
    (12, 'Connor',  'O''Brien', 'connor.obrien@example.com',   '555-0112'),
    (13, 'Maya',    'Chen',     'maya.chen@example.com',       '555-0113'),
    (14, 'Jordan',  'Price',    'jordan.price@example.com',    NULL),
    (15, 'Caleb',   'Ross',     'caleb.ross@example.com',      '555-0115'),
    (16, 'Noah',    'Fischer',  'noah.fischer@example.com',    '555-0116'),
    (17, 'Isaac',   'Walsh',    'isaac.walsh@example.com',     '555-0117'),
    (18, 'Brandon', 'Lee',      'brandon.lee@example.com',     '555-0118'),
    (19, 'Victor',  'Silva',    'victor.silva@example.com',    '555-0119'),
    (20, 'Eli',     'Morgan',   'eli.morgan@example.com',      '555-0120'),
    (21, 'Trevor',  'Hughes',   'trevor.hughes@example.com',   '555-0121'),
    (22, 'Adrian',  'Lopez',    'adrian.lopez@example.com',    '555-0122'),
    (23, 'Chris',   'Dunn',     'chris.dunn@example.com',      '555-0123'),
    (24, 'Mateo',   'Garcia',   'mateo.garcia@example.com',    '555-0124'),
    (25, 'Nate',    'Collins',  'nate.collins@example.com',    '555-0125'),
    (26, 'Priya',   'Shah',     'priya.shah@example.com',      '555-0126'),
    (27, 'Emily',   'Foster',   'emily.foster@example.com',    NULL),
    (28, 'Daniel',  'Kim',      'daniel.kim@example.com',      '555-0128'),
    (29, 'Sofia',   'Rossi',    'sofia.rossi@example.com',     '555-0129'),
    (30, 'Rachel',  'Adams',    'rachel.adams@example.com',    '555-0130'),
    (31, 'Ben',     'Carter',   'ben.carter@example.com',      '555-0131'),
    (32, 'Olivia',  'Park',     'olivia.park@example.com',     '555-0132'),
    (33, 'Grace',   'Liu',      'grace.liu@example.com',       '555-0133'),
    (34, 'Aaron',   'Hill',     'aaron.hill@example.com',      '555-0134'),
    (35, 'Zoe',     'Martin',   'zoe.martin@example.com',      NULL),
    (36, 'Liam',    'Ortiz',    'liam.ortiz@example.com',      '555-0136'),
    (37, 'Chloe',   'Evans',    'chloe.evans@example.com',     '555-0137'),
    (38, 'Mason',   'Reed',     'mason.reed@example.com',      '555-0138'),
    (39, 'Ava',     'Torres',   'ava.torres@example.com',      NULL);

-- ============ rosters ============
-- Some things to notice:
--   Andre (9) moved from Northside United to Old City Athletic and is captain there now.
--   Sam (11) was Sunset Strikers captain in Summer but is not captain on Lakeview FC.
--   Hannah (3) and Isaac (17) each play on an Open team and a Coed team in Fall.
--   Owen (5), Kevin (10), Jordan (14), and Caleb (15) played Summer and haven't joined a Fall team.
INSERT INTO rosters (team_id, player_id, jersey_number, is_captain) VALUES
    -- Summer: Riverside Rovers
    (1, 1, 10, 1), (1, 2, 9, 0), (1, 3, 7, 0), (1, 4, 4, 0), (1, 5, 1, 0),
    -- Summer: Northside United
    (2, 6, 11, 1), (2, 7, 8, 0), (2, 8, 5, 0), (2, 9, 14, 0), (2, 10, 1, 0),
    -- Summer: Sunset Strikers
    (3, 11, 23, 1), (3, 12, 6, 0), (3, 13, 17, 0), (3, 14, 3, 0), (3, 15, 1, 0),
    -- Fall Open: Riverside Rovers
    (4, 1, 10, 1), (4, 2, 9, 0), (4, 3, 7, 0), (4, 4, 4, 0), (4, 16, 1, 0),
    -- Fall Open: Northside United
    (5, 6, 11, 1), (5, 7, 8, 0), (5, 8, 5, 0), (5, 17, 19, 0), (5, 18, 1, 0),
    -- Fall Open: Old City Athletic
    (6, 9, 14, 1), (6, 19, 10, 0), (6, 20, 2, 0), (6, 21, 21, 0), (6, 22, 1, 0),
    -- Fall Open: Lakeview FC
    (7, 11, 23, 0), (7, 12, 6, 0), (7, 23, 1, 0), (7, 24, 10, 1), (7, 25, 15, 0),
    -- Fall Coed: Net Gains
    (8, 13, 17, 1), (8, 26, 8, 0), (8, 27, 3, 0), (8, 28, 1, 0), (8, 3, 12, 0),
    -- Fall Coed: Sole Mates
    (9, 29, 5, 1), (9, 30, 9, 0), (9, 31, 1, 0), (9, 32, 11, 0), (9, 17, 19, 0),
    -- Fall Coed: The Hat Tricks
    (10, 33, 10, 1), (10, 34, 7, 0), (10, 35, 2, 0), (10, 36, 1, 0), (10, 37, 13, 0);

-- ============ venues ============
-- Northview Rec Center was just added for Winter and has no slots yet.
INSERT INTO venues (venue_id, name, address) VALUES
    (1, 'Riverside Park',          '1200 River Rd'),
    (2, 'Lakeview Sports Complex', '450 Lakeview Dr'),
    (3, 'Westgate Middle School',  '88 Westgate Blvd'),
    (4, 'Northview Rec Center',    '300 Northview Ave');

-- ============ time_slots ============
-- Summer games were Wednesday nights at Westgate.
-- Fall games are Saturdays with 4 slots a week (2 at Riverside, 2 at Lakeview).
-- Each Fall week uses 3 of the 4, and Nov 7 has slots set up but nothing booked yet.
INSERT INTO time_slots (slot_id, venue_id, slot_date, start_time) VALUES
    -- Summer 2026
    (1,  3, '2026-06-10', '18:30'),
    (2,  3, '2026-06-17', '18:30'),
    (3,  3, '2026-06-24', '18:30'),
    (4,  3, '2026-07-01', '18:30'),
    (5,  3, '2026-07-08', '18:30'),
    (6,  3, '2026-07-15', '18:30'),
    -- Fall 2026, Oct 3
    (7,  1, '2026-10-03', '09:00'),
    (8,  1, '2026-10-03', '10:30'),
    (9,  2, '2026-10-03', '09:00'),
    (10, 2, '2026-10-03', '10:30'),
    -- Oct 10
    (11, 1, '2026-10-10', '09:00'),
    (12, 1, '2026-10-10', '10:30'),
    (13, 2, '2026-10-10', '09:00'),
    (14, 2, '2026-10-10', '10:30'),
    -- Oct 17
    (15, 1, '2026-10-17', '09:00'),
    (16, 1, '2026-10-17', '10:30'),
    (17, 2, '2026-10-17', '09:00'),
    (18, 2, '2026-10-17', '10:30'),
    -- Oct 24
    (19, 1, '2026-10-24', '09:00'),
    (20, 1, '2026-10-24', '10:30'),
    (21, 2, '2026-10-24', '09:00'),
    (22, 2, '2026-10-24', '10:30'),
    -- Oct 31
    (23, 1, '2026-10-31', '09:00'),
    (24, 1, '2026-10-31', '10:30'),
    (25, 2, '2026-10-31', '09:00'),
    (26, 2, '2026-10-31', '10:30'),
    -- Nov 7 (nothing booked yet)
    (27, 1, '2026-11-07', '09:00'),
    (28, 1, '2026-11-07', '10:30'),
    (29, 2, '2026-11-07', '09:00'),
    (30, 2, '2026-11-07', '10:30');

-- ============ games ============
-- Fall Open games are at 9:00 and Coed games at 10:30, so players on two teams
-- never have two games at the same time.
-- The Coed division has 3 teams, so one team has a bye each week.
INSERT INTO games (game_id, slot_id, home_team_id, away_team_id, status, home_score, away_score) VALUES
    -- Summer 2026 (each team plays the others twice)
    (1,  1,  1, 2,  'completed', 3, 1),
    (2,  2,  3, 1,  'completed', 2, 2),
    (3,  3,  2, 3,  'completed', 1, 0),
    (4,  4,  2, 1,  'completed', 2, 4),
    (5,  5,  1, 3,  'completed', 1, 2),
    (6,  6,  3, 2,  'completed', 3, 1),
    -- Fall 2026, Oct 3
    (7,  7,  4, 5,  'completed', 2, 1),
    (8,  9,  6, 7,  'completed', 0, 0),
    (9,  8,  8, 9,  'completed', 3, 2),
    -- Oct 10
    (10, 11, 4, 6,  'completed', 4, 1),
    (11, 13, 7, 5,  'completed', 1, 3),
    (12, 14, 10, 8, 'completed', 2, 2),
    -- Oct 17
    (13, 15, 7, 4,  'completed', 2, 3),
    (14, 17, 5, 6,  'completed', 2, 2),
    (15, 16, 9, 10, 'completed', 1, 4),
    -- Oct 24 (upcoming)
    (16, 19, 5, 4,  'scheduled', NULL, NULL),
    (17, 21, 7, 6,  'scheduled', NULL, NULL),
    (18, 22, 9, 8,  'scheduled', NULL, NULL),
    -- Oct 31 (upcoming)
    (19, 23, 6, 4,  'scheduled', NULL, NULL),
    (20, 25, 5, 7,  'scheduled', NULL, NULL),
    (21, 24, 8, 10, 'scheduled', NULL, NULL);

-- ============ referees ============
-- Mike (5) is a new ref who hasn't worked a game yet.
INSERT INTO referees (referee_id, first_name, last_name, email, phone) VALUES
    (1, 'Paul',  'Henderson', 'paul.henderson@example.com', '555-0181'),
    (2, 'Lisa',  'Moreno',    'lisa.moreno@example.com',    '555-0182'),
    (3, 'Greg',  'Walters',   'greg.walters@example.com',   '555-0183'),
    (4, 'Tanya', 'Ward',      'tanya.ward@example.com',     NULL),
    (5, 'Mike',  'Sullivan',  'mike.sullivan@example.com',  '555-0185');

-- ============ game_referees ============
-- Upcoming games 18, 20, and 21 don't have a ref yet.
INSERT INTO game_referees (game_id, referee_id, role) VALUES
    -- Summer 2026
    (1, 1, 'center'),
    (2, 2, 'center'),
    (3, 1, 'center'),
    (4, 3, 'center'),
    (5, 2, 'center'),
    (6, 1, 'center'), (6, 3, 'assistant'),
    -- Fall 2026, completed
    (7, 1, 'center'), (7, 4, 'assistant'),
    (8, 2, 'center'),
    (9, 3, 'center'),
    (10, 2, 'center'), (10, 3, 'assistant'),
    (11, 4, 'center'),
    (12, 2, 'center'),
    (13, 3, 'center'), (13, 1, 'assistant'),
    (14, 2, 'center'), (14, 4, 'assistant'),
    (15, 3, 'center'),
    -- Fall 2026, upcoming
    (16, 1, 'center'),
    (17, 2, 'center'),
    (19, 3, 'center');

-- ============ player_game_stats ============
-- One row per player who played in a completed game. Players who missed a game
-- have no row for it. Goals for each team add up to that team's score.
INSERT INTO player_game_stats (game_id, player_id, goals, assists, fouls) VALUES
    -- Game 1: Riverside 3, Northside 1
    (1, 1, 1, 1, 0), (1, 2, 2, 0, 1), (1, 3, 0, 1, 0), (1, 4, 0, 0, 1), (1, 5, 0, 0, 0),
    (1, 6, 1, 0, 0), (1, 7, 0, 1, 1), (1, 8, 0, 0, 2), (1, 9, 0, 0, 0), (1, 10, 0, 0, 0),
    -- Game 2: Sunset 2, Riverside 2 (Owen missed it)
    (2, 11, 1, 1, 0), (2, 12, 1, 0, 1), (2, 13, 0, 1, 0), (2, 14, 0, 0, 1), (2, 15, 0, 0, 0),
    (2, 1, 0, 1, 0), (2, 2, 1, 0, 0), (2, 3, 1, 0, 0), (2, 4, 0, 0, 2),
    -- Game 3: Northside 1, Sunset 0
    (3, 6, 0, 1, 0), (3, 7, 1, 0, 0), (3, 8, 0, 0, 1), (3, 9, 0, 0, 0), (3, 10, 0, 0, 0),
    (3, 11, 0, 0, 1), (3, 12, 0, 0, 0), (3, 13, 0, 0, 0), (3, 14, 0, 0, 1), (3, 15, 0, 0, 0),
    -- Game 4: Northside 2, Riverside 4 (Kevin missed it)
    (4, 6, 1, 0, 0), (4, 7, 0, 1, 0), (4, 8, 0, 0, 1), (4, 9, 1, 1, 1),
    (4, 1, 1, 2, 0), (4, 2, 2, 0, 0), (4, 3, 1, 1, 0), (4, 4, 0, 0, 1), (4, 5, 0, 0, 0),
    -- Game 5: Riverside 1, Sunset 2
    (5, 1, 0, 0, 1), (5, 2, 1, 0, 0), (5, 3, 0, 1, 0), (5, 4, 0, 0, 0), (5, 5, 0, 0, 0),
    (5, 11, 1, 0, 0), (5, 12, 0, 1, 1), (5, 13, 1, 1, 0), (5, 14, 0, 0, 0), (5, 15, 0, 0, 0),
    -- Game 6: Sunset 3, Northside 1
    (6, 11, 2, 0, 0), (6, 12, 0, 1, 0), (6, 13, 1, 1, 0), (6, 14, 0, 0, 2), (6, 15, 0, 0, 0),
    (6, 6, 0, 0, 1), (6, 7, 0, 0, 0), (6, 8, 0, 0, 0), (6, 9, 1, 0, 0), (6, 10, 0, 0, 0),
    -- Game 7: Riverside 2, Northside 1
    (7, 1, 1, 0, 0), (7, 2, 1, 1, 0), (7, 3, 0, 1, 1), (7, 4, 0, 0, 1), (7, 16, 0, 0, 0),
    (7, 6, 0, 0, 0), (7, 7, 1, 0, 1), (7, 8, 0, 0, 2), (7, 17, 0, 1, 0), (7, 18, 0, 0, 0),
    -- Game 8: Old City 0, Lakeview 0
    (8, 9, 0, 0, 1), (8, 19, 0, 0, 0), (8, 20, 0, 0, 1), (8, 21, 0, 0, 0), (8, 22, 0, 0, 0),
    (8, 11, 0, 0, 0), (8, 12, 0, 0, 2), (8, 23, 0, 0, 0), (8, 24, 0, 0, 1), (8, 25, 0, 0, 0),
    -- Game 9: Net Gains 3, Sole Mates 2
    (9, 13, 1, 1, 0), (9, 26, 1, 0, 0), (9, 27, 0, 1, 0), (9, 28, 0, 0, 0), (9, 3, 1, 0, 0),
    (9, 29, 1, 0, 0), (9, 30, 1, 1, 0), (9, 31, 0, 0, 1), (9, 32, 0, 1, 0), (9, 17, 0, 0, 0),
    -- Game 10: Riverside 4, Old City 1 (Adrian missed it)
    (10, 1, 1, 1, 0), (10, 2, 2, 1, 0), (10, 3, 1, 1, 0), (10, 4, 0, 0, 1), (10, 16, 0, 0, 0),
    (10, 9, 1, 0, 1), (10, 19, 0, 1, 0), (10, 20, 0, 0, 2), (10, 21, 0, 0, 0),
    -- Game 11: Lakeview 1, Northside 3
    (11, 11, 1, 0, 0), (11, 12, 0, 1, 1), (11, 23, 0, 0, 0), (11, 24, 0, 0, 1), (11, 25, 0, 0, 0),
    (11, 6, 1, 1, 0), (11, 7, 1, 0, 0), (11, 8, 0, 0, 1), (11, 17, 1, 1, 0), (11, 18, 0, 0, 0),
    -- Game 12: Hat Tricks 2, Net Gains 2 (Hannah missed it)
    (12, 33, 1, 0, 0), (12, 34, 1, 1, 0), (12, 35, 0, 1, 1), (12, 36, 0, 0, 0), (12, 37, 0, 0, 0),
    (12, 13, 2, 0, 0), (12, 26, 0, 1, 0), (12, 27, 0, 0, 1), (12, 28, 0, 0, 0),
    -- Game 13: Lakeview 2, Riverside 3
    (13, 11, 1, 0, 0), (13, 12, 0, 1, 0), (13, 23, 0, 0, 0), (13, 24, 1, 1, 1), (13, 25, 0, 0, 1),
    (13, 1, 0, 2, 0), (13, 2, 2, 0, 1), (13, 3, 1, 0, 0), (13, 4, 0, 0, 0), (13, 16, 0, 0, 0),
    -- Game 14: Northside 2, Old City 2
    (14, 6, 1, 0, 0), (14, 7, 0, 1, 0), (14, 8, 0, 0, 1), (14, 17, 1, 0, 0), (14, 18, 0, 0, 0),
    (14, 9, 1, 1, 0), (14, 19, 1, 0, 0), (14, 20, 0, 0, 1), (14, 21, 0, 1, 1), (14, 22, 0, 0, 0),
    -- Game 15: Sole Mates 1, Hat Tricks 4
    (15, 29, 0, 0, 0), (15, 30, 1, 0, 0), (15, 31, 0, 0, 1), (15, 32, 0, 1, 0), (15, 17, 0, 0, 1),
    (15, 33, 2, 1, 0), (15, 34, 1, 1, 0), (15, 35, 0, 1, 0), (15, 36, 0, 0, 0), (15, 37, 1, 0, 0);
