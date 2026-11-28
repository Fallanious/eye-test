from flask import jsonify
from sqlalchemy import create_engine, text
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


def connect():
    """Open a read-only session. Callers close it with a `with` block."""
    if not os.environ.get("DATABASE_URL_SQLALCHEMY"):
        return None, (jsonify(error="Player library is unavailable."), 503)
    session = None
    try:
        session = open_session()
        session.execute(text("SET TRANSACTION READ ONLY"))
        session.execute(text("SET LOCAL statement_timeout = '8s'"))
    except Exception:
        if session is not None:
            session.close()
        return None, (jsonify(error="Unable to connect."), 503)
    return session, None
