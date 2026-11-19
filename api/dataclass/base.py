from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import inspect
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass, RelationshipProperty


class Base(MappedAsDataclass, DeclarativeBase):
    def to_dict(self):
        """Column values for JSON. Relationships are left out."""
        data = {}
        for attr in inspect(self).mapper.attrs:
            if isinstance(attr, RelationshipProperty):
                continue
            value = getattr(self, attr.key)
            if isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, date):
                value = value.isoformat()
            elif isinstance(value, Decimal):
                value = int(value) if value == value.to_integral_value() else float(value)
            data[attr.key] = value
        return data