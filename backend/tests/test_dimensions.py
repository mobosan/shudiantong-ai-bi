import pytest
from datetime import date, timedelta
from app.models.entities import User
from app.schemas.contracts import Intent
from app.services.query_engine import build_sql, execute_readonly, period_range
from app.semantics.catalog import METRICS, DIMENSIONS
from app.core.config import settings
from app.services.parser import QueryError


@pytest.mark.parametrize('dimension', list(DIMENSIONS))
@pytest.mark.parametrize('metric', list(METRICS))
def test_metric_dimension_templates(db, metric, dimension):
    if dimension == 'channel' and METRICS[metric]['source'] == 'inventory':
        with pytest.raises(QueryError):
            build_sql(metric, Intent(metrics=[metric], dimension=dimension), User(role='store_manager', store_id=1), *period_range('last_30_days'))
        return
    start, end = period_range('last_30_days')
    sql, params = build_sql(metric, Intent(metrics=[metric], dimension=dimension), User(role='store_manager', store_id=1), start, end)
    rows = execute_readonly(db, sql, params)
    assert rows and len(rows) <= 1000
    if dimension == 'store':
        assert {row['dimension'] for row in rows} == {'上海静安店'}
    if METRICS[metric]['unit'] == '%':
        assert all(row['value'] is None or 0 <= row['value'] <= 100 for row in rows)


def test_date_comparison_alignment(client, login):
    response = client.post('/api/chat/query', headers=login('store1'), json={'question':'上周每天销售额环比'})
    assert response.status_code == 200, response.text
    result = response.json()
    assert len(result['chart_data']) == 7
    assert all(row['sales_amount_previous'] is not None and row['sales_amount_change_pct'] is not None for row in result['chart_data'])


def test_llm_structured_intent_and_reject_extra_sql(monkeypatch, client, login):
    import httpx
    monkeypatch.setattr(settings, 'llm_api_key', 'fake')
    monkeypatch.setattr(settings, 'llm_model', 'fake')
    content = {'metrics':['sales_amount'], 'dimension':'store', 'region':'华南区'}
    def response(*args, **kwargs):
        return httpx.Response(200, request=httpx.Request('POST','https://example.test'), json={'choices':[{'message':{'content':__import__('json').dumps(content)}}]})
    monkeypatch.setattr(httpx.Client, 'post', response)
    from app.services.parser import parse_intent
    intent, mode, _ = parse_intent('销售额')
    assert intent.region == '华南区' and mode == 'llm'
    content['sql'] = 'DROP TABLE users'
    intent, mode, warnings = parse_intent('昨天销售额')
    assert mode == 'rules_fallback' and warnings and intent.period == 'yesterday'


def test_calendar_boundaries():
    assert period_range('last_week', date(2026,10,19)) == (date(2026,10,12), date(2026,10,19))
    assert period_range('this_month', date(2026,11,1)) == (date(2026,11,1), date(2026,11,1))
