"""Rec League Manager: a Flask web app for the rec_league.db SQLite database.

Start it with:  python app.py   (see README.md for setup)

This file holds the web pages (routes), the league rules each form checks
before saving, and the error pages. All SQL is in queries.py.
"""
import os
import secrets
import sqlite3
import sys
from datetime import datetime

from flask import Flask, abort, flash, redirect, render_template, request, url_for

import queries
from config import DB_PATH, HOST, get_port
from db import DatabaseNotReady, close_db, get_db, missing_objects
from validators import parse_checkbox, parse_choice, parse_id, parse_int, parse_text

app = Flask(__name__)
# Only used to sign the short success and error messages shown after a form
# is saved. A random key is fine because nothing needs to survive a restart.
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(16)
# Close each request's database connection when the request ends.
app.teardown_appcontext(close_db)

MAX_SCORE = 99
MAX_STAT = 99
MAX_SEARCH_LENGTH = 50
GAME_STATUSES = ('scheduled', 'completed')
REFEREE_ROLES = ('center', 'assistant')
STAT_FIELDS = ('goals', 'assists', 'fouls')

# Friendly messages for constraint errors the database might still raise if
# two people change the same thing at once. Matched against SQLite's message.
INTEGRITY_MESSAGES = (
    ('rosters.team_id, rosters.jersey_number', 'That jersey number is already taken on this team.'),
    ('rosters.team_id, rosters.player_id', 'That player is already on this team.'),
    ('games.slot_id', 'That time slot already has a game. Pick a different slot.'),
    ('game_referees.game_id, game_referees.referee_id', 'That referee is already assigned to this game.'),
    ('player_game_stats.game_id, player_game_stats.player_id',
     'Stats for one of these players were already entered for this game.'),
    ('FOREIGN KEY constraint failed', 'Something you picked no longer exists. Reload the page and try again.'),
    ('CHECK constraint failed', 'One of the values is outside the allowed range.'),
)


# ---------------------------------------------------------------- small helpers

@app.template_filter('nice_date')
def nice_date(value):
    """'2026-10-24' becomes 'Sat Oct 24, 2026'."""
    try:
        day = datetime.strptime(value, '%Y-%m-%d')
    except (TypeError, ValueError):
        return value
    return f'{day:%a %b} {day.day}, {day.year}'


def full_name(row):
    return f'{row["first_name"]} {row["last_name"]}'


def plural(count, word):
    return f'{count} {word}' if count == 1 else f'{count} {word}s'


def friendly_integrity_message(error):
    text = str(error)
    for key, message in INTEGRITY_MESSAGES:
        if key in text:
            return message + ' Nothing was saved.'
    return 'That change breaks one of the database rules. Nothing was saved.'


def selected_season(conn, raw_season_id):
    """The season picked in a form or URL, or the default season if none was picked.

    Returns (season, error message or None). An invalid choice falls back to
    the default season so the page still shows something useful.
    """
    if (raw_season_id or '').strip() == '':
        return queries.default_season(conn), None
    errors = []
    season_id = parse_id(raw_season_id, 'season', errors)
    season = queries.get_season(conn, season_id) if season_id else None
    if season is None:
        message = errors[0] if errors else 'That season does not exist.'
        return queries.default_season(conn), message + ' Showing the current season instead.'
    return season, None


def get_team_or_404(conn, team_id):
    team = queries.get_team(conn, team_id)
    if team is None:
        abort(404, description=f'Team {team_id} was not found.')
    return team


def get_game_or_404(conn, game_id):
    game = queries.get_game(conn, game_id)
    if game is None:
        abort(404, description=f'Game {game_id} was not found. It may have been canceled.')
    return game


def require_scheduled(game, action):
    """Completed games are final. Returns a redirect with a message, or None if the game is upcoming."""
    if game['status'] != 'scheduled':
        flash(f'Game {game["game_id"]} is already completed, so it can\'t be {action}.', 'error')
        return redirect(url_for('game_detail', game_id=game['game_id']))
    return None


# ---------------------------------------------------------------- league rules

def roster_rule_errors(conn, team, player_id, jersey_number, is_captain):
    """Checks before adding a player to a roster (operation 3)."""
    player = queries.get_player(conn, player_id)
    if player is None:
        return ['That player does not exist.']
    errors = []
    name = full_name(player)
    current_team = queries.player_team_in_division(conn, player_id, team['division_id'])
    if current_team is not None:
        errors.append(f'{name} is already on {current_team["name"]} in the {team["season"]} '
                      f'{team["division"]} division. A player can only be on one team per division.')
    owner = queries.jersey_owner(conn, team['team_id'], jersey_number)
    if owner is not None:
        errors.append(f'Jersey #{jersey_number} is already worn by {owner["player"]} on {team["name"]}.')
    if is_captain:
        captain = queries.team_captain(conn, team['team_id'])
        if captain is not None:
            errors.append(f'{team["name"]} already has a captain ({captain["player"]}).')
    return errors


def slot_rule_errors(conn, slot_id, season_name, season_start, season_end,
                     home_team_id, away_team_id, ignore_game_id=0):
    """Checks a time slot before a game is scheduled or rescheduled into it."""
    slot = queries.get_slot(conn, slot_id)
    if slot is None:
        return ['That time slot does not exist.']
    errors = []
    when = f'{nice_date(slot["slot_date"])} at {slot["start_time"]}'
    if slot['booked_game_id'] == ignore_game_id:
        errors.append('The game is already in that time slot. Pick a different one.')
    elif slot['booked_game_id'] is not None:
        errors.append(f'{slot["venue"]} is already booked {when} (game {slot["booked_game_id"]}).')
    if not season_start <= slot['slot_date'] <= season_end:
        errors.append(f'{when} is outside the {season_name} season '
                      f'({nice_date(season_start)} to {nice_date(season_end)}).')
    for row in queries.team_conflicts(conn, slot_id, home_team_id, away_team_id, ignore_game_id):
        errors.append(f'{row["team"]} already plays {when} (game {row["game_id"]}).')
    for row in queries.player_conflicts(conn, slot_id, home_team_id, away_team_id, ignore_game_id):
        errors.append(f'{row["player"]} also plays for {row["other_team"]}, '
                      f'which already has a game {when} (game {row["game_id"]}).')
    return errors


def new_game_rule_errors(conn, season, home_team_id, away_team_id, slot_id):
    """Checks before scheduling a new game (extra operation)."""
    home = queries.get_team(conn, home_team_id)
    away = queries.get_team(conn, away_team_id)
    if home is None or away is None:
        return ['That team does not exist.']
    errors = []
    if home_team_id == away_team_id:
        errors.append('A team can\'t play itself. Pick two different teams.')
    if home['season_id'] != season['season_id'] or away['season_id'] != season['season_id']:
        errors.append(f'Both teams have to be in the {season["name"]} season.')
    elif home['division_id'] != away['division_id']:
        errors.append(f'{home["name"]} ({home["division"]}) and {away["name"]} ({away["division"]}) '
                      f'are in different divisions.')
    errors += slot_rule_errors(conn, slot_id, season['name'], season['start_date'],
                               season['end_date'], home_team_id, away_team_id)
    return errors


def referee_rule_errors(conn, game, referee_id, role):
    """Checks before assigning a referee to a game (extra operation)."""
    referee = queries.get_referee(conn, referee_id)
    if referee is None:
        return ['That referee does not exist.']
    errors = []
    name = full_name(referee)
    if queries.referee_on_game(conn, game['game_id'], referee_id) is not None:
        errors.append(f'{name} is already assigned to this game.')
    elif role == 'center' and queries.game_has_center_ref(conn, game['game_id']):
        errors.append('This game already has a center referee. Add this person as an assistant instead.')
    clash = queries.referee_conflict(conn, referee_id, game['game_id'])
    if clash is not None:
        errors.append(f'{name} is already working game {clash["game_id"]} at the same date and time.')
    return errors


def read_result_form(form, game, home_roster, away_roster):
    """Reads and checks the final score form (operation 6).

    Returns (home_score, away_score, stat_rows, errors). stat_rows has one
    (player_id, goals, assists, fouls) for every player marked as played.
    Player IDs come from the rosters in the database, not from the form.
    """
    errors = []
    home_score = parse_int(form.get('home_score'), f'{game["home_team"]} score',
                           errors, minimum=0, maximum=MAX_SCORE)
    away_score = parse_int(form.get('away_score'), f'{game["away_team"]} score',
                           errors, minimum=0, maximum=MAX_SCORE)
    stat_rows = []
    sides = ((game['home_team'], home_roster, home_score), (game['away_team'], away_roster, away_score))
    for team_name, roster, score in sides:
        if not roster:
            errors.append(f'{team_name} has no players on its roster, so its stats can\'t be '
                          f'entered. Add players to the roster first.')
            continue
        played_count = goals_total = assists_total = 0
        bad_value = False
        for player in roster:
            player_id = player['player_id']
            name = full_name(player)
            line = [parse_int(form.get(f'{stat}_{player_id}'), f'{name} {stat}', errors,
                              minimum=0, maximum=MAX_STAT, required=False, default=0)
                    for stat in STAT_FIELDS]
            if None in line:
                bad_value = True
                continue
            goals, assists, fouls = line
            if not parse_checkbox(form, f'played_{player_id}'):
                if goals or assists or fouls:
                    errors.append(f'{name} has stats but isn\'t marked as played.')
                continue
            played_count += 1
            goals_total += goals
            assists_total += assists
            stat_rows.append((player_id, goals, assists, fouls))
        if played_count == 0 and not bad_value:
            errors.append(f'Mark at least one {team_name} player as played.')
        # Totals are only checked once every number for the team is valid,
        # otherwise the sums would be wrong and the message confusing.
        if score is not None and not bad_value:
            if goals_total != score:
                errors.append(f'{team_name} player goals add up to {goals_total}, '
                              f'but the {team_name} score is {score}.')
            if assists_total > score:
                errors.append(f'{team_name} has {assists_total} assists but only {score} goals. '
                              f'Each goal can have at most one assist.')
    return home_score, away_score, stat_rows, errors


# ---------------------------------------------------------------- pages

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/players')
def players():
    """Operation 1 (search/browse): find players by name or email. A blank search lists everyone."""
    errors = []
    raw_search = request.args.get('q', '')
    search_text = parse_text(raw_search, 'Search text', errors, max_length=MAX_SEARCH_LENGTH)
    rows = [] if errors else queries.search_players(get_db(), search_text)
    return render_template('players.html', q=raw_search.strip(), players=rows,
                           errors=errors), (400 if errors else 200)


@app.route('/players/<int:player_id>')
def player_detail(player_id):
    conn = get_db()
    player = queries.get_player(conn, player_id)
    if player is None:
        abort(404, description=f'Player {player_id} was not found.')
    return render_template('player_detail.html', player=player,
                           teams=queries.player_teams(conn, player_id),
                           stats=queries.player_season_stats(conn, player_id))


@app.route('/teams')
def teams():
    conn = get_db()
    season, season_error = selected_season(conn, request.args.get('season_id'))
    rows = queries.list_teams(conn, season['season_id']) if season else []
    return render_template('teams.html', seasons=queries.list_seasons(conn), season=season,
                           teams=rows, errors=[season_error] if season_error else [])


@app.route('/teams/<int:team_id>')
def team_detail(team_id):
    """Operation 2 (related data): a team's roster and its schedule with results."""
    conn = get_db()
    team = get_team_or_404(conn, team_id)
    return render_template('team_detail.html', team=team,
                           roster=queries.team_roster(conn, team_id),
                           schedule=queries.team_schedule(conn, team_id))


@app.route('/teams/<int:team_id>/roster/add', methods=['GET', 'POST'])
def roster_add(team_id):
    """Operation 3 (add): put a player on a team's roster with a jersey number."""
    conn = get_db()
    team = get_team_or_404(conn, team_id)
    errors = []
    if request.method == 'POST':
        player_id = parse_id(request.form.get('player_id'), 'player', errors)
        jersey_number = parse_int(request.form.get('jersey_number'), 'Jersey number', errors,
                                  minimum=0, maximum=99)
        is_captain = parse_checkbox(request.form, 'is_captain')
        if not errors:
            errors = roster_rule_errors(conn, team, player_id, jersey_number, is_captain)
        if not errors:
            try:
                queries.add_roster_player(conn, team_id, player_id, jersey_number, is_captain)
            except sqlite3.IntegrityError as error:
                errors.append(friendly_integrity_message(error))
            else:
                player = queries.get_player(conn, player_id)
                role = ' as captain' if is_captain else ''
                flash(f'Added {full_name(player)} to {team["name"]} wearing #{jersey_number}{role}.',
                      'success')
                return redirect(url_for('team_detail', team_id=team_id))
    return render_template('roster_add.html', team=team,
                           players=queries.players_not_in_division(conn, team['division_id']),
                           roster=queries.team_roster(conn, team_id),
                           form=request.form, errors=errors), (400 if errors else 200)


@app.route('/games')
def games():
    conn = get_db()
    season, season_error = selected_season(conn, request.args.get('season_id'))
    errors = [season_error] if season_error else []
    status = parse_choice(request.args.get('status'), 'Status', errors, GAME_STATUSES, required=False)
    if status is None:
        status = ''  # ignore a bad filter and show every game
    needs_ref = parse_checkbox(request.args, 'needs_ref')
    rows = queries.list_games(conn, season['season_id'], status or None, needs_ref) if season else []
    return render_template('games.html', seasons=queries.list_seasons(conn), season=season,
                           games=rows, status=status, needs_ref=needs_ref, errors=errors)


def render_game_detail(conn, game, errors=(), status_code=200):
    box_score = queries.game_box_score(conn, game['game_id']) if game['status'] == 'completed' else []
    return render_template('game_detail.html', game=game,
                           refs=queries.game_referees(conn, game['game_id']),
                           all_refs=queries.list_referees(conn), box_score=box_score,
                           roles=REFEREE_ROLES, form=request.form, errors=errors), status_code


@app.route('/games/<int:game_id>')
def game_detail(game_id):
    conn = get_db()
    return render_game_detail(conn, get_game_or_404(conn, game_id))


def render_change_page(conn, game, errors=(), status_code=200):
    slots = queries.open_slots(conn, game['season_start'], game['season_end'])
    return render_template('game_change.html', game=game, slots=slots,
                           form=request.form, errors=errors), status_code


@app.route('/games/<int:game_id>/change')
def game_change(game_id):
    """Operation 4 (update/delete): the page with the reschedule and cancel forms."""
    conn = get_db()
    game = get_game_or_404(conn, game_id)
    stop = require_scheduled(game, 'rescheduled or canceled')
    if stop:
        return stop
    return render_change_page(conn, game)


@app.route('/games/<int:game_id>/reschedule', methods=['POST'])
def game_reschedule(game_id):
    """Operation 4 (update): move an upcoming game to an open time slot."""
    conn = get_db()
    game = get_game_or_404(conn, game_id)
    stop = require_scheduled(game, 'rescheduled')
    if stop:
        return stop
    errors = []
    slot_id = parse_id(request.form.get('slot_id'), 'new time slot', errors)
    if not errors:
        errors = slot_rule_errors(conn, slot_id, game['season'], game['season_start'],
                                  game['season_end'], game['home_team_id'],
                                  game['away_team_id'], ignore_game_id=game_id)
    if errors:
        return render_change_page(conn, game, errors, 400)
    try:
        changed = queries.reschedule_game(conn, game_id, slot_id)
    except sqlite3.IntegrityError as error:
        return render_change_page(conn, game, [friendly_integrity_message(error)], 400)
    if changed == 0:
        flash('That game was completed or canceled before your change was saved. Nothing was changed.',
              'error')
        return redirect(url_for('games'))
    slot = queries.get_slot(conn, slot_id)
    flash(f'Game {game_id} moved to {nice_date(slot["slot_date"])} at {slot["start_time"]}, '
          f'{slot["venue"]}. Its old slot is open again.', 'success')
    return redirect(url_for('game_detail', game_id=game_id))


@app.route('/games/<int:game_id>/cancel', methods=['POST'])
def game_cancel(game_id):
    """Operation 4 (delete): cancel an upcoming game, which frees its slot and removes its refs."""
    conn = get_db()
    game = get_game_or_404(conn, game_id)
    stop = require_scheduled(game, 'canceled')
    if stop:
        return stop
    if not parse_checkbox(request.form, 'confirm'):
        return render_change_page(conn, game, ['Tick the box to confirm you want to cancel this game.'], 400)
    ref_count = queries.count_game_referees(conn, game_id)
    if queries.cancel_game(conn, game_id) == 0:
        flash('That game was completed or canceled before your change was saved. Nothing was changed.',
              'error')
        return redirect(url_for('games'))
    refs_note = f' {plural(ref_count, "referee assignment")} removed.' if ref_count else ''
    flash(f'Canceled game {game_id} ({game["home_team"]} vs {game["away_team"]}). '
          f'The {game["venue"]} slot on {nice_date(game["slot_date"])} at {game["start_time"]} '
          f'is open again.{refs_note}', 'success')
    return redirect(url_for('games', season_id=game['season_id']))


@app.route('/games/<int:game_id>/result', methods=['GET', 'POST'])
def game_result(game_id):
    """Operation 6 (additional): enter the final score and player stats in one transaction."""
    conn = get_db()
    game = get_game_or_404(conn, game_id)
    stop = require_scheduled(game, 'entered again')
    if stop:
        return stop
    home_roster = queries.team_roster(conn, game['home_team_id'])
    away_roster = queries.team_roster(conn, game['away_team_id'])
    errors = []
    if request.method == 'POST':
        home_score, away_score, stat_rows, errors = read_result_form(
            request.form, game, home_roster, away_roster)
        if not errors:
            try:
                queries.record_result(conn, game_id, home_score, away_score, stat_rows)
            except queries.GameNotScheduledError:
                flash('Someone else completed or canceled this game while you were entering it. '
                      'Nothing was saved.', 'error')
                return redirect(url_for('games', season_id=game['season_id']))
            except sqlite3.IntegrityError as error:
                errors.append(friendly_integrity_message(error))
            else:
                flash(f'Final score saved: {game["home_team"]} {home_score}, '
                      f'{game["away_team"]} {away_score}. '
                      f'Added {plural(len(stat_rows), "player stat line")}.', 'success')
                return redirect(url_for('game_detail', game_id=game_id))
    form = request.form if request.method == 'POST' else None
    return render_template('game_result.html', game=game, home_roster=home_roster,
                           away_roster=away_roster, stat_fields=STAT_FIELDS, form=form,
                           errors=errors), (400 if errors else 200)


@app.route('/games/new', methods=['GET', 'POST'])
def game_new():
    """Extra operation (proposal operation 3): schedule a new game in an open slot."""
    conn = get_db()
    values = request.form if request.method == 'POST' else request.args
    season, season_error = selected_season(conn, values.get('season_id'))
    errors = [season_error] if season_error else []
    if season is None:
        abort(404, description='There are no seasons in the database yet.')
    if request.method == 'POST' and not errors:
        home_team_id = parse_id(request.form.get('home_team_id'), 'home team', errors)
        away_team_id = parse_id(request.form.get('away_team_id'), 'away team', errors)
        slot_id = parse_id(request.form.get('slot_id'), 'time slot', errors)
        if not errors:
            errors = new_game_rule_errors(conn, season, home_team_id, away_team_id, slot_id)
        if not errors:
            try:
                game_id = queries.schedule_game(conn, slot_id, home_team_id, away_team_id)
            except sqlite3.IntegrityError as error:
                errors.append(friendly_integrity_message(error))
            else:
                flash(f'Scheduled game {game_id}. Assign a referee below.', 'success')
                return redirect(url_for('game_detail', game_id=game_id))
    return render_template('game_new.html', seasons=queries.list_seasons(conn), season=season,
                           teams=queries.list_teams(conn, season['season_id']),
                           slots=queries.open_slots(conn, season['start_date'], season['end_date']),
                           form=request.form, errors=errors), (400 if errors else 200)


@app.route('/games/<int:game_id>/referees', methods=['POST'])
def game_assign_referee(game_id):
    """Extra operation (proposal operation 4): assign a referee to an upcoming game."""
    conn = get_db()
    game = get_game_or_404(conn, game_id)
    stop = require_scheduled(game, 'given another referee')
    if stop:
        return stop
    errors = []
    referee_id = parse_id(request.form.get('referee_id'), 'referee', errors)
    role = parse_choice(request.form.get('role'), 'Role', errors, REFEREE_ROLES)
    if not errors:
        errors = referee_rule_errors(conn, game, referee_id, role)
    if not errors:
        try:
            queries.assign_referee(conn, game_id, referee_id, role)
        except sqlite3.IntegrityError as error:
            errors.append(friendly_integrity_message(error))
        else:
            referee = queries.get_referee(conn, referee_id)
            flash(f'Assigned {full_name(referee)} as the {role} referee.', 'success')
            return redirect(url_for('game_detail', game_id=game_id))
    return render_game_detail(conn, game, errors, 400)


@app.route('/reports')
def reports():
    """Operation 5 (report): season summary, standings from the view, and top scorers."""
    conn = get_db()
    season, season_error = selected_season(conn, request.args.get('season_id'))
    errors = [season_error] if season_error else []
    min_goals = parse_int(request.args.get('min_goals'), 'Minimum goals', errors,
                          minimum=0, maximum=MAX_STAT, required=False, default=2)
    if min_goals is None:
        min_goals = 2  # fall back to the default after showing the error
    summary = standings = scorers = None
    if season:
        summary = queries.season_summary(conn, season['season_id'])
        standings = queries.standings(conn, season['name'])
        scorers = queries.top_scorers(conn, season['season_id'], min_goals)
    return render_template('reports.html', seasons=queries.list_seasons(conn), season=season,
                           summary=summary, standings=standings, scorers=scorers,
                           min_goals=min_goals, errors=errors)


# ---------------------------------------------------------------- error pages
# These keep raw errors and stack traces off the screen. Database errors are
# still written to the terminal so they can be looked into.

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', title='Not found', message=error.description), 404


@app.errorhandler(405)
def method_not_allowed(error):
    return render_template('error.html', title='Not allowed',
                           message='That page can\'t be used that way. Use the links and buttons '
                                   'in the app.'), 405


@app.errorhandler(DatabaseNotReady)
def database_not_ready(error):
    return render_template('error.html', title='Database not set up', message=str(error)), 500


@app.errorhandler(sqlite3.Error)
def database_error(error):
    app.logger.exception('Database error')
    return render_template('error.html', title='Database error',
                           message='The database couldn\'t finish that request, so nothing was '
                                   'changed. Try again in a moment. If it keeps happening, rebuild '
                                   'the database with "python init_db.py".'), 500


@app.errorhandler(500)
def server_error(error):
    return render_template('error.html', title='Something went wrong',
                           message='The app ran into an unexpected problem and nothing was '
                                   'changed.'), 500


def main():
    """Check the database is ready, then start the web server."""
    try:
        missing = missing_objects()
    except DatabaseNotReady as error:
        print(error)
        return 1
    except sqlite3.Error as error:
        print(f'Could not open the database at {DB_PATH}: {error}')
        return 1
    if missing:
        print(f'The database at {DB_PATH} is missing: {", ".join(missing)}.')
        print('Run "python init_db.py" to build it.')
        return 1
    port = get_port()
    print(f'Rec League Manager is running. Open http://{HOST}:{port} in your browser.')
    print('Press Ctrl+C to stop.')
    app.run(host=HOST, port=port)
    return 0


if __name__ == '__main__':
    sys.exit(main())
