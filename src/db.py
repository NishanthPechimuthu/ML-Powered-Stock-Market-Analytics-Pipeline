"""
Database connection helpers for Supabase PostgreSQL.
Uses SQLAlchemy with connection pooling.
"""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from src.config import DATABASE_URL

_engine: Engine | None = None


def get_engine() -> Engine:
    """Return a singleton SQLAlchemy engine with connection pooling."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            DATABASE_URL,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,  # verify connections before use
            connect_args={
                "sslmode": "require",  # Supabase requires SSL
            },
        )
    return _engine


def get_connection():
    """Return a new database connection from the pool."""
    return get_engine().connect()
