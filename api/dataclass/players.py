from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Identity, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column, query_expression, relationship

from .base import Base

if TYPE_CHECKING:
    from .teams import Team


class Player(Base):
    """One row of the players table. The database assigns id."""

    __tablename__ = "players"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True, init=False)
    bbref_id: Mapped[str] = mapped_column(Text, unique=True)
    full_name: Mapped[str] = mapped_column(Text)
    first_name: Mapped[str] = mapped_column(Text)
    last_name: Mapped[str] = mapped_column(Text)
    position: Mapped[str | None] = mapped_column(Text, default=None)
    headshot_url: Mapped[str | None] = mapped_column(Text, default=None)
    team_id: Mapped[int | None] = mapped_column(SmallInteger, ForeignKey("teams.id"), default=None)
    team: Mapped[Team | None] = relationship("Team", back_populates="players", default=None)
    clips: Mapped[int | None] = query_expression()
    games: Mapped[int | None] = query_expression()

    def to_dict(self):
        """Fields the player card reads. position is the card word, team is an abbreviation."""
        from routes.players import position_label

        return {
            "id": self.id,
            "bbref_id": self.bbref_id,
            "full_name": self.full_name,
            "position": position_label(self.position),
            "headshot_url": self.headshot_url,
            "team": self.team.abbr if self.team else "",
            "clips": self.clips,
            "games": self.games,
        }

    def __repr__(self) -> str:
        return f"Player(id={self.id}, bbref_id={self.bbref_id!r}, full_name={self.full_name!r})"
