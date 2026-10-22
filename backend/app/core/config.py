from pathlib import Path
from zoneinfo import ZoneInfo
from datetime import datetime
import secrets
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    database_url: str = 'sqlite:///./data/shudiantong.db'
    jwt_secret: str = ''
    jwt_expire_minutes: int = 480
    cors_origins: str = 'http://localhost:5173,http://127.0.0.1:5173'
    llm_base_url: str = 'https://api.openai.com/v1'
    llm_api_key: str = ''
    llm_model: str = ''
    llm_timeout_seconds: float = 15
    demo_password: str = 'Demo123!'
    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore')


settings = Settings()
if not settings.jwt_secret:
    settings.jwt_secret = secrets.token_urlsafe(48)


def now():
    return datetime.now(ZoneInfo('Asia/Shanghai'))
