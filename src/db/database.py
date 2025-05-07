# TODO: use a managed DB with PostgreSQL or MySQL instead of in memory SQLite for scalability and consistency

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import logging
from contextlib import contextmanager
from config import DATABASE_URL
from db import models  # noqa: F401 - Ensure models are loaded

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

@contextmanager
def get_db():
    """Dependency function to get a database session, usable as a context manager."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initializes the database by creating tables based on models."""
    # Import all modules here that define models so that
    # they are registered properly on the metadata. Otherwise
    # we need to import them first before calling init_db()
    from db.models import City, Museum, Base
    logging.info(f"Initializing database at {DATABASE_URL}")
    Base.metadata.create_all(bind=engine)
    logging.info("Database tables checked/created by init_db.") 