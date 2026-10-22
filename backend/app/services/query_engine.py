from datetime import date, timedelta
from time import perf_counter
import json
import re
from sqlalchemy import select, func, text
from sqlalchemy.orm import Session
from app.core.config import now
from app.models.entities import AuditLog, Store, Product, SalesOrder, InventorySnapshot, User
from app.schemas.contracts import Intent
from app.semantics.catalog import CATALOG, METRICS, DIMENSIONS
from app.services.parser import QueryError, parse_intent
from app.services.sql_safety import validate_sql


def redact(value: str):
    value = re.sub(r'(?<!\d)1[3-9]\d{9}(?!\d)', '[手机号已脱敏]', value)
    value = re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[邮箱已脱敏]', value)
    return re.sub(r'(?<!\d)\d{17}[\dXx](?!\w)', '[身份证已脱敏]', value)


def permission(user: User):
    rule = CATALOG['permissions'].get(user.role)
    if rule is None:
        raise QueryError('角色未配置权限')
    if user.role == 'admin':
        return '1=1', {}, '全部门店'
    value = getattr(user, rule['user_attribute'])
    if value is None:
        raise QueryError('账号未配置门店或区域，已拒绝查询')
    return f"{rule['field']} = :scope", {'scope': value}, f'门店 ID {value}' if user.role == 'store_manager' else str(value)


def period_range(period: str, today: date | None = None):
    today = today or now().date()
    if period == 'yesterday':
        return today - timedelta(days=1), today
    if period == 'last_week':
        end = today - timedelta(days=today.weekday())
        return end - timedelta(days=7), end
    if period == 'this_month':
        return today.replace(day=1), today  # completed days only
    if period == 'today':
        return today, today + timedelta(days=1)
    return today - timedelta(days=30), today


def previous_range(start, end, comparison):
    if comparison == 'year_over_year':
        def prior(d):
            try:
                return d.replace(year=d.year - 1)
            except ValueError:
                return d.replace(year=d.year - 1, day=28)
        return prior(start), prior(end)
    return start - (end - start), start


def filters(intent, user, start, end, source='sales'):
    scope, params, _ = permission(user)
    params.update(start=start.isoformat(), end=end.isoformat(), snapshot=(end - timedelta(days=1)).isoformat())
    clauses = [scope]
    for key, field in {'region': 's.region', 'store': 's.store_name', 'city': 's.city', 'category': 'p.category', 'product': 'p.product_name', 'channel': 'o.channel'}.items():
        value = getattr(intent, key)
        if value is not None:
            if source == 'inventory' and key == 'channel':
                raise QueryError('库存没有渠道字段，无法按渠道筛选或分组')
            clauses.append(f'{field} = :filter_{key}')
            params['filter_' + key] = value
    return ' AND '.join(clauses), params


SALES_FROM = ('sales_orders o JOIN stores s ON s.id = o.store_id '
              'JOIN sales_order_items i ON i.order_id = o.id JOIN products p ON p.id = i.product_id')
INVENTORY_FROM = 'inventory_snapshots n JOIN stores s ON s.id = n.store_id JOIN products p ON p.id = n.product_id'


def build_sql(metric: str, intent: Intent, user: User, start: date, end: date):
    meta = METRICS[metric]
    source = meta['source']
    dim = DIMENSIONS[intent.dimension]['field'] if intent.dimension else "'合计'"
    where, params = filters(intent, user, start, end, 'inventory' if source == 'inventory' else 'sales')
    if source == 'inventory':
        if intent.dimension == 'channel':
            raise QueryError('库存指标不支持渠道维度，请选择门店、商品或日期等维度')
        if intent.dimension == 'date':
            dim = DIMENSIONS['date']['inventory_field']
    expression = meta['expression']
    if source == 'sales':
        sql = (f'SELECT {dim} AS dimension, {expression} AS value FROM {SALES_FROM} '
               f'WHERE o.order_time >= :start AND o.order_time < :end AND {where} GROUP BY {dim} LIMIT 1000')
    elif source == 'members':
        sql = (f'WITH member_counts AS (SELECT {dim} AS dimension, o.member_id AS member_id, COUNT(DISTINCT o.id) AS purchase_count '
               f'FROM {SALES_FROM} WHERE o.order_time >= :start AND o.order_time < :end AND o.member_id IS NOT NULL AND {where} '
               f'GROUP BY {dim}, o.member_id) SELECT m.dimension AS dimension, {expression} AS value '
               'FROM member_counts m GROUP BY m.dimension LIMIT 1000')
    elif metric == 'stockout_rate':
        sql = (f'SELECT {dim} AS dimension, {expression} AS value FROM {INVENTORY_FROM} '
               f'WHERE n.snapshot_date >= :start AND n.snapshot_date < :end AND {where} GROUP BY {dim} LIMIT 1000')
    else:
        # The sales CTE has its own independently injected scope.
        active_where, active_params = filters(intent, user, start, end)
        params.update(active_params)
        daily = intent.dimension == 'date'
        active_date = ', DATE(o.order_time) AS sale_date' if daily else ''
        join_date = ' AND a.sale_date = n.snapshot_date' if daily else ''
        snapshot = 'n.snapshot_date >= :start AND n.snapshot_date < :end' if daily else 'n.snapshot_date = :snapshot'
        extras = ', AVG(n.stock_days) AS stock_days' if intent.slow_inventory else ''
        having = f'HAVING {expression} < 60 AND AVG(n.stock_days) > 30' if intent.slow_inventory else ''
        sql = (f'WITH active AS (SELECT DISTINCT o.store_id AS store_id, i.product_id AS product_id{active_date} '
               f'FROM {SALES_FROM} WHERE o.order_time >= :start AND o.order_time < :end AND {active_where}) '
               f'SELECT {dim} AS dimension, {expression} AS value{extras} FROM {INVENTORY_FROM} '
               f'LEFT JOIN active a ON a.store_id = n.store_id AND a.product_id = n.product_id{join_date} '
               f'WHERE {snapshot} AND {where} GROUP BY {dim} {having} LIMIT 1000')
    ordering = 'dimension ASC' if intent.dimension == 'date' else 'value DESC, dimension ASC'
    sql = sql.removesuffix('LIMIT 1000') + f'ORDER BY {ordering} LIMIT 1000'
    validate_sql(sql)
    return sql, params


def coverage(db: Session, user: User):
    # Only scoped inventory coverage is used; no cross-scope timestamps are returned.
    query = select(func.min(InventorySnapshot.snapshot_date), func.max(InventorySnapshot.snapshot_date)).join(Store, Store.id == InventorySnapshot.store_id)
    if user.role == 'store_manager':
        query = query.where(Store.id == user.store_id)
    elif user.role == 'regional_manager':
        query = query.where(Store.region == user.region)
    return db.execute(query).one()


def execute_readonly(db, sql, params):
    # Dedicated physical connection: query_only cannot contaminate the audit session.
    with db.get_bind().connect() as connection:
        raw = connection.connection.driver_connection
        connection.exec_driver_sql('PRAGMA query_only=ON')
        deadline = perf_counter() + 5
        raw.set_progress_handler(lambda: int(perf_counter() > deadline), 10000)
        try:
            return [dict(row) for row in connection.execute(text(sql), params).mappings().fetchmany(1000)]
        finally:
            raw.set_progress_handler(None, 0)
            connection.exec_driver_sql('PRAGMA query_only=OFF')


def run_query(question: str, user: User, db: Session):
    begun = perf_counter()
    statements = []
    status = 'error'
    response = None
    safe_question = redact(question.strip())
    try:
        permission(user)
        if not question.strip():
            raise QueryError('请输入问题')
        intent, mode, warnings = parse_intent(safe_question)
        # Resolve exact known names without adding a free-form SQL path.
        for cls, attribute, field in [(Store, Store.store_name, 'store'), (Product, Product.product_name, 'product')]:
            matches = [name for name in db.scalars(select(attribute)).all() if name in question]
            if len(matches) > 1:
                raise QueryError('MVP每次支持一个明确门店或商品筛选，请拆分问题')
            if matches:
                setattr(intent, field, matches[0])
        if '我店' in question and user.role != 'store_manager':
            raise QueryError('当前账号没有唯一所属门店，请明确门店名称或使用店长账号')
        if intent.slow_inventory and (intent.metrics != ['sell_through'] or intent.dimension != 'product'):
            raise QueryError('库存商品筛选仅支持商品维度的动销率')
        if intent.rank_drop and not intent.comparison:
            raise QueryError('下降排名需要指定同比或环比基期')
        if any(word in question for word in ['客流', '转化率', '为什么']):
            warnings.append('未采集进店客流和转化率，无法判断下降原因；仅提供已成交订单、销售额及客单价对比，不等同于因果归因。')
        if intent.slow_inventory:
            warnings.append('本筛选的库存天数为期末可见门店该商品stock_days的算术平均值；动销率为门店商品组合覆盖率。')
        start, end = period_range(intent.period)
        earliest, latest = coverage(db, user)
        available = earliest is not None and start < end and earliest <= start and latest >= end - timedelta(days=1)
        if not available:
            warnings.append('请求期间的数据覆盖不完整或尚未入库；当前结果仅供查看，不据此判断完整期间的经营表现。')
        rows = {}
        details = []
        source_capped = False

        def collect(metric, period_start, period_end):
            nonlocal source_capped
            sql, params = build_sql(metric, intent, user, period_start, period_end)
            statements.append(sql)
            details.append({'metric': metric, 'sql': sql, 'parameters': params})
            records = execute_readonly(db, sql, params)
            source_capped = source_capped or len(records) == 1000
            return records

        for metric in dict.fromkeys(intent.metrics):
            for item in collect(metric, start, end):
                label = str(item['dimension'])
                row = rows.setdefault(label, {'dimension': label})
                row[metric] = round(item['value'], 2) if item['value'] is not None else None
                if 'stock_days' in item:
                    row['stock_days'] = round(item['stock_days'], 2)
        baseline_available = False
        comparison_range = None
        if intent.comparison:
            before_start, before_end = previous_range(start, end, intent.comparison)
            comparison_range = {'start': before_start.isoformat(), 'end_exclusive': before_end.isoformat()}
            baseline_available = earliest is not None and earliest <= before_start and latest >= before_end - timedelta(days=1)
            if not baseline_available:
                warnings.append('基期数据未覆盖（示例仅含最近90天），同比/环比及下降排名不可计算；缺失值不按0处理。')
            else:
                for metric in dict.fromkeys(intent.metrics):
                    for item in collect(metric, before_start, before_end):
                        label = str(item['dimension'])
                        if intent.dimension == 'date':
                            day = date.fromisoformat(label)
                            if intent.comparison == 'year_over_year':
                                try:
                                    day = day.replace(year=day.year + 1)
                                except ValueError:
                                    day = day.replace(year=day.year + 1, day=28)
                            else:
                                day += start - before_start
                            label = day.isoformat()
                        row = rows.setdefault(label, {'dimension': label})
                        row[metric + '_previous'] = round(item['value'], 2) if item['value'] is not None else None
            for row in rows.values():
                for metric in intent.metrics:
                    current, previous = row.get(metric), row.get(metric + '_previous')
                    row[metric + '_previous'] = previous
                    row[metric + '_change_pct'] = round((current / previous - 1) * 100, 2) if available and current is not None and previous not in (None, 0) else None
        result = list(rows.values())
        metric = intent.metrics[0]
        sort_key = metric + '_change_pct' if intent.rank_drop and baseline_available else metric
        if intent.dimension == 'date':
            result.sort(key=lambda row: row['dimension'])
        else:
            result.sort(key=lambda row: (row.get(sort_key) is None, (row.get(sort_key) or 0) * (1 if intent.rank_drop and baseline_available else -1)))
        total = len(result)
        result = result[:intent.limit]
        if source_capped:
            warnings.append('某个查询达到1000组上限，结果可能被截断；跨指标及变化排名只针对已返回分组，请缩小筛选范围。')
        columns = [{'key': 'dimension', 'label': DIMENSIONS[intent.dimension]['label'] if intent.dimension else '范围', 'unit': ''}]
        for key in dict.fromkeys(intent.metrics):
            columns.append({'key': key, 'label': METRICS[key]['label'], 'unit': METRICS[key]['unit']})
            if intent.comparison:
                columns += [{'key': key + '_previous', 'label': METRICS[key]['label'] + '（基期）', 'unit': METRICS[key]['unit']},
                            {'key': key + '_change_pct', 'label': METRICS[key]['label'] + '变化幅度', 'unit': '%'}]
        if intent.slow_inventory:
            columns.append({'key': 'stock_days', 'label': '平均库存天数', 'unit': '天'})
        if not result:
            answer = '当前权限与筛选范围内没有匹配记录，不能据此推断指标为0。'
        elif not available:
            answer = f'当前返回{len(result)}组已入库数据；请求期间覆盖不完整，无法给出完整期间结论。'
        else:
            first = result[0]
            value = first.get(metric)
            answer = f"当前范围返回{len(result)}组数据；{first['dimension']}的{METRICS[metric]['label']}为{value if value is not None else '暂无数据'}{METRICS[metric]['unit'] if value is not None else ''}。"
            if intent.rank_drop and not baseline_available:
                answer += '缺少基期数据，无法判断哪个分组下降最厉害。'
            elif intent.comparison:
                change = first.get(metric + '_change_pct')
                if change is not None:
                    answer += f'相对基期变化{change:+.2f}%。'
                    if intent.rank_drop and change >= 0:
                        answer += '可比较的分组没有下降。'
        _, _, scope = permission(user)
        response = {'answer_text': answer, 'chart_type': 'line' if intent.dimension == 'date' else ('bar' if intent.dimension and result else 'table'),
                    'chart_data': result, 'columns': columns, 'sql': '\n\n'.join(statements), 'queries': details,
                    'metric_definition': '\n'.join(f"{METRICS[k]['label']}：{METRICS[k]['definition']}" for k in intent.metrics),
                    'data_updated_at': latest.isoformat() if latest else None, 'permission_scope': scope, 'warnings': warnings,
                    'intent': intent.model_dump(), 'parser_mode': mode, 'period': {'start': start.isoformat(), 'end_exclusive': end.isoformat()},
                    'comparison_period': comparison_range, 'total_groups': total, 'truncated': total > intent.limit or source_capped,
                    'latency_ms': round((perf_counter() - begun) * 1000)}
        status = 'success'
        return response
    finally:
        # Never persist secrets or raw identifiers supplied inside a question.
        db.add(AuditLog(user_id=user.id, question=safe_question, generated_sql='\n\n'.join(statements), status=status,
                        latency_ms=round((perf_counter() - begun) * 1000), response_json=json.dumps(response, ensure_ascii=False) if response else None))
        db.commit()
