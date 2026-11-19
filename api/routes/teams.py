"""Team/game browsing using the existing film and player-link catalog."""
import os

from flask import Blueprint, jsonify, request
from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import with_expression

from dataclass.games import Game
from dataclass.teams import Team
from routes.engine import open_session
from routes.players import clock_label, duration_label, serve_clip_row
from utils.labels import extract_attributes

bp = Blueprint('teams', __name__)
CATEGORIES = {
    'three_pointer': 'Three-pointers', 'dunk': 'Dunks', 'layup': 'Layups',
    'shot': 'Shots', 'rebound': 'Rebounds', 'steal': 'Steals', 'block': 'Blocks',
    'assist': 'Assists', 'foul': 'Fouls', 'turnover': 'Turnovers',
    'free_throw': 'Free throws',
}
# Older imports omit clips.team_id. Count a linked player's involvement rather
# than guessing a team from a player's abbreviated name in the description.
TEAM_CLIP = """(c.team_id = :team_id OR (c.team_id IS NULL AND EXISTS (
    SELECT 1 FROM clip_players cp JOIN players p ON p.id = cp.player_id
    WHERE cp.clip_id = c.id AND p.team_id = :team_id)))"""


def connect():
    """Open a read-only session. Callers close it with a `with` block."""
    if not os.environ.get("DATABASE_URL_SQLALCHEMY"):
        return None, (jsonify(error="Player library is unavailable."), 503)
    session = None
    try:
        session = open_session()
        session.execute(text("SET TRANSACTION READ ONLY"))
        session.execute(text("SET LOCAL statement_timeout = '8s'"))
    except Exception:
        if session is not None:
            session.close()
        return None, (jsonify(error="Database connection unavailable."), 503)
    return session, None


def cursor_value():
    raw = request.args.get('cursor', '')
    if not raw:
        return None
    value = int(raw)
    if value < 1 or value > 9223372036854775807:
        raise ValueError('Invalid cursor')
    return value


def clip_categories(description, action, subtype, roles):
    inferred = extract_attributes(description, '')
    values = {action or inferred.get('action_type'), subtype or inferred.get('shot_subtype')}
    values.update(roles or [])
    return [key for key in CATEGORIES if key in values]


@bp.get('/api/teams')
def list_teams():
    session, error = connect()
    if error:
        return error
    statement = (
        select(Team)
        .outerjoin(Game, or_(Game.home_team_id == Team.id, Game.away_team_id == Team.id))
        .options(with_expression(Team.games, func.count(Game.id.distinct())))
        .group_by(Team.id)
        .order_by(Team.city, Team.name)
    )
    with session:
        teams = session.scalars(statement).all()
        return jsonify(teams=teams)


@bp.get('/api/teams/<int:team_id>/games')
def list_games(team_id):
    try:
        cursor = cursor_value()
    except ValueError:
        return jsonify(error='Invalid game cursor.'), 400
    session, error = connect()
    if error:
        return error
    with session:
        if not session.execute(text('SELECT id FROM teams WHERE id = :team_id'), {'team_id': team_id}).first():
            return jsonify(error='Team not found.'), 404
        mark = None
        if cursor:
            mark = session.execute(text('''SELECT game_date, id FROM games
                WHERE id = :cursor AND :team_id IN (home_team_id, away_team_id)'''),
                {'cursor': cursor, 'team_id': team_id}).first()
            if mark is None:
                return jsonify(error='Cursor game not found.'), 404
        params = {'team_id': team_id}
        after = ''
        if mark:
            after = 'AND (g.game_date, g.id) < (:mark_date, :mark_id)'
            params['mark_date'] = mark[0]
            params['mark_id'] = mark[1]
        rows = session.execute(text(f'''
            SELECT g.id, g.game_date, g.season, ht.abbr, at.abbr,
                COUNT(c.id), COUNT(c.id) FILTER (WHERE {TEAM_CLIP})
            FROM games g JOIN teams ht ON ht.id = g.home_team_id
            JOIN teams at ON at.id = g.away_team_id JOIN clips c ON c.game_id = g.id
            WHERE :team_id IN (g.home_team_id, g.away_team_id) {after}
            GROUP BY g.id, ht.abbr, at.abbr
            ORDER BY g.game_date DESC, g.id DESC LIMIT 25
        '''), params).all()
    return jsonify(games=[dict(id=r[0], date=r[1].isoformat(), season=r[2], home=r[3], away=r[4],
                               clips=r[5], team_clips=r[6]) for r in rows[:24]],
                   cursor=rows[23][0] if len(rows) > 24 else None)


@bp.get('/api/teams/<int:team_id>/games/<int:game_id>/clips')
def list_game_clips(team_id, game_id):
    try:
        cursor = cursor_value()
    except ValueError:
        return jsonify(error='Invalid clip cursor.'), 400
    scope = request.args.get('scope', 'team')
    categories = set(filter(None, request.args.get('categories', '').split(',')))
    if scope not in ('team', 'both') or categories - CATEGORIES.keys():
        return jsonify(error='Invalid clip filters.'), 400
    session, error = connect()
    if error:
        return error
    with session:
        found = session.execute(text('''SELECT id FROM games
            WHERE id = :game_id AND :team_id IN (home_team_id, away_team_id)'''),
            {'game_id': game_id, 'team_id': team_id}).first()
        if not found:
            return jsonify(error='Game not found for this team.'), 404
        team_sql = f'AND {TEAM_CLIP}' if scope == 'team' else ''
        params = {'game_id': game_id}
        if scope == 'team':
            params['team_id'] = team_id
        rows = session.execute(text(f'''
            SELECT c.id, c.description, c.period, c.game_clock, c.duration_s,
                   c.action_type, c.shot_subtype,
                   ARRAY(SELECT DISTINCT cp.role::text FROM clip_players cp WHERE cp.clip_id = c.id)
            FROM clips c WHERE c.game_id = :game_id {team_sql}
            ORDER BY c.video_start_s, c.play_index, c.id LIMIT 10001
        '''), params).all()
    # Bound legacy category inference, and never silently truncate the game.
    if len(rows) > 10000:
        return jsonify(error='This game has too many clips to browse.'), 503
    all_clips = [dict(id=r[0], description=r[1], period=r[2], game_clock=clock_label(r[3]),
                      duration_label=duration_label(r[4]), categories=clip_categories(r[1], r[5], r[6], r[7])) for r in rows]
    counts = {key: sum(key in clip['categories'] for clip in all_clips) for key in CATEGORIES}
    matches = [clip for clip in all_clips if not categories or categories.intersection(clip['categories'])]
    start = 0
    if cursor:
        index = next((i for i, clip in enumerate(matches) if clip['id'] == cursor), None)
        if index is None:
            return jsonify(error='Cursor clip not found in these filters.'), 404
        start = index + 1
    page = matches[start:start + 30]
    return jsonify(clips=page, total=len(matches),
                   categories=[dict(key=k, label=v, count=counts[k]) for k, v in CATEGORIES.items()],
                   cursor=page[-1]['id'] if start + len(page) < len(matches) else None)


@bp.get('/api/teams/<int:team_id>/games/<int:game_id>/clips/<int:clip_id>')
def serve_game_clip(team_id, game_id, clip_id):
    session, error = connect()
    if error:
        return error
    with session:
        row = session.execute(text('''SELECT c.video_start_s, c.video_end_s, g.s3_key
            FROM clips c JOIN games g ON g.id = c.game_id
            WHERE c.id = :clip_id AND g.id = :game_id AND :team_id IN (g.home_team_id, g.away_team_id)
        '''), {'clip_id': clip_id, 'game_id': game_id, 'team_id': team_id}).first()
    return serve_clip_row(row, clip_id)
