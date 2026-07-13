"""Database engine / session plumbing."""

from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app import config

connect_args = (
    {"check_same_thread": False}
    if config.DATABASE_URL.startswith("sqlite")
    else {}
)
engine = create_engine(config.DATABASE_URL, connect_args=connect_args)


def init_db() -> None:
    """Create tables and bind the ActiveRecord session."""
    from app import models  # noqa: F401  (register tables)

    SQLModel.metadata.create_all(engine)
    models.Screening.set_session(Session(engine))


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
