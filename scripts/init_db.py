"""Run from any directory: python scripts/init_db.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.core.database import Base, engine
from app.models import entities  # noqa: F401

if __name__ == '__main__':
    Base.metadata.create_all(engine)
    print('Database schema ready. Next: python scripts/seed_data.py')
