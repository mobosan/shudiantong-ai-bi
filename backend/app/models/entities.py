from datetime import date, datetime
from sqlalchemy import String, Float, ForeignKey, Date, DateTime, Text, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.core.config import now


class Store(Base):
    __tablename__ = 'stores'
    id: Mapped[int] = mapped_column(primary_key=True)
    store_name: Mapped[str] = mapped_column(String(80), unique=True)
    region: Mapped[str] = mapped_column(String(30), index=True)
    city: Mapped[str] = mapped_column(String(30))
    open_date: Mapped[date] = mapped_column(Date)


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(40), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(30))
    store_id: Mapped[int | None] = mapped_column(ForeignKey('stores.id'))
    region: Mapped[str | None] = mapped_column(String(30))


class Product(Base):
    __tablename__ = 'products'
    id: Mapped[int] = mapped_column(primary_key=True)
    product_name: Mapped[str] = mapped_column(String(80))
    category: Mapped[str] = mapped_column(String(30))
    price: Mapped[float] = mapped_column(Float)
    cost: Mapped[float] = mapped_column(Float)


class Member(Base):
    __tablename__ = 'members'
    id: Mapped[int] = mapped_column(primary_key=True)
    member_no: Mapped[str] = mapped_column(String(40), unique=True)
    store_id: Mapped[int] = mapped_column(ForeignKey('stores.id'))
    register_date: Mapped[date] = mapped_column(Date)


class SalesOrder(Base):
    __tablename__ = 'sales_orders'
    id: Mapped[int] = mapped_column(primary_key=True)
    order_no: Mapped[str] = mapped_column(String(40), unique=True)
    store_id: Mapped[int] = mapped_column(ForeignKey('stores.id'))
    member_id: Mapped[int | None] = mapped_column(ForeignKey('members.id'))
    channel: Mapped[str] = mapped_column(String(30))
    order_time: Mapped[datetime] = mapped_column(DateTime)
    total_amount: Mapped[float] = mapped_column(Float)
    __table_args__ = (Index('ix_orders_store_time', 'store_id', 'order_time'),)


class SalesOrderItem(Base):
    __tablename__ = 'sales_order_items'
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey('sales_orders.id'), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'))
    quantity: Mapped[int]
    amount: Mapped[float] = mapped_column(Float)
    cost: Mapped[float] = mapped_column(Float)


class InventorySnapshot(Base):
    __tablename__ = 'inventory_snapshots'
    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey('stores.id'))
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'))
    snapshot_date: Mapped[date] = mapped_column(Date)
    stock_qty: Mapped[int]
    stock_days: Mapped[float] = mapped_column(Float)
    __table_args__ = (UniqueConstraint('store_id', 'product_id', 'snapshot_date'),)


class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    question: Mapped[str] = mapped_column(Text)
    generated_sql: Mapped[str] = mapped_column(Text, default='')
    status: Mapped[str] = mapped_column(String(30))
    latency_ms: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    response_json: Mapped[str | None] = mapped_column(Text)
