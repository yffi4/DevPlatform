import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

load_dotenv()

DATABASE_URL = os.getenv('SYNC_DATABASE_URL')
ASYNC_DATABASE_URL = os.getenv('ASYNC_DATABASE_URL')    

engine = create_engine(DATABASE_URL)
async_engine = create_async_engine(ASYNC_DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
AsyncSessionLocal = async_sessionmaker(bind=async_engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_db():
    async with AsyncSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()

