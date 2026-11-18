import subprocess

import pytest

from match_play_timestamps import extract_frame_at_time


@pytest.mark.parametrize('crop,expected_filter', [(None, None), ((46, 580, 338, 94), 'crop=338:94:46:580')])
def test_frame_uses_only_optional_crop(monkeypatch, crop, expected_filter):
    calls = []
    monkeypatch.setattr(subprocess, 'run', lambda cmd, **kwargs: calls.append(cmd))
    extract_frame_at_time('game.mp4', 1188, 'frame.jpg', crop)
    command = calls[0]
    if expected_filter is None:
        assert '-vf' not in command
    else:
        assert command[command.index('-vf') + 1] == expected_filter


def test_failed_frame_reports_timestamp_and_encoder_error(monkeypatch):
    def fail(cmd, **kwargs):
        raise subprocess.CalledProcessError(234, cmd, stderr=b'Non full-range YUV is non-standard')
    monkeypatch.setattr(subprocess, 'run', fail)
    with pytest.raises(RuntimeError, match='1188s.*234') as error:
        extract_frame_at_time('game.mp4', 1188, 'frame.jpg')
    assert 'Non full-range YUV' in str(error.value)
