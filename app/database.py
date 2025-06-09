"""
Database configuration for multi-tenant FastAPI application
Following Rule 2.1: Always Use Async Functions
"""

from typing import AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Create the declarative base
Base = declarative_base()

# Global engine variables
engine = None
async_engine = None
SessionLocal = None
AsyncSessionLocal = None


def init_database():
    """
    Initialize database engines and session factories
    """
    global engine, async_engine, SessionLocal, AsyncSessionLocal
    
    settings = get_settings()
    
    # Sync engine for legacy compatibility
    engine = create_engine(
        settings.get_database_url(),
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        echo=settings.DEBUG,
    )
    
    # Async engine for modern FastAPI
    async_database_url = settings.get_database_url().replace("postgresql://", "postgresql+asyncpg://")
    async_engine = create_async_engine(
        async_database_url,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        echo=settings.DEBUG,
    )
    
    # Session factories
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    AsyncSessionLocal = async_sessionmaker(
        async_engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    
    logger.info("Database initialized successfully")


# Dependency for getting sync database session (legacy)
def get_db() -> Session:
    """
    Dependency for getting synchronous database session
    Used for legacy code compatibility
    """
    if not SessionLocal:
        init_database()
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Dependency for getting async database session (modern)
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting asynchronous database session
    Following Rule 2.1: Always Use Async Functions
    """
    if not AsyncSessionLocal:
        init_database()
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# Database utilities
async def create_tables():
    """
    Create all database tables
    """
    if not async_engine:
        init_database()
    
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("All database tables created")


async def drop_tables():
    """
    Drop all database tables (use with caution!)
    """
    if not async_engine:
        init_database()
    
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    logger.info("All database tables dropped")


# Health check utilities
async def check_database_health() -> bool:
    """
    Check database connection health
    """
    try:
        if not async_engine:
            init_database()
        
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


def get_sync_db_session() -> Session:
    """
    Get a synchronous database session for scripts or non-async contexts
    """
    if not SessionLocal:
        init_database()
    
    return SessionLocal()


# Database transaction utilities
async def execute_in_transaction(func, *args, **kwargs):
    """
    Execute a function in a database transaction
    """
    async with AsyncSessionLocal() as session:
        try:
            result = await func(session, *args, **kwargs)
            await session.commit()
            return result
        except Exception as e:
            await session.rollback()
            logger.error(f"Transaction failed: {e}")
            raise


# Multi-tenant database utilities
class TenantDatabaseManager:
    """
    Manager for tenant-specific database operations
    Following Rule 3.1: Data Isolation by Tenant ID
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
    
    async def get_tenant_data(self, model_class, session: AsyncSession, filters: dict = None):
        """
        Get data for specific tenant with automatic isolation
        """
        from sqlalchemy import select
        
        query = select(model_class).where(model_class.tenant_id == self.tenant_id)
        
        if filters:
            for key, value in filters.items():
                if hasattr(model_class, key):
                    query = query.where(getattr(model_class, key) == value)
        
        result = await session.execute(query)
        return result.scalars().all()
    
    async def create_tenant_data(self, instance, session: AsyncSession):
        """
        Create data with automatic tenant assignment
        """
        instance.tenant_id = self.tenant_id
        session.add(instance)
        await session.commit()
        await session.refresh(instance)
        return instance
    
    async def update_tenant_data(self, model_class, item_id: str, updates: dict, session: AsyncSession):
        """
        Update data with tenant isolation check
        """
        from sqlalchemy import select
        
        query = select(model_class).where(
            model_class.id == item_id,
            model_class.tenant_id == self.tenant_id
        )
        result = await session.execute(query)
        item = result.scalar_one_or_none()
        
        if not item:
            raise ValueError("Item not found or not accessible")
        
        for key, value in updates.items():
            if hasattr(item, key):
                setattr(item, key, value)
        
        await session.commit()
        await session.refresh(item)
        return item
    
    async def delete_tenant_data(self, model_class, item_id: str, session: AsyncSession):
        """
        Delete data with tenant isolation check
        """
        from sqlalchemy import select, delete
        
        query = select(model_class).where(
            model_class.id == item_id,
            model_class.tenant_id == self.tenant_id
        )
        result = await session.execute(query)
        item = result.scalar_one_or_none()
        
        if not item:
            raise ValueError("Item not found or not accessible")
        
        delete_query = delete(model_class).where(
            model_class.id == item_id,
            model_class.tenant_id == self.tenant_id
        )
        await session.execute(delete_query)
        await session.commit()
        
        return True


# Database migration utilities
async def run_migrations():
    """
    Run database migrations
    """
    try:
        # This would integrate with Alembic in production
        await create_tables()
        logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.error(f"Database migration failed: {e}")
        raise


# Initialize database on import
try:
    init_database()
except Exception as e:
    logger.warning(f"Database initialization failed: {e}")
    logger.warning("Database will be initialized on first use")