"""Exercise team filters, legacy labels, pagination and scope against local PG."""
import os

import pytest
import psycopg

from test_persist_matcher_clips import postgres_url, _reset  # noqa: F401
from eye_test import create_app

pytestmark = pytest.mark.postgres


@pytest.fixture
def client(postgres_url, tmp_path):
    _reset(postgres_url)
    with psycopg.connect(postgres_url) as conn:
        conn.execute("INSERT INTO teams (abbr, city, name) VALUES ('OUT','Other','Team')")
        conn.execute("INSERT INTO players (bbref_id,full_name,first_name,last_name,team_id) VALUES ('test','A. Player','A','Player',1)")
        for i in range(65):
            # Legacy rows have no team_id or shot_subtype; current rows have team_id.
            conn.execute('''INSERT INTO clips (game_id,team_id,game_date,play_index,period,game_clock,
                description,video_start_s,video_end_s) VALUES (1,%s,'2026-01-01',%s,1,'10 minutes',%s,%s,%s)''',
                         (None if i < 35 else 2, i, 'A. Player makes 3-pt jump shot' if i % 2 == 0 else 'A. Player makes dunk', i*6, i*6+5))
            if i < 35:
                conn.execute("INSERT INTO clip_players VALUES (%s,1,'shot','2026-01-01')", (i+1,))
    previous = os.environ.get('DATABASE_URL_SQLALCHEMY')
    os.environ['DATABASE_URL_SQLALCHEMY'] = postgres_url.replace('postgresql://', 'postgresql+psycopg://', 1)
    from routes.engine import dispose_engine
    dispose_engine()
    app = create_app({'TESTING': True, 'DATABASE_URL': postgres_url, 'REDIS_URL': '',
                      'RATE_LIMIT_PATH': str(tmp_path/'limits')})
    yield app.test_client()
    dispose_engine()
    if previous is None:
        os.environ.pop('DATABASE_URL_SQLALCHEMY', None)
    else:
        os.environ['DATABASE_URL_SQLALCHEMY'] = previous


def test_team_game_counts_and_missing_teams(client):
    teams = client.get('/api/teams').json['teams']
    assert {team['abbr']: team['games'] for team in teams} == {'FIC': 1, 'QAF': 1, 'OUT': 0}
    games = client.get('/api/teams/1/games').json['games']
    assert games[0]['team_clips'] == 35
    assert games[0]['clips'] == 65
    assert client.get('/api/teams/999/games').status_code == 404
    assert client.get('/api/teams/3/games/1/clips').status_code == 404


def test_scope_and_category_filters_on_legacy_rows(client):
    url = '/api/teams/1/games/1/clips'
    assert client.get(url).json['total'] == 35
    assert client.get(url+'?scope=both').json['total'] == 65
    data = client.get(url+'?categories=three_pointer').json
    assert data['total'] == 18
    assert all('three_pointer' in c['categories'] for c in data['clips'])
    assert client.get(url+'?categories=three_pointer,dunk').json['total'] == 35
    assert client.get(url+'?categories=steal').json['clips'] == []
    assert client.get(url+'?categories=invalid').status_code == 400
    assert client.get(url+'?scope=invalid').status_code == 400


def test_clip_pagination_preserves_order_without_duplicates(client):
    url = '/api/teams/1/games/1/clips'
    first = client.get(url).json
    second = client.get(url+f"?cursor={first['cursor']}").json
    ids = [c['id'] for c in first['clips']+second['clips']]
    assert ids == list(range(1,36))
    assert second['cursor'] is None
    assert client.get(url+'?cursor=999').status_code == 404
    assert client.get(url+'?cursor=-1').status_code == 400


def test_playback_checks_game_and_team_and_missing_film(client):
    assert client.get('/api/teams/3/games/1/clips/1').status_code == 404
    assert client.get('/api/teams/1/games/999/clips/1').status_code == 404
    response = client.get('/api/teams/1/games/1/clips/1')
    assert response.status_code == 404
    assert 'no film' in response.json['error']


def test_player_clip_pages_keep_multiple_roles_together(client, postgres_url):
    with psycopg.connect(postgres_url) as conn:
        conn.execute("INSERT INTO clip_players VALUES (15, 1, 'assist', '2026-01-01')")
    url = '/api/players/1/clips'
    first = client.get(url).json
    assert first['cursor'] == 15
    assert [(clip['id'], clip['role']) for clip in first['clips'][-2:]] == [
        (15, 'assist'), (15, 'shot')]
    second = client.get(url + '?cursor=15').json
    assert second['clips'][0]['id'] == 16
    filtered = client.get(url + '?role=assist').json
    assert [clip['id'] for clip in filtered['clips']] == [15]
    assert filtered['cursor'] is None
    assert client.get(url + '?role=assist&cursor=1').status_code == 404


def test_game_players_filter_before_pagination(client, postgres_url):
    with psycopg.connect(postgres_url) as conn:
        conn.execute("""INSERT INTO players (bbref_id,full_name,first_name,last_name,team_id)
                        VALUES ('helper','B. Helper','B','Helper',1),
                               ('opponent','C. Opponent','C','Opponent',2)""")
        conn.execute("""INSERT INTO clip_players VALUES
                        (1,2,'assist','2026-01-01'), (1,3,'foul','2026-01-01'),
                        (3,2,'assist','2026-01-01')""")
        conn.execute("""UPDATE clips SET period = 4, game_clock = '1 minute',
                        attributes = '{"pre_play_score":{"home":90,"away":92}}' WHERE id = 3""")

    base = '/api/teams/1/games/1'
    assert client.get(base + '/players').json['players'] == [
        {'id': 1, 'full_name': 'A. Player'}, {'id': 2, 'full_name': 'B. Helper'}]
    assert client.get('/api/teams/3/games/1/players').status_code == 404
    assert client.get(base + '/clips?player=invalid').status_code == 400
    assert client.get(base + '/clips?player=3').json['total'] == 0
    assert client.get(base + '/clips?scope=both&player=3').json['total'] == 1
    assert {p['id'] for p in client.get(base + '/players?scope=both').json['players']} == {1, 2, 3}
    filtered = client.get(base + '/clips?player=2&categories=three_pointer&clutch=1').json
    assert [clip['id'] for clip in filtered['clips']] == [3]
    url = base + '/clips?player=1&player=2'
    first = client.get(url).json
    assert first['total'] == 35
    second = client.get(url + f"&cursor={first['cursor']}").json
    assert [clip['id'] for clip in first['clips'] + second['clips']] == list(range(1, 36))


def test_schedule_merges_feed_and_catalog_by_matchup(client, postgres_url, monkeypatch):
    from routes import games
    fixtures = [
        dict(key='one', home='BKN', away='GS', status='Final', start=None),
        dict(key='two', home='BOS', away='LAL', status='Final', start=None),
    ]
    monkeypatch.setattr(games, 'scoreboard', lambda *_: fixtures)
    with psycopg.connect(postgres_url) as conn:
        conn.execute("UPDATE teams SET abbr='BRK' WHERE id=1")
        conn.execute("UPDATE teams SET abbr='GSW' WHERE id=2")
        conn.execute("UPDATE games SET s3_key='games/one.mkv' WHERE id=1")
    assert client.get('/api/games/clip-dates?year=2026').json['dates'] == ['2026-01-01']
    assert client.get('/api/games/clip-dates?year=2025').json['dates'] == []
    response = client.get('/api/games?date=2026-01-01').json
    assert not response['incomplete']
    one, two = response['games']
    assert (one['id'], one['away'], one['home'], one['has_clips']) == (1, 'GSW', 'BKN', True)
    assert two['id'] is None and not two['has_clips']

    def offline(*_):
        raise TimeoutError
    monkeypatch.setattr(games, 'scoreboard', offline)
    fallback = client.get('/api/games?date=2026-01-01').json
    assert fallback['incomplete'] and fallback['games'][0]['id'] == 1
    assert client.get('/api/games?date=invalid').status_code == 400
