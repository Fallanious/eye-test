from datetime import date
from decimal import Decimal

from dataclass.clips import Clip, ClipPlayer
from dataclass.games import Game
from dataclass.players import Player
from dataclass.teams import Team


def test_player_maps_the_players_table():
    player = Player(
        bbref_id="greenaj01",
        full_name="A.J. Green",
        first_name="A.J.",
        last_name="Green",
        position="SG",
        team_id=1,
    )

    assert player.headshot_url is None
    assert player.position == "SG"
    assert player.team_id == 1
    columns = Player.__table__.columns
    assert [column.name for column in columns] == [
        "id",
        "bbref_id",
        "full_name",
        "first_name",
        "last_name",
        "position",
        "headshot_url",
        "team_id",
    ]
    assert columns["id"].primary_key
    assert columns["bbref_id"].unique
    assert columns["full_name"].nullable is False
    assert columns["team_id"].nullable
    assert columns["position"].nullable
    assert columns["headshot_url"].nullable
    foreign_key = next(iter(columns["team_id"].foreign_keys))
    assert foreign_key.column.table.name == "teams"
    assert foreign_key.column.name == "id"
    assert player.team is None
    assert repr(player) == "Player(id=None, bbref_id='greenaj01', full_name='A.J. Green')"

    team = Team(abbr="MIL", city="Milwaukee", name="Bucks")
    assert repr(team) == "Team(id=None, abbr='MIL', city='Milwaukee', name='Bucks')"
    assert team.to_dict()["name"] == "Bucks"
    assert team.to_dict()["games"] is None
    assert "players" not in team.to_dict()

    game = Game(
        bbref_id="202601010MIL",
        season="2025-26",
        game_date=date(2026, 1, 1),
        home_team_id=1,
        away_team_id=2,
    )
    assert repr(game) == "Game(id=None, bbref_id='202601010MIL', season='2025-26', game_date=2026-01-01)"

    clip = Clip(
        game_id=1,
        game_date=date(2026, 1, 1),
        play_index=4,
        period=1,
        description="A.J. Green makes 3-pt jump shot",
        video_start_s=Decimal("12.000"),
        video_end_s=Decimal("18.000"),
    )
    assert clip.status == "pending"
    assert clip.attributes == {}
    assert repr(clip) == (
        "Clip(id=None, game_id=1, play_index=4, description='A.J. Green makes 3-pt jump shot')"
    )
    link = ClipPlayer(player_id=1, clip_id=1, role="shot", game_date=date(2026, 1, 1))
    assert repr(link) == "ClipPlayer(player_id=1, clip_id=1, role='shot')"
