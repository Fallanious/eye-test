import re


def score_attributes(plays, index):
    """Basketball Reference lists the visitor first and reports the post-event score."""
    play = plays[index]
    attrs = {"game_clock": play["time"], "period": play["quarter"]}
    previous = plays[index - 1].get("score") if index else "0-0"
    for key, value in (("pre_play_score", previous), ("post_play_score", play.get("score"))):
        match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", str(value).strip())
        if match:
            attrs[key] = {"away": int(match[1]), "home": int(match[2])}
    return attrs
