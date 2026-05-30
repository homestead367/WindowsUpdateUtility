import pytest
from app import create_app
from app.config import TestConfig
from app.database import Base, engine

@pytest.fixture
def app():
    application = create_app(TestConfig.__dict__)
    yield application

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def session(app):
    from app.database import get_session
    s = get_session()
    yield s
    s.close()
