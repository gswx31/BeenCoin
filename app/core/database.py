from sqlmodel import create_engine, Session
from app.core.config import settings
from contextlib import contextmanager

engine = create_engine(settings.DATABASE_URL)

@contextmanager
def get_session():
    with Session(engine) as session:
        yield session
