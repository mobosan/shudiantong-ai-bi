"""Idempotent demo seed; refuses to overwrite existing business data."""
import sys
import random
from pathlib import Path
from datetime import timedelta, datetime, time
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from sqlalchemy import select, func
from app.core.config import now, settings
from app.core.database import Base, engine, SessionLocal
from app.core.security import hash_password
from app.models.entities import Store, User, Product, Member, SalesOrder, SalesOrderItem, InventorySnapshot


def seed(db, today=None):
    if db.scalar(select(func.count(Store.id))):
        return {'skipped': True, 'reason': 'Existing data preserved'}
    rng = random.Random(20261021)
    today = today or now().date()
    stores = [('上海静安店', '华东区', '上海'), ('杭州西湖店', '华东区', '杭州'), ('南京新街口店', '华东区', '南京'),
              ('广州天河店', '华南区', '广州'), ('深圳南山店', '华南区', '深圳'), ('佛山南海店', '华南区', '佛山')]
    for sid, (name, region, city) in enumerate(stores, 1):
        db.add(Store(id=sid, store_name=name, region=region, city=city, open_date=today - timedelta(days=730)))
    db.flush()
    password = hash_password(settings.demo_password)
    db.add_all([User(username='admin', password_hash=password, role='admin'),
                User(username='east_manager', password_hash=password, role='regional_manager', region='华东区'),
                User(username='south_manager', password_hash=password, role='regional_manager', region='华南区')])
    for sid in range(1, 7):
        db.add(User(username=f'store{sid}', password_hash=password, role='store_manager', store_id=sid))
    names = ['矿泉水', '乌龙茶', '鲜牛奶', '美式咖啡', '橙汁', '薯片', '坚果', '黑巧克力', '苏打饼干', '果干',
             '抽纸', '洗衣液', '洗手液', '牙刷', '保鲜袋', '苹果', '香蕉', '鸡蛋', '生菜', '番茄']
    products = []
    for pid, name in enumerate(names, 1):
        price = round(rng.uniform(5, 40), 2)
        product = Product(id=pid, product_name=name, category=['饮料', '零食', '日用品', '生鲜'][(pid-1)//5], price=price, cost=round(price * rng.uniform(.45, .8), 2))
        products.append(product)
        db.add(product)
    for sid in range(1, 7):
        for m in range(1, 81):
            mid = (sid - 1) * 80 + m
            db.add(Member(id=mid, member_no=f'M{mid:06}', store_id=sid, register_date=today - timedelta(days=180)))
    db.flush()
    orders, items, snapshots = [], [], []
    oid = iid = 0
    for offset in range(90, 0, -1):
        day = today - timedelta(days=offset)
        for sid in range(1, 7):
            # Products 19/20 intentionally slow-moving at most stores.
            available_products = list(range(1, 19)) + ([19, 20] if sid == 1 else [])
            count = rng.randint(12, 22) + (5 if day.weekday() >= 5 else 0)
            if sid == 1 and offset == 1:
                count = 8
            for n in range(count):
                oid += 1
                total = 0
                for pid in rng.sample(available_products, rng.randint(1, 4)):
                    iid += 1
                    p = products[pid-1]
                    quantity = rng.randint(1, 3)
                    amount = round(p.price * quantity, 2)
                    total += amount
                    items.append({'id': iid, 'order_id': oid, 'product_id': pid, 'quantity': quantity, 'amount': amount, 'cost': round(p.cost * quantity, 2)})
                orders.append({'id': oid, 'order_no': f'SO{day:%Y%m%d}{sid}{n:03}', 'store_id': sid,
                               'member_id': (sid - 1) * 80 + rng.randint(1, 80) if rng.random() < .7 else None,
                               'channel': rng.choices(['线下', '小程序', '外卖'], [7, 2, 1])[0],
                               'order_time': datetime.combine(day, time(rng.randint(8, 21), rng.randint(0, 59))), 'total_amount': round(total, 2)})
            for pid in range(1, 21):
                stock = 0 if rng.random() < .09 else rng.randint(8, 140)
                snapshots.append({'store_id': sid, 'product_id': pid, 'snapshot_date': day, 'stock_qty': stock,
                                  'stock_days': round(rng.uniform(40, 65) if pid >= 19 else stock / rng.uniform(3, 12), 1)})
    db.bulk_insert_mappings(SalesOrder, orders)
    db.bulk_insert_mappings(SalesOrderItem, items)
    db.bulk_insert_mappings(InventorySnapshot, snapshots)
    db.commit()
    return {'stores': 6, 'products': 20, 'members': 480, 'orders': len(orders), 'items': len(items), 'inventory_snapshots': len(snapshots), 'from': str(today-timedelta(days=90)), 'through': str(today-timedelta(days=1))}


if __name__ == '__main__':
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        print(seed(db))
