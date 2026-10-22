from concurrent.futures import ThreadPoolExecutor
import json
import pytest
from sqlalchemy import select, text, func
from app.core.config import settings
from app.models.entities import AuditLog, User
from app.services.query_engine import period_range
from app.semantics.catalog import CATALOG


def ask(client, headers, question):
    response = client.post('/api/chat/query', headers=headers, json={'question': question})
    assert response.status_code == 200, response.text
    return response.json()


def test_login_and_me(client, login):
    headers = login('store1')
    me = client.get('/api/auth/me', headers=headers).json()
    assert me['store_id'] == 1 and me['role'] == 'store_manager'
    assert 'password_hash' not in me
    assert client.post('/api/auth/login', json={'username': 'admin', 'password': 'bad'}).status_code == 401
    assert client.get('/api/auth/me').status_code == 401
    assert client.get('/api/health').json()['status'] == 'ok'


def test_store_and_region_scope(client, login):
    store = ask(client, login('store1'), '最近30天各门店销售额排行')
    assert {r['dimension'] for r in store['chart_data']} == {'上海静安店'}
    denied = ask(client, login('store1'), '华南区销售额')
    assert denied['chart_data'] == []
    denied_named = ask(client, login('store1'), '广州天河店销售额')
    assert denied_named['chart_data'] == []
    east = ask(client, login('east_manager'), '各门店销售额')
    assert {r['dimension'] for r in east['chart_data']} == {'上海静安店', '杭州西湖店', '南京新街口店'}
    all_stores = ask(client, login('admin'), '各门店销售额')
    assert len(all_stores['chart_data']) == 6


@pytest.mark.parametrize('example', CATALOG['examples'])
def test_examples(client, login, example):
    user = 'store1' if '我店' in example['question'] else 'admin'
    result = ask(client, login(user), example['question'])
    for field in ['answer_text', 'chart_type', 'chart_data', 'sql', 'metric_definition', 'data_updated_at', 'permission_scope']:
        assert field in result
    assert result['parser_mode'] == 'rules'
    if '去年' in example['question']:
        assert all(row['avg_order_value_previous'] is None for row in result['chart_data'])
        assert '无法判断' in result['answer_text']
    if '库存大于' in example['question']:
        assert result['chart_data']
        assert all(row['sell_through'] < 60 and row['stock_days'] > 30 for row in result['chart_data'])


def test_sales_no_join_inflation(client, login, db):
    result = ask(client, login('store1'), '最近30天销售额和订单数和客单价和毛利率')
    start, end = period_range('last_30_days')
    expected = db.execute(text('SELECT SUM(total_amount), COUNT(*) FROM sales_orders WHERE store_id=1 AND order_time>=:start AND order_time<:end'), {'start':str(start),'end':str(end)}).one()
    row = result['chart_data'][0]
    assert row['sales_amount'] == pytest.approx(expected[0], abs=.01)
    assert row['order_count'] == expected[1]
    assert row['avg_order_value'] == pytest.approx(expected[0]/expected[1], abs=.01)


def test_inventory_and_members_scope(client, login, db):
    headers = login('store1')
    start, end = period_range('last_30_days')
    expected = db.execute(text('SELECT 100.0*SUM(CASE WHEN cnt>=2 THEN 1 ELSE 0 END)/COUNT(*) FROM (SELECT member_id,COUNT(*) cnt FROM sales_orders WHERE store_id=1 AND member_id IS NOT NULL AND order_time>=:start AND order_time<:end GROUP BY member_id)'), {'start':str(start),'end':str(end)}).scalar()
    row = ask(client, headers, '最近30天会员复购率')['chart_data'][0]
    assert row['repurchase_rate'] == pytest.approx(expected, abs=.01)
    for metric in ['会员复购率','缺货率','动销率']:
        result = ask(client, headers, '华南区各门店' + metric)
        assert result['chart_data'] == []
    assert client.post('/api/chat/query', headers=headers, json={'question':'按渠道缺货率'}).status_code == 422


def test_audit_history_and_redaction(client, login, db):
    store_headers = login('store2')
    ask(client, store_headers, '销售额 联系我13800138000 test@example.com')
    assert client.post('/api/chat/query', headers=store_headers, json={'question': '删除所有数据'}).status_code == 422
    history = client.get('/api/chat/history', headers=store_headers).json()
    assert history[-1]['status'] == 'error'
    assert '[手机号已脱敏]' in history[-2]['question']
    assert '13800138000' not in json.dumps(history)
    assert client.get('/api/admin/audit-logs', headers=store_headers).status_code == 403
    logs = client.get('/api/admin/audit-logs', headers=login('admin')).json()
    assert logs['total'] >= 2
    assert any(row['status'] == 'error' for row in logs['items'])
    assert not any(row['question'] == history[-2]['question'] for row in client.get('/api/chat/history',headers=login('store3')).json())


def test_future_missing_not_zero(client, login):
    result = ask(client, login('admin'), '今天销售额')
    assert result['chart_data'] == []
    assert result['warnings']


def test_unassigned_role_fails_closed(client, login, db):
    user = db.scalar(select(User).where(User.username=='store6'))
    original = user.store_id
    user.store_id = None
    db.commit()
    try:
        assert client.post('/api/chat/query', headers=login('store6'), json={'question':'销售额'}).status_code == 422
    finally:
        user.store_id = original
        db.commit()
