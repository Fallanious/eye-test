from clip_scores import score_attributes


def test_pre_play_score_uses_previous_event_even_at_same_clock():
    plays = [
        {"quarter": 4, "time": "5:00.0", "score": "90-85"},
        {"quarter": 4, "time": "5:00.0", "score": "91-85"},
    ]
    assert score_attributes(plays, 0)["pre_play_score"] == {"away": 0, "home": 0}
    assert score_attributes(plays, 1) == {
        "period": 4, "game_clock": "5:00.0",
        "pre_play_score": {"away": 90, "home": 85},
        "post_play_score": {"away": 91, "home": 85},
    }
