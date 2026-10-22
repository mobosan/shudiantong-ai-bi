import re
import sqlglot
from sqlglot import exp
from sqlglot.optimizer.qualify import qualify
from app.services.parser import QueryError

# No users, members, audit_logs, member identifiers in output, or SQLite system tables.
SCHEMA = {
    'stores': {'id': 'INT', 'store_name': 'TEXT', 'region': 'TEXT', 'city': 'TEXT', 'open_date': 'DATE'},
    'products': {'id': 'INT', 'product_name': 'TEXT', 'category': 'TEXT', 'price': 'REAL', 'cost': 'REAL'},
    'sales_orders': {'id': 'INT', 'store_id': 'INT', 'member_id': 'INT', 'channel': 'TEXT', 'order_time': 'DATETIME', 'total_amount': 'REAL'},
    'sales_order_items': {'id': 'INT', 'order_id': 'INT', 'product_id': 'INT', 'quantity': 'INT', 'amount': 'REAL', 'cost': 'REAL'},
    'inventory_snapshots': {'id': 'INT', 'store_id': 'INT', 'product_id': 'INT', 'snapshot_date': 'DATE', 'stock_qty': 'INT', 'stock_days': 'REAL'},
}
ALLOWED_FUNCTIONS = {'SUM', 'COUNT', 'AVG', 'MIN', 'MAX', 'NULLIF', 'COALESCE', 'DATE', 'CAST', 'CASE', 'IF', 'ROUND', 'AND', 'OR'}


def validate_sql(sql: str):
    if re.search(r';|--|/\*|\*/|\x00', sql) or not re.match(r'^\s*(SELECT|WITH)\b', sql, re.I):
        raise QueryError('SQL必须为无注释的单条只读查询')
    try:
        statements = sqlglot.parse(sql, read='sqlite')
        if len(statements) != 1 or not isinstance(statements[0], exp.Select):
            raise ValueError('select only')
        tree = statements[0]
        ctes = {c.alias_or_name for c in tree.find_all(exp.CTE)}
        for table in tree.find_all(exp.Table):
            if table.name not in SCHEMA and table.name not in ctes or table.db or table.catalog:
                raise ValueError('table not allowed')
        for node in tree.walk():
            if isinstance(node, (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Command, exp.Union, exp.Into)):
                raise ValueError('operation not allowed')
            if isinstance(node, exp.Func):
                name = node.name.upper() if isinstance(node, exp.Anonymous) else node.sql_name()
                if name not in ALLOWED_FUNCTIONS:
                    raise ValueError('function not allowed: ' + name)
        for star in tree.find_all(exp.Star):
            if not isinstance(star.parent, exp.Count):
                raise ValueError('wildcard projection not allowed')
        qualify(tree.copy(), dialect='sqlite', schema=SCHEMA, validate_qualify_columns=True)
        limit = tree.args.get('limit')
        if not limit or not isinstance(limit.expression, exp.Literal) or not 1 <= int(limit.expression.this) <= 1000:
            raise ValueError('bounded literal LIMIT required')
    except Exception as exc:
        raise QueryError('SQL未通过表名、字段、函数或行数白名单校验') from exc
