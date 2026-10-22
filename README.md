# 数店通 · shudiantong-ai-bi

面向店长、区域经理与运营人员的连锁零售经营 AI 问数 MVP。中文问题 → 结构化意图 → 语义层指标 → 参数化只读 SQL → 权限校验 → 图表、结论与口径说明。

**无需 LLM 密钥即可运行。** 本地规则模式支持全部内置示例；依赖首次安装需要网络，安装后问数无需外网。默认连接本地 SQLite。Python 3.11、FastAPI、SQLAlchemy 2、Pydantic 2；React 18、Vite、TypeScript、Ant Design、ECharts。

本次验收：85项pytest通过，前端生产构建通过，浏览器登录/问数/权限/审计检查通过。详细结果和截图见 [验收记录](docs/VALIDATION.md)。

## 快速启动（Windows PowerShell）

在项目根目录执行，要求 Python 3.11 和 Node.js 20.19+ 或 22.12+：

```powershell
Copy-Item .env.example .env
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe scripts/init_db.py
.\.venv\Scripts\python.exe scripts/seed_data.py
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

另开一个终端：

```powershell
cd frontend
npm install
npm run dev
```

打开 [前端工作台](http://localhost:5173)，[API 文档](http://127.0.0.1:8000/docs)，[健康检查](http://127.0.0.1:8000/api/health)。Vite 将 `/api` 代理至 8000 端口。若 5173 被占用，Vite 会提示其他端口；同源代理仍可使用。

如果 Python 由 uv 管理，可用 `uv venv --python 3.11 .venv` 和 `uv pip install --python .venv/Scripts/python.exe -r backend/requirements.txt`。

## macOS / Linux

```bash
cp .env.example .env
python3.11 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
.venv/bin/python scripts/init_db.py
.venv/bin/python scripts/seed_data.py
.venv/bin/python -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
# 第二个终端
cd frontend
npm ci
npm run dev
```

## 演示账号

默认密码均为 `Demo123!`，可在**首次初始化前**设置 `DEMO_PASSWORD`。改变环境变量不会修改已存在用户的密码。

| 账号 | 角色 | 数据范围 |
| --- | --- | --- |
| admin | 管理员 | 全部 6 家门店，可查看审计日志 |
| east_manager | 区域经理 | 华东区：上海、杭州、南京 |
| south_manager | 区域经理 | 华南区：广州、深圳、佛山 |
| store1 / store2 / store3 | 店长 | 上海静安店 / 杭州西湖店 / 南京新街口店 |
| store4 / store5 / store6 | 店长 | 广州天河店 / 深圳南山店 / 佛山南海店 |

令牌存于浏览器 `sessionStorage`，有效期默认 8 小时。每次请求根据数据库用户重新获取角色/范围。JWT 密钥留空时使用进程级随机密钥，服务重启后需重新登录。多进程部署必须设置相同的强随机密钥。

## 示例问题与预期行为

1. **最近30天各品类销售额排行。** 返回四个品类的销售额、柱状图与口径；店长只汇总本店。
2. **上周各门店缺货率是多少？** 管理员看到六店，华东经理看到三店，上海店长只看到上海静安店。
3. **本月动销率低于60%且库存大于30天的商品有哪些？** 返回满足两个条件的商品；演示数据特意包含滞销商品。每月1日尚无本月完整日数据，系统会提示数据缺口。
4. **上周华东区哪个城市客单价掉得最厉害？跟去年同期比呢？** 返回当期城市客单价；由于仅有90天数据，明确提示缺少去年同期，基期与变化列为空，不编造下降排名。
5. **我店昨天销售额为什么下降？主要是客流少了还是转化率低了？** 用店长账号提问；提供昨日与前日销售额、订单数、客单价，明确无法判断客流/转化原因。经理和管理员需指定门店名称。
6. **把华南区TOP10门店的会员复购率和客单价做成对比图。** 按复购率降序，最多10店；演示仅3家华南店，返回3家。百分比与元/单使用不同坐标轴。华东经理/店长查询华南得到空结果。

也可问“最近30天每天销售额趋势”“昨天毛利率”“上海静安店订单数”“广州线下销售额”。规则模式识别 YAML 同义词、已知门店/商品名称、城市、区域、品类和渠道。**并非任意中文都能正确理解**：仅支持昨天、今天、上周、本月、最近30天，以及示例中的固定库存阈值；不支持的明显时间/阈值会被拒绝。请在口径和参数中核对实际解析结果。复杂归因、多轮追问和任意条件表达不在范围内。

## 数据与指标口径

`scripts/seed_data.py` 使用固定随机种子，按 Asia/Shanghai 当前日期生成**截至昨天的最近90个完整自然日**：2区域、6门店、20商品、480会员、约1万订单、每日120条库存快照。所有商品在所有门店均有库存档案；部分商品有意设置为滞销。重复执行保留现有数据库，不追加、不覆盖。没有真实个人信息。

时间计算以请求时上海日期为准；上周指周一至周日，本月默认月初至昨天，最近30天不含今天。日期窗口使用 `[start, end_exclusive)`。数据更新时间为账号可见范围内最新库存数据日期，不伪装成实时同步时间。数据随初始化时间固定；若后续日期变化导致缺口，页面会提示。需要新演示数据时先停后端、备份并重命名 `data/shudiantong.db`（及存在的 `-wal`、`-shm` 文件），再重新初始化。

| 指标 | 核心口径 |
| --- | --- |
| 销售额 | 期间订单明细金额之和；不含退款处理 |
| 订单数 | 去重订单数；跨品类订单在各组分别计数，各组不可直接相加 |
| 客单价 | 匹配明细销售额 / 包含匹配明细的去重订单数 |
| 毛利率 | (销售额 - 明细成本) / 销售额 × 100%；不含租金人工税费 |
| 动销率 | 期间有销售的门店商品组合 / 期末有库存档案的组合；日期维度为当日动销覆盖率 |
| 缺货率 | 期间库存≤0的门店商品日快照 / 全部快照；不是简单平均各店百分比 |
| 会员复购率 | 期间在分组内购买≥2次会员 / 购买≥1次会员；排除非会员订单，非终身复购率 |

商品维度的动销率衡量可见门店中的动销覆盖；“库存大于30天”使用期末各可见门店该商品 `stock_days` 算术平均，不重新推导周转天数。库存指标不支持渠道（源数据没有渠道字段），接口明确拒绝。指标分母为0或基期缺失时返回 `null`，不填0。同比是上一年同一日历日期区间（闰日调整至2月28日）；普通环比为前一个等长区间。百分比指标的变化列也是相对变化率，不是百分点差。

## 架构

```text
React / Ant Design / ECharts
           │ JWT + 中文问题
           ▼
FastAPI → 认证 + 数据库角色/权限
           │
规则解析器 / 可选 OpenAI 兼容接口 → Pydantic Intent 白名单
           │
config/semantics.yml → 指标表达式、维度、权限规则
           │
后端固定 SQL 模板 + 权限交集 + 绑定参数
           │
sqlglot AST 校验（表、字段、函数、SELECT、LIMIT）
           │
SQLite query_only 独立查询连接 + 5秒执行预算
           │
聚合结果 → 图表推荐 + 确定性结论 + 口径/缺口说明
           └→ 独立可写会话记录审计及个人历史
```

LLM 仅接收脱敏问题、语义定义和意图 schema，**不接收查询明细，不生成最终 SQL，也不撰写经营结论**。成功输出再次通过 Pydantic 白名单校验。超时、HTTP 错误、非法 JSON/字段会回退规则解析。规则也无法理解时返回422，并记失败审计。

销售、会员、库存使用不同模板。会员先按分组与会员去重计单，再计算复购率；库存独立聚合，避免订单明细放大分母。多指标/基期分别运行安全 SELECT，结果按维度合并。每条最多1000组，最终最多1000行，默认100行；TOP 按第一指标排序。“新对话”仅清空当前视图，审计历史仍保留；刷新后恢复最近30次。

## 安全边界

- 登录密码采用 PBKDF2-SHA256 + 随机盐；JWT HS256，校验签名与有效期。
- 店长自动加 `s.id = :scope`，区域经理加 `s.region = :scope`；用户指定筛选与权限取交集，缺失权限配置直接拒绝。
- SQL 仅从后端模板和受版本管理的 YAML 生成，HTTP 不接受 SQL。每条只允许 SELECT/SELECT CTE；拒绝多语句、注释、DDL、DML、UNION、通配投影、未知函数和越界 LIMIT。
- sqlglot 进行表/字段解析和白名单校验。问数数据源不包含 users、members、audit_logs；`member_id` 仅在内部聚合使用，不作为输出维度。
- 筛选值参数化；查询在 SQLite `query_only` 连接运行，带5秒进度中断；审核写入使用普通连接。失败时清理只读标志。
- 查询历史按用户隔离；管理员审计接口服务端校验角色。问题里的手机号、邮箱和身份证号在发送 LLM 及保存日志前脱敏。
- 所有已认证、通过请求体格式校验的问数尝试都写成功/失败审计；未认证请求和非法请求体由框架拒绝，不创建业务问数审计。

这是本地演示 MVP：不包含 SSO、生产级会话撤销、登录限流、租户隔离、审计防篡改、业务数据采集或数据库迁移。现有表结构由 `create_all` 创建，修改模型后需自行迁移。示例金额使用 SQLite 浮点数，真实财务业务应改用整数分或定点精度并引入退款/结算模型。

## API

| 方法 | 路径 | 权限 |
| --- | --- | --- |
| POST | `/api/auth/login` | 公开，JSON username/password |
| GET | `/api/auth/me` | 已登录 |
| POST | `/api/chat/query` | 已登录，JSON question |
| GET | `/api/chat/history?limit=30` | 仅当前用户，最多100次 |
| GET | `/api/metadata/metrics` | 已登录，含指标/维度/示例/权限规则 |
| GET | `/api/admin/audit-logs?page=1&page_size=20` | 管理员，分页 |
| GET | `/api/health` | 公开 |

```powershell
$login = Invoke-RestMethod http://127.0.0.1:8000/api/auth/login -Method Post -ContentType 'application/json' -Body '{"username":"store1","password":"Demo123!"}'
$headers = @{ Authorization = "Bearer $($login.access_token)" }
$body = @{ question = '上周各门店缺货率是多少？' } | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:8000/api/chat/query -Method Post -Headers $headers -ContentType 'application/json; charset=utf-8' -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
```

响应包含要求的 `answer_text`、`chart_type`、`chart_data`、`sql`、`metric_definition`、`data_updated_at`、`permission_scope`，以及 `columns`、`warnings`、`queries`（独立SQL和绑定参数）、`intent`、`parser_mode`、`period`、`comparison_period`、`latency_ms`、`total_groups`、`truncated`。`sql` 是多次执行语句的展示文本，空行分隔，不能整体提交数据库执行。

## 环境变量

根目录 `.env` 自动读取；真实环境变量优先。

| 变量 | 默认值 / 说明 |
| --- | --- |
| DATABASE_URL | `sqlite:///./data/shudiantong.db`；相对路径以项目根目录解析，仅支持SQLite |
| JWT_SECRET | 空：每进程生成随机值；持久会话请设≥32字节随机密钥 |
| JWT_EXPIRE_MINUTES | `480` |
| CORS_ORIGINS | `http://localhost:5173,http://127.0.0.1:5173`，逗号分隔 |
| LLM_BASE_URL | `https://api.openai.com/v1`，包含服务API前缀，程序追加 `/chat/completions` |
| LLM_API_KEY | 空：规则模式 |
| LLM_MODEL | 空：规则模式；与密钥同时配置后启用，填服务商实际支持的模型名 |
| LLM_TIMEOUT_SECONDS | `15` |
| DEMO_PASSWORD | `Demo123!`，仅首次生成示例用户时使用 |

兼容接口需支持 Chat Completions、`messages` 和 `response_format: {"type":"json_object"}`；不支持时会回退。参考 [OpenAI Chat Completions 官方接口文档](https://developers.openai.com/api/reference/resources/chat)。API密钥只在后端环境配置，不放入前端。网络接口实际调用需要自行配置服务和凭据。

## 测试与构建

项目根目录执行：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
cd frontend
npm run build
```

Linux 对应 `.venv/bin/python -m pytest -q`。pytest 使用独立临时 SQLite，并生成测试数据，不清空示例库。覆盖登录、三角色权限、越权交集、无配置权限、SQL安全白名单/注入、数据库只读、规则回退、全部示例、销售额不重复、复购分母、历史隔离、审计和脱敏。

前端 `npm run build` 执行 TypeScript 类型检查与 Vite 生产构建。Docker 部署采用 Nginx 代理，因此生产包也无需写死后端地址。

## Docker（可选）

```bash
cp .env.example .env
docker compose up --build
```

Windows 使用 `Copy-Item .env.example .env`。打开 `http://localhost:5173`。SQLite保存在命名卷 `retail-data`，重启不会覆盖数据。此方式固定单后端进程；若配置多副本必须使用固定 JWT_SECRET，并重新评估数据库并发模型。

## 目录

```text
backend/
  app/
    main.py                 FastAPI入口与CORS
    api/routes.py           所有HTTP接口
    core/                   配置、数据库、认证
    models/entities.py      SQLAlchemy业务模型
    schemas/contracts.py    受约束的意图与请求模型
    semantics/catalog.py    YAML加载
    services/parser.py      规则与兼容LLM解析
    services/query_engine.py 权限、模板、查询、结论、审计
    services/sql_safety.py  SQL AST白名单校验
  tests/
  requirements.txt
  Dockerfile
frontend/
  src/{api,components,pages,types}/
  src/App.tsx
  src/styles.css
  package.json
  nginx.conf
  Dockerfile
config/semantics.yml
scripts/init_db.py
scripts/seed_data.py
pytest.ini
docker-compose.yml
.env.example
```
