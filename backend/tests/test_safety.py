import pytest
from pydantic import ValidationError
from app.services.sql_safety import validate_sql
from app.services.parser import QueryError, parse_intent
from app.services.query_engine import build_sql, execute_readonly
from app.schemas.contracts import Intent
from app.models.entities import User
from app.core.config import settings
from datetime import date


@pytest.mark.parametrize('sql', [
    'DELETE FROM stores', 'SELECT store_name FROM stores; DROP TABLE stores',
    'SELECT store_name FROM stores -- comment', 'SELECT /* comment */ store_name FROM stores',
    'SELECT password_hash FROM users LIMIT 10', 'SELECT member_no FROM members LIMIT 10',
    'SELECT secret FROM stores LIMIT 10', 'SELECT load_extension(:file) FROM stores LIMIT 10',
    'SELECT store_name FROM stores LIMIT 1001', 'SELECT store_name FROM stores',
    'SELECT * FROM stores LIMIT 10', 'SELECT name FROM sqlite_master LIMIT 10',
    'WITH stolen AS (DELETE FROM stores RETURNING id) SELECT id FROM stolen LIMIT 10',
    'SELECT store_name FROM stores UNION SELECT password_hash FROM users LIMIT 10',
    'SELECT store_name FROM other.stores LIMIT 10',
])
def test_reject_unsafe_sql(sql):
    with pytest.raises(QueryError):
        validate_sql(sql)


def test_select_allowed():
    validate_sql('SELECT s.store_name AS dimension, COUNT(s.id) AS value FROM stores s WHERE s.region = :region GROUP BY s.store_name LIMIT 100')


def test_parameterized_injection_and_scope():
    intent = Intent(metrics=['sales_amount'], store="x' OR 1=1 --")
    sql, params = build_sql('sales_amount', intent, User(role='store_manager',store_id=1), date(2026,1,1),date(2026,2,1))
    assert "x'" not in sql and ':scope' in sql
    assert params['filter_store'] == intent.store and params['scope'] == 1


def test_intent_disallows_sql():
    with pytest.raises(ValidationError):
        Intent.model_validate({'metrics':['sales_amount'], 'sql':'DROP TABLE users'})


def test_llm_failure_falls_back(monkeypatch):
    import httpx
    monkeypatch.setattr(settings, 'llm_api_key', 'fake')
    monkeypatch.setattr(settings, 'llm_model', 'fake')
    def fail(*args, **kwargs):
        raise httpx.ConnectError('offline')
    monkeypatch.setattr(httpx.Client, 'post', fail)
    intent, mode, warnings = parse_intent('昨天销售额')
    assert intent.period == 'yesterday' and mode == 'rules_fallback' and warnings


def test_database_query_only_enforcement(db):
    with pytest.raises(Exception):
        execute_readonly(db, 'DELETE FROM stores', {})
    # Connection is reset after failure and audit can still be written by the app.
    assert db.execute(__import__('sqlalchemy').text('SELECT COUNT(*) FROM stores')).scalar() == 6
