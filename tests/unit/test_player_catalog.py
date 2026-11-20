"""Exercise catalog joins and pagination with a small in-memory relational fixture."""
import sqlite3

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from flask import Flask
import pytest

from routes import players


@pytest.fixture
def catalog(monkeypatch):
    db = sqlite3.connect(':memory:')
    db.executescript('''
        CREATE TABLE teams (id INTEGER PRIMARY KEY, abbr TEXT);
        CREATE TABLE players (id INTEGER PRIMARY KEY, bbref_id TEXT, full_name TEXT,
                              position TEXT, headshot_url TEXT, team_id INTEGER);
        CREATE TABLE games (id INTEGER PRIMARY KEY, season TEXT);
        CREATE TABLE clips (id INTEGER PRIMARY KEY, game_id INTEGER);
        CREATE TABLE clip_players (player_id INTEGER, clip_id INTEGER);
        INSERT INTO teams VALUES (1, 'BOS'), (2, 'NYK'), (3, 'LAL');
        INSERT INTO players VALUES
            (1, 'a', 'Alpha', 'PG', NULL, 1),
            (2, 'b', 'Bravo', 'C', NULL, 2),
            (3, 'c', 'Charlie', 'SF', NULL, NULL);
        ALTER TABLE players ADD COLUMN first_name TEXT;
        ALTER TABLE players ADD COLUMN last_name TEXT;
        ALTER TABLE teams ADD COLUMN city TEXT;
        ALTER TABLE teams ADD COLUMN name TEXT;
        ALTER TABLE teams ADD COLUMN created_at DATETIME;
        INSERT INTO games VALUES (1, '2025-26');
        INSERT INTO clips VALUES (10, 1), (11, 1);
        INSERT INTO clip_players VALUES (1, 10), (1, 10), (1, 11);
    ''')

    engine = create_engine('sqlite://', creator=lambda: db)
    monkeypatch.setattr(players, 'connect', lambda: (Session(engine), None))
    app = Flask(__name__)
    app.register_blueprint(players.bp)
    yield app.test_client()
    engine.dispose()


def test_catalog_includes_zero_clip_players_and_empty_teams(catalog):
    response = catalog.get('/api/players')
    assert response.status_code == 200
    data = response.get_json()
    assert data['teams'] == ['BOS', 'LAL', 'NYK']
    assert data['total'] == 3
    assert [(p['full_name'], p['clips'], p['games']) for p in data['players']] == [
        ('Alpha', 2, 1), ('Bravo', 0, 0), ('Charlie', 0, 0)]
    assert data['players'][2]['team'] == ''


def test_team_and_search_include_players_without_clips(catalog):
    data = catalog.get('/api/players?team=NYK&q=brav').get_json()
    assert data['total'] == 1
    assert data['players'][0]['full_name'] == 'Bravo'
    assert data['players'][0]['clips'] == 0
    empty = catalog.get('/api/players?team=LAL').get_json()
    assert empty['players'] == []
    assert empty['total'] == 0
    assert empty['teams'] == ['BOS', 'LAL', 'NYK']


def test_pagination_accepts_zero_clip_cursor(catalog, monkeypatch):
    monkeypatch.setattr(players, 'CLIP_PAGE', 1)
    first = catalog.get('/api/players').get_json()
    second = catalog.get(f"/api/players?cursor={first['cursor']}").get_json()
    assert second['players'][0]['full_name'] == 'Bravo'
    third = catalog.get(f"/api/players?cursor={second['cursor']}").get_json()
    assert third['players'][0]['full_name'] == 'Charlie'
    assert third['cursor'] is None
    assert third['total'] == 3
