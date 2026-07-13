"""Persistence models.

Privacy-first: only the structured household profile and the engine's
determinations are stored — never names, contact info, payment handles,
or (by default) the raw narrative text.
"""

from datetime import datetime

from sqlalchemy import func
from sqlalchemy_mixins.activerecord import ActiveRecordMixin
from sqlmodel import JSON, Column, Field, SQLModel


class Screening(SQLModel, ActiveRecordMixin, table=True):
    """One anonymous screening run: profile in, determinations out."""

    id: int | None = Field(default=None, primary_key=True)
    profile: dict = Field(sa_column=Column(JSON))
    determinations: list = Field(sa_column=Column(JSON))
    engine_version: str = Field(default="")
    # Only populated when config.STORE_NARRATIVES is True (debug only).
    narrative: str | None = Field(default=None)
    created_at: datetime | None = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )
