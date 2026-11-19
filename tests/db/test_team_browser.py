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
