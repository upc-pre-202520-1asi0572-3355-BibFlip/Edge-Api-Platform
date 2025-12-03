import os
from typing import Any, AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import logging

logger = logging.getLogger(__name__)

# Database URL from environment or default
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://useradmin:Bibflip123@db-bibflip-server.postgres.database.azure.com:5432/bibflip_azure_db"
)

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600
)

@event.listens_for(engine.sync_engine, "connect")
def set_timezone(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("SET TIME ZONE 'America/Lima'")
    cursor.close()

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Base for models
Base = declarative_base()


async def init_db():
    """Initialize database tables"""
    logger.info("Initializing database...")
    try:
        async with engine.begin() as conn:
            # Create tables if they don't exist
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise


async def close_db():
    """Close database connections"""
    logger.info("Closing database connections...")
    await engine.dispose()
    logger.info("Database connections closed")


async def get_db_session() -> AsyncGenerator[AsyncSession | Any, Any]:
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()