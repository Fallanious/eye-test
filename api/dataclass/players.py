from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, Identity, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
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
    team: Mapped[Team | None] = relationship(back_populates="players", default=None)

    def __repr__(self) -> str:
        return f"Player(id={self.id}, bbref_id={self.bbref_id!r}, full_name={self.full_name!r})"
