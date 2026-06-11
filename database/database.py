from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from config import settings
from database.models import Base

# Create async engine (connection pool to PostgreSQL)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Dependency for FastAPI (we'll use this later in auth/routes)
async def get_db():
    """
    Dependency that provides database session to API endpoints.
    Usage:
        async def my_endpoint(db: AsyncSession = Depends(get_db)):
            results = await db.execute(...)
    """
    async with AsyncSessionLocal() as session:
        yield session

# Function to create all tables
async def init_db():
    """
    Creates all tables in PostgreSQL based on models.
    Run this once at startup.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)