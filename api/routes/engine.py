from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# One engine for DATABASE_URL_SQLALCHEMY. Read it on first use so dotenv
# has already loaded; this module is imported before the app starts.
engine = None
SessionLocal = sessionmaker(autoflush=False)


def dispose_engine():
    """Close pooled connections so a local test database can shut down."""
    global engine
    if engine is not None:
        engine.dispose()
        engine = None


def open_session():
    """Open a session on the shared engine."""
    global engine
    if engine is None:
        url = os.environ.get("DATABASE_URL_SQLALCHEMY")
        if not url:
            raise RuntimeError("DATABASE_URL_SQLALCHEMY is not set")
        engine = create_engine(url, pool_size=10, connect_args={"connect_timeout": 8})
        SessionLocal.configure(bind=engine)
    return SessionLocal()
