"""Daily NBA schedule with availability from the local film catalog."""
from datetime import date, timedelta
from functools import lru_cache
import json
from time import time
from urllib.request import urlopen

from flask import Blueprint, jsonify, request
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from dataclass.clips import Clip
from dataclass.games import Game
from routes.engine import connect

bp = Blueprint('games', __name__)
ALIASES = {'GS': 'GSW', 'SA': 'SAS', 'NY': 'NYK', 'NO': 'NOP', 'UTAH': 'UTA',
           'WSH': 'WAS', 'BRK': 'BKN', 'CHO': 'CHA', 'PHO': 'PHX'}


@lru_cache(maxsize=256)
def scoreboard(day, refresh_bucket):
    url = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates='
    with urlopen(url + day.strftime('%Y%m%d'), timeout=5) as response:
        events = json.load(response)['events']
    games = []
    for event in events:
        competition = event['competitions'][0]
        teams = {side['homeAway']: side['team']['abbreviation']
                 for side in competition['competitors']}
        status = event['status']['type']
        games.append(dict(key=event['id'], away=teams['away'], home=teams['home'],
                          start=event['date'], status=status['shortDetail']))
    return games


def matchup(row):
    return tuple(ALIASES.get(row[side], row[side]) for side in ('away', 'home'))


def available_film():
    clips = select(Clip.id).where(Clip.game_id == Game.id).exists()
    return (Game.s3_key != '') & clips


@bp.get('/api/games/clip-dates')
def clip_dates():
    year = request.args.get('year', type=int)
    if year is None or not 2 <= year <= 9999:
        return jsonify(error='Choose a valid year.'), 400
    # Include the start of the week that crosses into January.
    start = date(year, 1, 1) - timedelta(days=6)
    statement = (select(Game.game_date)
                 .where(Game.game_date.between(start, date(year, 12, 31)), available_film())
                 .distinct().order_by(Game.game_date))
    session, error = connect()
    if error:
        return error
    with session:
        return jsonify(dates=[day.isoformat() for day in session.scalars(statement)])


@bp.get('/api/games')
def schedule():
    try:
        day = date.fromisoformat(request.args.get('date', ''))
    except ValueError:
        return jsonify(error='Choose a valid schedule date.'), 400
    incomplete = False
    try:
        fixtures = scoreboard(day, int(time() // 300))
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        fixtures = []
        incomplete = True

    session, error = connect()
    if error:
        return error
    statement = (select(Game, available_film()).where(Game.game_date == day)
                 .options(joinedload(Game.home_team), joinedload(Game.away_team))
                 .order_by(Game.id))
    with session:
        catalog = {}
        for game, has_clips in session.execute(statement):
            row = dict(id=game.id, home_id=game.home_team_id, home=game.home_team.abbr,
                       away=game.away_team.abbr, season=game.season,
                       has_clips=bool(has_clips))
            catalog[matchup(row)] = row

    result = []
    for fixture in fixtures:
        away, home = matchup(fixture)
        row = dict(id=None, home_id=None, season='', has_clips=False)
        row.update(catalog.pop((away, home), {}))
        result.append({**fixture, **row, 'away': away, 'home': home})
    for (away, home), row in catalog.items():
        result.append({**row, 'away': away, 'home': home, 'key': f"catalog-{row['id']}",
                       'start': None, 'status': ''})
    return jsonify(games=result, incomplete=incomplete)
