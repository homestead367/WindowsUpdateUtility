from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

class Base(DeclarativeBase):
    pass

engine = None
SessionLocal = None

def init_db(app):
    global engine, SessionLocal
    engine = create_engine(
        app.config['DATABASE_URL'],
        connect_args={'check_same_thread': False}
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False)
    Base.metadata.create_all(engine)

def get_session():
    return SessionLocal()
