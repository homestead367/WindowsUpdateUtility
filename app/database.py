from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

class Base(DeclarativeBase):
    pass

engine = None
SessionLocal = None

def init_db(app):
    global engine, SessionLocal
    is_sqlite = app.config['DATABASE_URL'].startswith('sqlite')
    connect_args = {'check_same_thread': False} if is_sqlite else {}
    engine = create_engine(app.config['DATABASE_URL'], connect_args=connect_args)
    SessionLocal = sessionmaker(bind=engine, autoflush=False)
    Base.metadata.create_all(engine)

    @app.teardown_appcontext
    def close_session(exc):
        pass  # sessions are closed explicitly by callers; hook reserved for future use

def get_session():
    if SessionLocal is None:
        raise RuntimeError('Database not initialized — call init_db() first')
    return SessionLocal()
