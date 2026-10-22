from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import ROOT, settings


class Base(DeclarativeBase):
    pass


url = settings.database_url
if url.startswith('sqlite:///./'):
    path = ROOT / url.removeprefix('sqlite:///./')
    path.parent.mkdir(parents=True, exist_ok=True)
    url = 'sqlite:///' + path.as_posix()
engine = create_engine(url, connect_args={'check_same_thread': False})


@event.listens_for(engine, 'connect')
def configure_sqlite(connection, _):
    connection.execute('PRAGMA foreign_keys=ON')
    connection.execute('PRAGMA busy_timeout=5000')
    connection.execute('PRAGMA journal_mode=WAL')


SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db():
    with SessionLocal() as session:
        yield session
