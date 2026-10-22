import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.core.database import Base, get_db
from app.main import app
from app.core.config import settings
from scripts.seed_data import seed


@pytest.fixture(scope='session')
def test_engine(tmp_path_factory):
    path = tmp_path_factory.mktemp('db') / 'test.db'
    engine = create_engine('sqlite:///' + path.as_posix(), connect_args={'check_same_thread': False})
    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        seed(db)
    yield engine
    engine.dispose()


@pytest.fixture
def db(test_engine):
    with sessionmaker(bind=test_engine, expire_on_commit=False)() as session:
        yield session


@pytest.fixture
def client(test_engine, monkeypatch):
    monkeypatch.setattr(settings, 'llm_api_key', '')
    def override_db():
        with sessionmaker(bind=test_engine, expire_on_commit=False)() as db:
            yield db
    app.dependency_overrides[get_db] = override_db
    # No app lifespan: tests must never create or alter the demo DB.
    client = TestClient(app)
    yield client
    client.close()
    app.dependency_overrides.clear()


@pytest.fixture
def login(client):
    def login_as(username):
        result = client.post('/api/auth/login', json={'username': username, 'password': settings.demo_password})
        assert result.status_code == 200
        return {'Authorization': 'Bearer ' + result.json()['access_token']}
    return login_as
