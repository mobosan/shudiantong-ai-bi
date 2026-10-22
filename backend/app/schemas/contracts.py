from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

Metric = Literal['sales_amount', 'order_count', 'avg_order_value', 'gross_margin', 'sell_through', 'stockout_rate', 'repurchase_rate']
Dimension = Literal['date', 'store', 'region', 'city', 'category', 'product', 'channel']


class Intent(BaseModel):
    model_config = ConfigDict(extra='forbid')
    metrics: list[Metric] = Field(min_length=1, max_length=7)
    dimension: Dimension | None = None
    period: Literal['yesterday', 'last_week', 'this_month', 'last_30_days', 'today'] = 'last_30_days'
    region: Literal['华东区', '华南区'] | None = None
    store: str | None = Field(default=None, max_length=80)
    city: str | None = Field(default=None, max_length=30)
    category: str | None = Field(default=None, max_length=30)
    product: str | None = Field(default=None, max_length=80)
    channel: Literal['线下', '小程序', '外卖'] | None = None
    comparison: Literal['previous', 'year_over_year'] | None = None
    rank_drop: bool = False
    slow_inventory: bool = False
    limit: int = Field(default=100, ge=1, le=1000)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=40)
    password: str = Field(min_length=1, max_length=128)


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class UserView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    role: str
    store_id: int | None
    region: str | None
