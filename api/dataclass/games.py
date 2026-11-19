from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Numeric,
    SmallInteger,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .teams import Team


class Game(Base):
    """One row of the games table. The database assigns id and created_at."""

    __tablename__ = "games"
    __table_args__ = (CheckConstraint("home_team_id <> away_team_id"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True, init=False)
    bbref_id: Mapped[str] = mapped_column(Text, unique=True)
    season: Mapped[str] = mapped_column(Text)
    game_date: Mapped[date] = mapped_column(Date)
    home_team_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("teams.id"))
    away_team_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("teams.id"))
    s3_key: Mapped[str | None] = mapped_column(Text, default=None)
    duration_s: Mapped[Decimal | None] = mapped_column(Numeric(9, 3), default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), init=False, server_default=func.now()
    )
    home_team: Mapped[Team | None] = relationship(foreign_keys=[home_team_id], default=None)
    away_team: Mapped[Team | None] = relationship(foreign_keys=[away_team_id], default=None)

    def __repr__(self) -> str:
        return (
            f"Game(id={self.id}, bbref_id={self.bbref_id!r}, "
            f"season={self.season!r}, game_date={self.game_date})"
        )
