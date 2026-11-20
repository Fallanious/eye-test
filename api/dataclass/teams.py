from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Identity, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, query_expression, relationship

from .base import Base

if TYPE_CHECKING:
    from .players import Player


class Team(Base):
    """One row of the teams table. The database assigns id and created_at."""

    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(SmallInteger, Identity(always=True), primary_key=True, init=False)
    abbr: Mapped[str] = mapped_column(String(3), unique=True)
    city: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), init=False, server_default=func.now()
    )
    games: Mapped[int | None] = query_expression()
    players: Mapped[list[Player]] = relationship("Player", back_populates="team", default_factory=list)

    def to_dict(self):
        """Fields the team list reads."""
        return {
            "id": self.id,
            "abbr": self.abbr,
            "name": self.name,
            "games": self.games,
        }

    def __repr__(self) -> str:
        return f"Team(id={self.id}, abbr={self.abbr!r}, city={self.city!r}, name={self.name!r})"