import os
from dotenv import load_dotenv
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

load_dotenv()

DATABASE_URL = (f"postgresql+asyncpg://"
                f"{os.getenv("DB_USER")}:{os.getenv("DB_PASSWORD")}@"
                f"{os.getenv("DB_HOST")}:{os.getenv("DB_PORT")}/"
                f"{os.getenv("DB_NAME")}")

engine = create_async_engine(DATABASE_URL)

AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

Base = declarative_base()

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
