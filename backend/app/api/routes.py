import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import current_user, admin_user, verify_password, create_token
from app.models.entities import User, AuditLog
from app.schemas.contracts import LoginRequest, QuestionRequest, UserView
from app.services.query_engine import run_query
from app.services.parser import QueryError
from app.semantics.catalog import CATALOG

router = APIRouter(prefix='/api')
logger = logging.getLogger(__name__)


@router.get('/health')
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {'status': 'ok', 'service': 'shudiantong-ai-bi'}


@router.post('/auth/login')
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == body.username))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, '用户名或密码错误')
    return {'access_token': create_token(user), 'token_type': 'bearer', 'user': UserView.model_validate(user)}


@router.get('/auth/me', response_model=UserView)
def me(user: User = Depends(current_user)):
    return user


@router.post('/chat/query')
def query(body: QuestionRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        return run_query(body.question, user, db)
    except QueryError as exc:
        raise HTTPException(422, str(exc))
    except Exception:
        logger.exception('Query execution failed for user_id=%s', user.id)
        raise HTTPException(500, '查询执行失败，已记录审计，请稍后重试')


@router.get('/chat/history')
def history(user: User = Depends(current_user), db: Session = Depends(get_db), limit: int = Query(30, ge=1, le=100)):
    rows = db.scalars(select(AuditLog).where(AuditLog.user_id == user.id).order_by(AuditLog.id.desc()).limit(limit)).all()
    return [{'id': r.id, 'question': r.question, 'status': r.status, 'created_at': r.created_at, 'response': json.loads(r.response_json) if r.response_json else None} for r in reversed(rows)]


@router.get('/metadata/metrics')
def metrics(user: User = Depends(current_user)):
    return CATALOG


@router.get('/admin/audit-logs')
def audit(user: User = Depends(admin_user), db: Session = Depends(get_db), page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    total = db.scalar(select(func.count(AuditLog.id)))
    rows = db.execute(select(AuditLog, User.username).join(User, User.id == AuditLog.user_id).order_by(AuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return {'total': total, 'items': [{'id': r.id, 'user_id': r.user_id, 'username': name, 'question': r.question, 'generated_sql': r.generated_sql,
                                      'status': r.status, 'latency_ms': r.latency_ms, 'created_at': r.created_at} for r, name in rows]}
