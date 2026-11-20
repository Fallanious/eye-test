"""Playback checks membership before signing media and bounds corrupt DB windows."""
from pathlib import Path

import pytest

from eye_test import create_app
from routes import players


class Connection:
    def __init__(self, row):
        self.row = row
        self.parameters = None
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def execute(self, statement):
        compiled = statement.compile()
        self.parameters = compiled.params
        assert 'clip_players.player_id = :player_id_1' in str(compiled)
        assert 'clips.id = :id_1' in str(compiled)
        return self
    def first(self):
        return self.row


@pytest.mark.parametrize('row,status', [(None, 404), ((1, 3, None), 404),
    ((0, 121, 'game.mkv'), 422), ((float('nan'), 2, 'game.mkv'), 422)])
def test_invalid_clip_never_signs_or_cuts(tmp_path, monkeypatch, row, status):
    app = create_app({'TESTING': True, 'REDIS_URL': '', 'RATE_LIMIT_PATH': str(tmp_path/'limits'),
                      'DATABASE_URL': 'unused'})
    conn = Connection(row)
    monkeypatch.setattr(players, 'connect', lambda: (conn, None))
    def refuse(*args):
        pytest.fail('invalid clip must not access storage')
    monkeypatch.setattr('services.storage.presign_get_url', refuse)
    assert app.test_client().get('/api/players/7/clips/9').status_code == status
    assert conn.parameters['player_id_1'] == 7
    assert conn.parameters['id_1'] == 9


def test_playback_returns_only_cut_and_cleans_up(tmp_path, monkeypatch):
    app = create_app({'TESTING': True, 'REDIS_URL': '', 'RATE_LIMIT_PATH': str(tmp_path/'limits'),
                      'DATABASE_URL': 'unused'})
    monkeypatch.setattr(players, 'connect', lambda: (Connection((2, 5, 'games/game.mkv')), None))
    monkeypatch.setattr('services.storage.presign_get_url', lambda _: 'https://film.test/signed')
    paths = []
    def cut(source, start, end, path, **kwargs):
        assert (source, start, end) == ('https://film.test/signed', 2, 5)
        paths.append(Path(path))
        Path(path).write_bytes(b'cut-video')
        return True
    monkeypatch.setattr('generate_clips.extract_clip', cut)
    with app.test_request_context('/api/players/7/clips/9'):
        response = players.serve_player_clip(7, 9)
        response.direct_passthrough = False
        assert response.mimetype == 'video/mp4'
        assert response.get_data() == b'cut-video'
        response.close()
    assert not paths[0].exists()
