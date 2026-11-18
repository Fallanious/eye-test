from routes.teams import clip_categories
from eye_test import create_app


def test_inferred_categories_include_assists_and_subtypes():
    assert 'dunk' in clip_categories('A. Player makes dunk', None, None, [])
    assert 'three_pointer' in clip_categories('A. Player makes 3-pt jump shot', None, None, [])
    assert 'assist' in clip_categories('A. Player makes jump shot', 'shot', None, ['shot', 'assist'])


def test_game_playback_uses_shared_rate_budget(tmp_path):
    app = create_app({'TESTING': True, 'REDIS_URL': '', 'RATE_LIMIT_PATH': str(tmp_path/'limits'),
                      'PLAYBACK_PER_MINUTE': 1})
    app.view_functions['teams.serve_game_clip'] = lambda **kwargs: ('film', 200)
    app.view_functions['players.serve_player_clip'] = lambda **kwargs: ('film', 200)
    client = app.test_client()
    assert client.get('/api/teams/1/games/1/clips/1').status_code == 200
    assert client.get('/api/players/1/clips/1').status_code == 429
