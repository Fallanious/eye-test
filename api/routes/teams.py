"""Team/game browsing using the existing film and player-link catalog."""
from flask import Blueprint, jsonify, request

from routes.players import _db_params, _open, clock_label, duration_label, serve_clip_row
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
TEAM_CLIP = """(c.team_id = %s OR (c.team_id IS NULL AND EXISTS (
    SELECT 1 FROM clip_players cp JOIN players p ON p.id = cp.player_id
    WHERE cp.clip_id = c.id AND p.team_id = %s)))"""


def connect():
    params, error = _db_params()
    if error:
        return None, error
    conn, error = _open(params)
    if error:
        return None, error
    try:
        conn.execute('SET TRANSACTION READ ONLY')
        conn.execute("SET LOCAL statement_timeout = '8s'")
    except Exception:
        conn.close()
        raise
    return conn, None


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
    conn, error = connect()
    if error:
        return error
    with conn:
        rows = conn.execute('''
            SELECT t.id, t.abbr, t.city, t.name, COUNT(DISTINCT g.id)
            FROM teams t JOIN games g ON t.id IN (g.home_team_id, g.away_team_id)
            WHERE EXISTS (SELECT 1 FROM clips c WHERE c.game_id = g.id)
            GROUP BY t.id ORDER BY t.city, t.name
        ''').fetchall()
    return jsonify(teams=[dict(id=r[0], abbr=r[1], name=f'{r[2]} {r[3]}', games=r[4]) for r in rows])


@bp.get('/api/teams/<int:team_id>/games')
def list_games(team_id):
    try:
        cursor = cursor_value()
    except ValueError:
        return jsonify(error='Invalid game cursor.'), 400
    conn, error = connect()
    if error:
        return error
    with conn:
        if not conn.execute('SELECT id FROM teams WHERE id = %s', (team_id,)).fetchone():
            return jsonify(error='Team not found.'), 404
        mark = None
        if cursor:
            mark = conn.execute('''SELECT game_date, id FROM games
                WHERE id = %s AND %s IN (home_team_id, away_team_id)''', (cursor, team_id)).fetchone()
            if mark is None:
                return jsonify(error='Cursor game not found.'), 404
        after = 'AND (g.game_date, g.id) < (%s, %s)' if mark else ''
        rows = conn.execute(f'''
            SELECT g.id, g.game_date, g.season, ht.abbr, at.abbr,
                COUNT(c.id), COUNT(c.id) FILTER (WHERE {TEAM_CLIP})
            FROM games g JOIN teams ht ON ht.id = g.home_team_id
            JOIN teams at ON at.id = g.away_team_id JOIN clips c ON c.game_id = g.id
            WHERE %s IN (g.home_team_id, g.away_team_id) {after}
            GROUP BY g.id, ht.abbr, at.abbr
            ORDER BY g.game_date DESC, g.id DESC LIMIT 25
        ''', [team_id, team_id, team_id, *(mark or [])]).fetchall()
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
    conn, error = connect()
    if error:
        return error
    with conn:
        if not conn.execute('SELECT id FROM games WHERE id = %s AND %s IN (home_team_id, away_team_id)',
                            (game_id, team_id)).fetchone():
            return jsonify(error='Game not found for this team.'), 404
        team_sql = f'AND {TEAM_CLIP}' if scope == 'team' else ''
        rows = conn.execute(f'''
            SELECT c.id, c.description, c.period, c.game_clock, c.duration_s,
                   c.action_type, c.shot_subtype,
                   ARRAY(SELECT DISTINCT cp.role::text FROM clip_players cp WHERE cp.clip_id = c.id)
            FROM clips c WHERE c.game_id = %s {team_sql}
            ORDER BY c.video_start_s, c.play_index, c.id LIMIT 10001
        ''', [game_id, *([team_id, team_id] if scope == 'team' else [])]).fetchall()
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
    conn, error = connect()
    if error:
        return error
    with conn:
        row = conn.execute('''SELECT c.video_start_s, c.video_end_s, g.s3_key
            FROM clips c JOIN games g ON g.id = c.game_id
            WHERE c.id = %s AND g.id = %s AND %s IN (g.home_team_id, g.away_team_id)
        ''', (clip_id, game_id, team_id)).fetchone()
    return serve_clip_row(row, clip_id)
