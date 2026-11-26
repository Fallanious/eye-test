"""Player catalog, clip metadata, and cuts from the S3 game."""

import math
import os
import re
import tempfile
from datetime import timedelta
from decimal import Decimal

from werkzeug.wsgi import ClosingIterator

from flask import Blueprint, jsonify, request, send_file

from sqlalchemy import Text, cast, func, select, tuple_
from sqlalchemy.orm import joinedload, load_only, selectinload, with_expression

from dataclass.clips import Clip, ClipPlayer
from dataclass.games import Game
from dataclass.players import Player
from dataclass.teams import Team
from routes.engine import connect

bp = Blueprint("players", __name__)

MAX_CLIP_S = 120
CLIP_PAGE = 15

ROLE_LABELS = {
    "shot": "Shot",
    "assist": "Assist",
    "rebound": "Rebound",
    "block": "Block",
    "steal": "Steal",
    "foul": "Foul",
    "fouled": "Fouled",
    "turnover": "Turnover",
}

POSITION_LABELS = {
    "PG": "Guard",
    "SG": "Guard",
    "G": "Guard",
    "SF": "Forward",
    "PF": "Forward",
    "F": "Forward",
    "C": "Center",
}


def position_label(position):
    """Turn a roster code into the word on the player card."""
    if not position:
        return ""
    return POSITION_LABELS.get(position, position)


def clock_label(value):
    """Game clock interval as M:SS."""
    if not isinstance(value, timedelta):
        return ""
    total = int(value.total_seconds())
    minutes, seconds = divmod(abs(total), 60)
    return f"{minutes}:{seconds:02d}"


def duration_label(value):
    """Clip length as M:SS."""
    if isinstance(value, bool) or value is None:
        return ""
    if isinstance(value, Decimal):
        value = float(value)
    if isinstance(value, str):
        return ""
    try:
        total = int(round(float(value)))
    except (TypeError, ValueError):
        return ""
    if total < 0:
        return ""
    minutes, seconds = divmod(total, 60)
    return f"{minutes}:{seconds:02d}"


def season_label(season):
    """2026-27 becomes 2026–27, matching the archive line."""
    if not season:
        return ""
    return str(season).replace("-", "–")


def matchup_label(player_team, home, away):
    """The player's team first, then the other team."""
    if player_team and player_team == home:
        return f"{home} vs {away}"
    if player_team and player_team == away:
        return f"{away} vs {home}"
    return f"{away} at {home}"


def _like(text):
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def player_page_request(args):
    """The player id to start after, plus the search and team on this list."""
    raw_cursor = args.get("cursor", "")
    cursor = None
    if raw_cursor != "":
        try:
            cursor = int(raw_cursor)
        except (TypeError, ValueError):
            raise ValueError("Cursor is not a player id")
        if cursor < 1:
            raise ValueError("Cursor is not a player id")
    team = args.get("team", "").strip().upper()
    if team and not re.fullmatch(r"[A-Z]{2,3}", team):
        raise ValueError("Team is not valid")
    query = " ".join(args.get("q", "").split())
    if len(query) > 80:
        raise ValueError("Search is too long")
    return cursor, team or None, query or None


def clip_page_request(args):
    """The clip id to start after, and an optional role. The first page has no cursor."""
    raw_cursor = args.get("cursor", "")
    cursor = None
    if raw_cursor != "":
        try:
            cursor = int(raw_cursor)
        except (TypeError, ValueError):
            raise ValueError("Cursor is not a clip id")
        if cursor < 1:
            raise ValueError("Cursor is not a clip id")
    raw_role = args.get("role", "")
    if raw_role and raw_role not in ROLE_LABELS:
        raise ValueError("Role is not valid")
    return cursor, raw_role or None


def clip_window(start_s, end_s):
    """Seconds to keep. A bad row must not ask ffmpeg to cut the whole game."""
    start = float(start_s)
    end = float(end_s)
    if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end <= start or end - start > MAX_CLIP_S:
        raise ValueError("Clip window is not usable")
    return start, end


def player_cards(catalog):
    return (catalog.outerjoin(ClipPlayer, ClipPlayer.player_id == Player.id)
        .outerjoin(Clip, Clip.id == ClipPlayer.clip_id)
        .options(
            selectinload(Player.team),
            with_expression(Player.clips, func.count(ClipPlayer.clip_id.distinct())),
            with_expression(Player.games, func.count(Clip.game_id.distinct())),
        )
        .group_by(Player.id))


@bp.get("/api/players/<int:player_id>")
def get_player(player_id):
    session, error = connect()
    if error:
        return error
    with session:
        player = session.scalar(player_cards(select(Player).where(Player.id == player_id)))
        if player is None:
            return jsonify(error="Player not found."), 404
        return jsonify(player.to_dict())


@bp.route("/api/players")
def list_players():
    """One page of all catalog players, including those without clips."""
    try:
        cursor, team, query = player_page_request(request.args)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    session, error = connect()
    if error:
        return error
    catalog = select(Player).outerjoin(Player.team)
    if team:
        catalog = catalog.where(Team.abbr == team)
    if query:
        catalog = catalog.where(Player.full_name.ilike(_like(query), escape="\\"))
    order = (Player.full_name, Player.id)
    with session:
        total = session.scalar(catalog.with_only_columns(func.count(Player.id)))
        if cursor is not None:
            mark = session.execute(catalog.with_only_columns(*order).where(Player.id == cursor)).first()
            if mark is None:
                return jsonify(error="Cursor player was not found."), 404
            catalog = catalog.where(tuple_(*order) > tuple_(*mark))
        rows = session.scalars(
            player_cards(catalog).order_by(*order).limit(CLIP_PAGE + 1)
        ).all()
        seasons = [season_label(value) for value in session.scalars(
            select(Game.season).join(Clip, Clip.game_id == Game.id).distinct().order_by(Game.season)
        )]
        teams = session.scalars(select(Team.abbr).distinct().order_by(Team.abbr)).all()
        page = rows[:CLIP_PAGE]
        return jsonify(
            season=seasons[0] if len(seasons) == 1 else "",
            seasons=seasons, teams=teams, players=[player.to_dict() for player in page],
            cursor=page[-1].id if len(rows) > CLIP_PAGE else None, total=total,
        )


def _clip_payload(clip, role, team):
    game = clip.game
    return {
        "id": clip.id,
        "role": role,
        "role_label": ROLE_LABELS.get(role, role),
        "description": clip.description,
        "period": clip.period,
        "game_clock": clock_label(clip.game_clock),
        "duration_label": duration_label(clip.duration_s),
        "video_start_s": float(clip.video_start_s),
        "video_end_s": float(clip.video_end_s),
        "bbref_id": game.bbref_id,
        "game_date": game.game_date.isoformat(),
        "season": season_label(game.season),
        "matchup": matchup_label(team, game.home_team.abbr, game.away_team.abbr),
    }


@bp.route("/api/players/<int:player_id>/clips")
def list_player_clips(player_id):
    """Page by clip, returning each matching role on the selected clips."""
    try:
        cursor, role = clip_page_request(request.args)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    session, error = connect()
    if error:
        return error
    role_name = cast(ClipPlayer.role, Text)
    order = (Clip.video_start_s, Clip.play_index, Clip.id)
    links = (select(Clip, role_name).join(ClipPlayer, ClipPlayer.clip_id == Clip.id)
             .where(ClipPlayer.player_id == player_id))
    if request.args.get("clutch") == "1":
        links = links.where(Clip.is_clutch.is_(True))
    if role:
        links = links.where(role_name == role)
    with session:
        player = session.get(Player, player_id, options=[
            load_only(Player.full_name), joinedload(Player.team).load_only(Team.abbr),
        ])
        if player is None:
            return jsonify(error="Player not found."), 404
        name = player.full_name
        team = player.team.abbr if player.team else ""
        found_roles = set(session.scalars(
            select(role_name).where(ClipPlayer.player_id == player_id).distinct()
        ))
        page = links.with_only_columns(Clip.id).group_by(*order).order_by(*order)
        if cursor is not None:
            mark = session.execute(links.with_only_columns(*order).where(Clip.id == cursor).limit(1)).first()
            if mark is None:
                return jsonify(error="Cursor clip was not found."), 404
            page = page.where(tuple_(*order) > tuple_(*mark))
        ids = session.scalars(page.limit(CLIP_PAGE + 1)).all()
        next_cursor = ids[CLIP_PAGE - 1] if len(ids) > CLIP_PAGE else None
        clips = []
        if ids:
            details = links.where(Clip.id.in_(ids[:CLIP_PAGE])).options(
                joinedload(Clip.game).joinedload(Game.home_team),
                joinedload(Clip.game).joinedload(Game.away_team),
            ).order_by(*order, role_name)
            clips = [_clip_payload(clip, clip_role, team) for clip, clip_role in session.execute(details)]
    roles = [{"role": name, "label": ROLE_LABELS[name]} for name in ROLE_LABELS if name in found_roles]
    roles.extend({"role": name, "label": name} for name in sorted(found_roles - set(ROLE_LABELS)))
    return jsonify({
        "player": name,
        "team": team,
        "roles": roles,
        "clips": clips,
        "cursor": next_cursor,
    })


def _remove(path):
    try:
        os.remove(path)
    except OSError:
        pass


@bp.route("/api/players/<int:player_id>/clips/<int:clip_id>")
def serve_player_clip(player_id, clip_id):
    """Cut this play from the S3 game and return only that file."""
    session, error = connect()
    if error:
        return error
    with session:
        row = session.execute(
            select(Clip.video_start_s, Clip.video_end_s, Game.s3_key)
            .join(Clip.game)
            .join(ClipPlayer, ClipPlayer.clip_id == Clip.id)
            .where(ClipPlayer.player_id == player_id, Clip.id == clip_id)
            .limit(1)
        ).first()
    return serve_clip_row(row, clip_id)


def serve_clip_row(row, clip_id):
    """Stream one validated clip, shared by player and game browsing."""
    if row is None:
        return jsonify({"error": "Clip not found."}), 404
    if not row[2]:
        return jsonify({"error": "This game has no film in storage."}), 404
    try:
        start, end = clip_window(row[0], row[1])
    except (TypeError, ValueError):
        return jsonify({"error": "Clip window is not usable."}), 422
    try:
        from services.storage import presign_get_url

        source = presign_get_url(row[2])
    except Exception:
        return jsonify({"error": "Could not open the game film."}), 502

    fd, path = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    try:
        from generate_clips import extract_clip

        ok = extract_clip(source, start, end, path, quiet=True)
        if not ok or os.path.getsize(path) <= 0:
            _remove(path)
            return jsonify({"error": "Could not cut this clip."}), 502
    except Exception:
        _remove(path)
        return jsonify({"error": "Could not cut this clip."}), 502

    response = send_file(
        path,
        mimetype="video/mp4",
        conditional=True,
        download_name=f"{clip_id}.mp4",
    )
    response.headers["Cache-Control"] = "private, max-age=3600"
    response.response = ClosingIterator(response.response, lambda: _remove(path))
    return response
