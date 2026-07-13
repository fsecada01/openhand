"""Database engine / session plumbing."""

from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine, select

from app import config

connect_args = (
    {"check_same_thread": False}
    if config.DATABASE_URL.startswith("sqlite")
    else {}
)
engine = create_engine(config.DATABASE_URL, connect_args=connect_args)


def init_db() -> None:
    """Create tables, bind the ActiveRecord session, seed reference data."""
    from app import models  # noqa: F401  (register tables)

    SQLModel.metadata.create_all(engine)
    models.Screening.set_session(Session(engine))
    _seed_disability_conditions()


def _seed_disability_conditions() -> None:
    from app.models import DisabilityCondition
    from app.seed_data import DISABILITY_CONDITIONS

    with Session(engine) as session:
        if session.exec(select(DisabilityCondition)).first():
            return
        for name, category, aliases, ssa_reference in DISABILITY_CONDITIONS:
            session.add(
                DisabilityCondition(
                    name=name,
                    category=category,
                    aliases=aliases,
                    ssa_reference=ssa_reference,
                )
            )
        session.commit()


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
