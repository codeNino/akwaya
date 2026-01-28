"""
Database session management
"""

from contextlib import contextmanager, asynccontextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from internal.utils.logger import AppLogger
from internal.config.secret import SecretManager
from internal.utils.database.models import Base

logger = AppLogger("utils.database.session")()

# Global engine and session factory
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create database engine"""
    global _engine
    if _engine is None:
        connection_string = SecretManager.PG_URI
        if not connection_string:
            raise ValueError("PostgreSQL connection string (PG_URI) is required")
        
        _engine = create_engine(
            connection_string,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,  # Verify connections before using
            echo=False  # Set to True for SQL query logging
        )
        logger.info("Database engine created")
    
    return _engine


def get_session_factory():
    """Get or create session factory"""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine
        )
        logger.info("Session factory created")
    
    return _SessionLocal


def inject_session() -> Generator[Session, None, None]:
    SessionLocal = get_session_factory()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Get a database session context manager
    
    Usage:
        with get_session() as session:
            # Use session here
            pass
    """
    SessionLocal = get_session_factory()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(drop_existing: bool = False):
    """
    Initialize database tables
    
    Args:
        drop_existing: If True, drop all tables before creating (use with caution!)
    """
    engine = get_engine()
    
    if drop_existing:
        logger.warning("Dropping all existing tables...")
        Base.metadata.drop_all(engine)
    
    logger.info("Creating database tables...")
    Base.metadata.create_all(engine)
    logger.info("Database tables created successfully")

