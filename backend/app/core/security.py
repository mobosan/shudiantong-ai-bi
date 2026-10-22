import hashlib
import hmac
import secrets
from datetime import timedelta
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import now, settings
from app.core.database import get_db
from app.models.entities import User

bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 310000).hex()
    return f'pbkdf2_sha256$310000${salt}${digest}'


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt, digest = stored.split('$')
        calculated = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), int(iterations)).hex()
        return hmac.compare_digest(digest, calculated)
    except (ValueError, TypeError):
        return False


def create_token(user: User):
    return jwt.encode({'sub': str(user.id), 'exp': now() + timedelta(minutes=settings.jwt_expire_minutes)}, settings.jwt_secret, algorithm='HS256')


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    try:
        if not credentials:
            raise ValueError()
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=['HS256'], options={'require': ['exp', 'sub']})
        user = db.scalar(select(User).where(User.id == int(payload['sub'])))
        if user is None or user.role not in {'admin', 'regional_manager', 'store_manager'}:
            raise ValueError()
        return user
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(401, '登录已失效，请重新登录')


def admin_user(user: User = Depends(current_user)):
    if user.role != 'admin':
        raise HTTPException(403, '仅管理员可访问审计日志')
    return user
