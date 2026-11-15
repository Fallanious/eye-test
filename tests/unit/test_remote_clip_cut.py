"""A remote game is seeked, then only the window is read. The signed URL stays out of the log."""

import json
import subprocess

from generate_clips import CUT_TIMEOUT_S, PROBE_TIMEOUT_S, extract_clip


def test_remote_cut_seeks_before_reading(monkeypatch, tmp_path):
    calls = []

    def run(cmd, *args, **kwargs):
        calls.append(([str(part) for part in cmd], kwargs.get("timeout")))
        return subprocess.CompletedProcess(cmd, 0, stdout="{}", stderr="")

    monkeypatch.setattr("generate_clips.subprocess.run", run)
    dest = tmp_path / "clip.mp4"
    assert extract_clip("https://example.test/game.mkv?X-Amz-Signature=secret", 22, 27, str(dest), quiet=True)
    ffmpeg, cut_timeout = next(item for item in calls if item[0][0] == "ffmpeg")
    probe_timeout = next(timeout for cmd, timeout in calls if cmd[0] == "ffprobe")
    assert ffmpeg.index("-ss") < ffmpeg.index("-t") < ffmpeg.index("-seekable") < ffmpeg.index("-i")
    assert ffmpeg[ffmpeg.index("-seekable") + 1] == "1"
    assert "-reconnect" in ffmpeg
    assert "ultrafast" in ffmpeg
    assert "libx264" in ffmpeg
    assert ffmpeg[ffmpeg.index("-crf") + 1] == "18"
    assert probe_timeout == PROBE_TIMEOUT_S
    assert cut_timeout == CUT_TIMEOUT_S


def test_av1_game_is_remuxed(monkeypatch, tmp_path):
    calls = []

    def run(cmd, *args, **kwargs):
        calls.append([str(part) for part in cmd])
        if cmd[0] == "ffprobe":
            body = json.dumps({"streams": [{"codec_type": "video", "codec_name": "av1"}]})
            return subprocess.CompletedProcess(cmd, 0, stdout=body, stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr("generate_clips.subprocess.run", run)
    assert extract_clip("https://example.test/game.mkv?X-Amz-Signature=secret", 877, 882, str(tmp_path / "c.mp4"), quiet=True)
    ffmpeg = next(cmd for cmd in calls if cmd[0] == "ffmpeg")
    assert ffmpeg[ffmpeg.index("-c") + 1] == "copy"
    assert "libx264" not in ffmpeg


def test_remote_failure_does_not_print_the_signed_url(monkeypatch, tmp_path, capsys):
    def run(cmd, *args, **kwargs):
        if str(cmd[0]).endswith("ffprobe"):
            return subprocess.CompletedProcess(cmd, 0, stdout="{}", stderr="")
        raise subprocess.CalledProcessError(
            1, cmd, stderr=b"open https://example.test/game.mkv?X-Amz-Signature=secret"
        )

    monkeypatch.setattr("generate_clips.subprocess.run", run)
    assert extract_clip("https://example.test/game.mkv?X-Amz-Signature=secret", 22, 27, str(tmp_path / "c.mp4")) is False
    logged = capsys.readouterr().out + capsys.readouterr().err
    assert "secret" not in logged
    assert "X-Amz-Signature" not in logged
