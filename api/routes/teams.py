"""Team/game browsing using the existing film and player-link catalog."""

from flask import Blueprint, jsonify, request
from sqlalchemy import Text, and_, cast, distinct, func, or_, select, tuple_
from sqlalchemy.orm import selectinload, with_expression

from dataclass.clips import Clip, ClipPlayer
from dataclass.games import Game
from dataclass.players import Player
from dataclass.teams import Team
from routes.engine import connect
from routes.players import serve_clip_row
from utils.labels import extract_attributes

bp = Blueprint('teams', __name__)
CATEGORIES = {
    'three_pointer': 'Three-pointers', 'dunk': 'Dunks', 'layup': 'Layups',
    'shot': 'Shots', 'rebound': 'Rebounds', 'steal': 'Steals', 'block': 'Blocks',
    'assist': 'Assists', 'foul': 'Fouls', 'turnover': 'Turnovers',
    'free_throw': 'Free throws',
}
def team_involved(team_id):
    """A clip belongs to a team by its own team_id, or by a linked player.

    Older imports omit clips.team_id. A linked player's current team counts
    those rows. Do not guess from an abbreviated name in the description.
    """
    linked_player = (
        select(ClipPlayer.clip_id)
        .join(Player, Player.id == ClipPlayer.player_id)
        .where(ClipPlayer.clip_id == Clip.id, Player.team_id == team_id)
        .exists()
    )
    return or_(Clip.team_id == team_id, and_(Clip.team_id.is_(None), linked_player))


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
    on_team = or_(Game.home_team_id == team_id, Game.away_team_id == team_id)
    statement = (
        select(Game)
        .join(Clip, Clip.game_id == Game.id)
        .where(on_team)
        .options(
            with_expression(Game.clips, func.count(Clip.id)),
            with_expression(Game.team_clips, func.count(Clip.id).filter(team_involved(team_id))),
            selectinload(Game.home_team),
            selectinload(Game.away_team),
        )
        .group_by(Game.id)
        .order_by(Game.game_date.desc(), Game.id.desc())
        .limit(25)
    )
    with session:
        if session.get(Team, team_id) is None:
            return jsonify(error='Team not found.'), 404
        if cursor:
            mark = session.scalar(select(Game).where(Game.id == cursor, on_team))
            if mark is None:
                return jsonify(error='Cursor game not found.'), 404
            statement = statement.where(
                tuple_(Game.game_date, Game.id) < tuple_(mark.game_date, mark.id)
            )
        games = session.scalars(statement).all()
        page = games[:24]
        next_cursor = page[-1].id if len(games) > 24 else None
        return jsonify(games=page, cursor=next_cursor)


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
    role_names = (
        select(func.array_agg(distinct(cast(ClipPlayer.role, Text))))
        .where(ClipPlayer.clip_id == Clip.id)
        .scalar_subquery()
    )
    statement = (
        select(Clip)
        .where(Clip.game_id == game_id)
        .options(with_expression(Clip.roles, role_names))
        .order_by(Clip.video_start_s, Clip.play_index, Clip.id)
        .limit(10001)
    )
    if request.args.get("clutch") == "1":
        statement = statement.where(Clip.is_clutch.is_(True))
    if scope == 'team':
        statement = statement.where(team_involved(team_id))
    with session:
        found = session.scalar(select(Game.id).where(
            Game.id == game_id,
            or_(Game.home_team_id == team_id, Game.away_team_id == team_id),
        ))
        if found is None:
            return jsonify(error='Game not found for this team.'), 404
        clips = session.scalars(statement).all()
        # Bound legacy category inference, and never silently truncate the game.
        if len(clips) > 10000:
            return jsonify(error='This game has too many clips to browse.'), 503
        keyed = [(clip, clip.category_keys()) for clip in clips]
        counts = {key: sum(key in keys for _, keys in keyed) for key in CATEGORIES}
        matches = [clip for clip, keys in keyed if not categories or categories.intersection(keys)]
        start = 0
        if cursor:
            index = next((i for i, clip in enumerate(matches) if clip.id == cursor), None)
            if index is None:
                return jsonify(error='Cursor clip not found in these filters.'), 404
            start = index + 1
        page = matches[start:start + 30]
        return jsonify(clips=page, total=len(matches),
                       categories=[dict(key=k, label=v, count=counts[k]) for k, v in CATEGORIES.items()],
                       cursor=page[-1].id if start + len(page) < len(matches) else None)


@bp.get('/api/teams/<int:team_id>/games/<int:game_id>/clips/<int:clip_id>')
def serve_game_clip(team_id, game_id, clip_id):
    session, error = connect()
    if error:
        return error
    with session:
        pair = session.execute(
            select(Clip, Game)
            .join(Game, Game.id == Clip.game_id)
            .where(
                Clip.id == clip_id,
                Game.id == game_id,
                or_(Game.home_team_id == team_id, Game.away_team_id == team_id),
            )
        ).first()
        # serve_clip_row still reads a 3-item row: start, end, film key.
        row = None if pair is None else (pair[0].video_start_s, pair[0].video_end_s, pair[1].s3_key)
    return serve_clip_row(row, clip_id)
