from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    Interval,
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import Mapped, mapped_column, query_expression, relationship

from .games import Game
from .base import Base
from .teams import Team

CLIP_ROLE = ENUM(
    "shot", "assist", "block", "steal", "rebound", "foul", "fouled", "turnover",
    name="clip_role",
    create_type=False,
)
CLIP_STATUS = ENUM(
    "pending", "rendered", "uploaded", "failed",
    name="clip_status",
    create_type=False,
)


class Clip(Base):
    """One row of the clips table. The database assigns id, duration, and timestamps."""

    __tablename__ = "clips"
    __table_args__ = (
        UniqueConstraint("game_id", "play_index"),
        CheckConstraint("period >= 1 AND period <= 10"),
        CheckConstraint("video_end_s > video_start_s"),
        CheckConstraint("video_start_s >= 0"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True, init=False)
    game_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("games.id", ondelete="CASCADE"))
    game_date: Mapped[date] = mapped_column(Date)
    play_index: Mapped[int] = mapped_column(Integer)
    period: Mapped[int] = mapped_column(SmallInteger)
    description: Mapped[str] = mapped_column(Text)
    video_start_s: Mapped[Decimal] = mapped_column(Numeric(9, 3))
    video_end_s: Mapped[Decimal] = mapped_column(Numeric(9, 3))
    team_id: Mapped[int | None] = mapped_column(SmallInteger, ForeignKey("teams.id"), default=None)
    game_clock: Mapped[timedelta | None] = mapped_column(Interval, default=None)
    action_type: Mapped[str | None] = mapped_column(Text, default=None)
    shot_subtype: Mapped[str | None] = mapped_column(Text, default=None)
    outcome: Mapped[str | None] = mapped_column(Text, default=None)
    attributes: Mapped[dict] = mapped_column(
        JSONB, default_factory=dict, server_default=text("'{}'::jsonb")
    )
    s3_key: Mapped[str | None] = mapped_column(Text, unique=True, default=None)
    status: Mapped[str] = mapped_column(CLIP_STATUS, default="pending", server_default="pending")
    duration_s: Mapped[Decimal] = mapped_column(
        Numeric(9, 3),
        Computed("video_end_s - video_start_s", persisted=True),
        init=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), init=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), init=False, server_default=func.now()
    )
    game: Mapped[Game | None] = relationship(default=None)
    team: Mapped[Team | None] = relationship(default=None)
    roles: Mapped[list[str] | None] = query_expression()

    def category_keys(self):
        """Browse categories for this clip, in the order the filters are listed."""
        from routes.teams import clip_categories

        return clip_categories(self.description, self.action_type, self.shot_subtype, self.roles)

    def to_dict(self):
        """Fields the game clip list reads. Clock and duration are display labels."""
        from routes.players import clock_label, duration_label

        return {
            "id": self.id,
            "description": self.description,
            "period": self.period,
            "game_clock": clock_label(self.game_clock),
            "duration_label": duration_label(self.duration_s),
            "categories": self.category_keys(),
        }

    def __repr__(self) -> str:
        return (
            f"Clip(id={self.id}, game_id={self.game_id}, "
            f"play_index={self.play_index}, description={self.description!r})"
        )


class ClipPlayer(Base):
    """One player role on a clip."""

    __tablename__ = "clip_players"

    player_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("players.id", ondelete="CASCADE"), primary_key=True
    )
    clip_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("clips.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(CLIP_ROLE, primary_key=True)
    game_date: Mapped[date] = mapped_column(Date)

    def to_dict(self):
        """Fields that identify one player on a clip."""
        return {
            "player_id": self.player_id,
            "clip_id": self.clip_id,
            "role": self.role,
        }

    def __repr__(self) -> str:
        return f"ClipPlayer(player_id={self.player_id}, clip_id={self.clip_id}, role={self.role!r})"
