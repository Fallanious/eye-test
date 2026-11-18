"""Public boundary and limits, without Neon or media access."""
from concurrent.futures import ThreadPoolExecutor

from eye_test import create_app
from public_limits import RateLimits
from routes.players import _db_params


def make_app(tmp_path, **kwargs):
    return create_app({'TESTING': True, 'REDIS_URL': '', 'RATE_LIMIT_PATH': str(tmp_path / 'limits.sqlite3'), **kwargs})


def test_browser_origin_is_echoed_only_when_listed(tmp_path):
    app = make_app(tmp_path, ALLOWED_ORIGINS={'https://eye.example'})
    client = app.test_client()
    allowed = client.get('/healthz', headers={'Origin': 'https://eye.example'})
    assert allowed.headers['Access-Control-Allow-Origin'] == 'https://eye.example'
    assert 'Origin' in allowed.headers['Vary']
    blocked = client.get('/healthz', headers={'Origin': 'https://other.example'})
    assert 'Access-Control-Allow-Origin' not in blocked.headers
    preflight = client.options('/api/players', headers={'Origin': 'https://eye.example'})
    assert preflight.status_code == 204
    assert preflight.headers['Access-Control-Allow-Origin'] == 'https://eye.example'


def test_only_public_routes_are_registered(tmp_path):
    app = make_app(tmp_path)
    endpoints = {rule.rule for rule in app.url_map.iter_rules() if rule.rule.startswith('/api/')}
    assert endpoints == {'/api/players', '/api/players/<int:player_id>/clips',
                         '/api/players/<int:player_id>/clips/<int:clip_id>',
                         '/api/teams', '/api/teams/<int:team_id>/games',
                         '/api/teams/<int:team_id>/games/<int:game_id>/clips',
                         '/api/teams/<int:team_id>/games/<int:game_id>/clips/<int:clip_id>'}
    client = app.test_client()
    for path in ['/api/jobs', '/api/upload', '/api/download', '/api/generate', '/api/film/game.mkv']:
        assert client.get(path).status_code == 404
        assert client.post(path).status_code == 404


def test_browsing_limit_and_spoofed_forwarding(tmp_path):
    app = make_app(tmp_path, BROWSE_PER_MINUTE=2)
    client = app.test_client()
    for i in range(2):
        assert client.get('/api/players?cursor=bad', headers={'X-Forwarded-For': str(i)}).status_code == 400
    response = client.get('/api/players?cursor=bad', headers={'X-Forwarded-For': 'different'})
    assert response.status_code == 429
    assert 1 <= int(response.headers['Retry-After']) <= 60
    assert response.headers['Cache-Control'] == 'no-store'


def test_playback_has_separate_and_global_budgets(tmp_path):
    app = make_app(tmp_path, PLAYBACK_PER_MINUTE=1, GLOBAL_PLAYBACK_PER_MINUTE=2)
    app.view_functions['players.serve_player_clip'] = lambda **kwargs: ('clip', 200)
    client = app.test_client()
    path = '/api/players/1/clips/1'
    assert client.get(path).status_code == 200
    assert client.get(path).status_code == 429
    assert client.get('/api/players?cursor=bad').status_code == 400
    assert client.get(path, environ_base={'REMOTE_ADDR': '192.0.2.1'}).status_code == 200
    assert client.get(path, environ_base={'REMOTE_ADDR': '192.0.2.2'}).status_code == 429


def test_shared_atomic_limits_and_expiration(tmp_path):
    path = tmp_path / 'shared.sqlite3'
    first, second = RateLimits(path), RateLimits(path)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda i: (first if i % 2 else second).take([('ip', 5)], now=120), range(20)))
    assert results.count(0) == 5
    assert first.take([('ip', 5)], now=180) == 0


def test_public_database_is_read_only_and_keeps_pooler(tmp_path):
    url = 'postgresql://reader:password@example-pooler.neon.tech/neondb'
    app = make_app(tmp_path, DATABASE_URL=url)
    with app.app_context():
        params, error = _db_params()
    assert error is None
    assert params['conninfo'] == url
    assert 'options' not in params


def test_limit_storage_failure_fails_closed(tmp_path):
    app = make_app(tmp_path)
    (tmp_path / 'limits.sqlite3').unlink()
    response = app.test_client().get('/api/players')
    assert response.status_code == 503


def test_database_guards_are_set_before_queries(tmp_path, monkeypatch):
    from routes.players import _open
    calls = []
    class Connection:
        def execute(self, sql):
            calls.append(sql)
    connection = Connection()
    def connect(**kwargs):
        assert 'options' not in kwargs
        return connection
    monkeypatch.setattr('psycopg.connect', connect)
    app = make_app(tmp_path)
    with app.app_context():
        conn, error = _open({'conninfo': 'unused'})
    assert conn is connection and error is None
    assert calls == ['SET TRANSACTION READ ONLY', "SET LOCAL statement_timeout = '8s'"]


def test_database_guard_failure_closes_connection(tmp_path, monkeypatch):
    from routes.players import _open
    class Connection:
        closed = False
        def execute(self, sql):
            raise RuntimeError('setup failed')
        def close(self):
            self.closed = True
    connection = Connection()
    monkeypatch.setattr('psycopg.connect', lambda **kwargs: connection)
    with make_app(tmp_path).app_context():
        conn, error = _open({'conninfo': 'unused'})
    assert conn is None and error[1] == 503
    assert connection.closed
