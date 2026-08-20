from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from config import settings
from database.models import Base

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_size=30,
    max_overflow=30,   # 60 max, same as your last successful run
    pool_timeout=30,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

import time

async def get_db():
    start = time.perf_counter()

    async with AsyncSessionLocal() as session:
        acquire_time = (time.perf_counter() - start) * 1000
        print(f"[POOL] Session acquired: {acquire_time:.2f} ms")

        yield session

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)