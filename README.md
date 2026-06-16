<img width="2559" height="1187" alt="image" src="https://github.com/user-attachments/assets/13452eeb-ac85-4937-89b5-3033205143b2" />
<img width="2223" height="780" alt="image" src="https://github.com/user-attachments/assets/812fdd3d-310b-4784-9973-c0c6ddb2f119" />
<img width="2181" height="620" alt="image" src="https://github.com/user-attachments/assets/aad47dd0-8049-494e-97f4-9c994190bb7e" />
<img width="2193" height="591" alt="image" src="https://github.com/user-attachments/assets/1a7d68dc-b16c-402b-a143-b0ed6ca5b409" />




# 🛢️ 霍尔木兹海峡油轮监测数据看板

实时监测霍尔木兹海峡石油航运态势的多维度数据看板，集成卫星 AIS 通行量、港口装船、国际油价、卫星火点和海上安全事件，通过多源交叉验证评估区域供应风险。

## 看板截图

- **总览看板** — 风险仪表盘、6 项核心指标、趋势图表、数据源状态
- **海峡通行量详情** — IEA 权威估算 vs IMF PortWatch AIS 卫星检测 双曲线对比
- **风险评估** — 风险趋势、UKMTO 安全事件时间线、6 维度分解评估

## 架构

```
frontend (React + TypeScript + Vite)     backend (FastAPI + SQLAlchemy)
┌──────────────────────────────┐         ┌──────────────────────────────┐
│  Dashboard (Ant Design)      │  HTTP   │  API (/api/dashboard)        │
│  ├─ OverviewPage             │◄───────►│  API (/api/data)             │
│  ├─ StraitDetailPage         │         │  API (/api/risk)             │
│  └─ RiskPage                 │         │  API (/api/admin)            │
│                              │         │                              │
│  ECharts + Leaflet 地图      │         │  Scheduler (每小时)           │
│  实时数据 5 分钟轮询          │         │  ├─ PortWatchCollector       │
└──────────────────────────────┘         │  ├─ FIRMSCollector           │
                                         │  ├─ OilPriceCollector        │
                                         │  ├─ UKMTOCollector           │
                                         │  ├─ ShippingIndexCollector   │
                                         │  └─ RiskEngine               │
                                         │                              │
                                         │  SQLite (data.db)            │
                                         └──────────────────────────────┘
```

## 数据源

| 指标 | 数据源 | 频率 | 说明 |
|------|--------|------|------|
| 🛳️ 海峡通行量 | IMF PortWatch (卫星AIS) + IEA/EIA 基准 | 每小时 | 双源对比：卫星实时检测 + 权威估算 |
| ⛽ 港口装船量 | IMF PortWatch / IEA | 每小时 | 波斯湾 10 大油港装载比 |
| 🛢️ 布伦特/WTI | 新浪财经 实时行情 | 每 6 小时 | ICE/NYMEX 期货实时价 |
| 🔥 卫星火点 | NASA FIRMS (VIIRS) | 每 6 小时 | 波斯湾 12 个关键设施火点监测 |
| ⚠️ 安全事件 | UKMTO (手动录入) | 按需 | 霍尔木兹/阿曼湾/波斯湾事件 |
| 📊 BDTI 运价 | 模型估算 | 每日 | 基于油价+通行量相关性推算 |

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 20+
- npm 10+

### 1. 后端

```bash
cd backend
pip install -r requirements.txt

# 初始化数据
python seed.py

# 启动 (http://localhost:8000)
uvicorn app.main:app --reload
```

API 文档：http://localhost:8000/docs

### 2. 前端

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
```

或一键启动：`start.bat`

### 3. 配置 NASA FIRMS（火点数据）

1. 打开 https://firms.modaps.eosdis.nasa.gov/api/map_key/
2. 输入邮箱获取免费 API Key
3. 编辑 `backend/.env`：`FIRMS_API_KEY=你的key`

### 4. 配置代理（UKMTO 安全事件，可选）

编辑 `backend/.env`：
```
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
```

## 项目结构

```
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI 入口
│   │   ├── config.py               # 配置（env + 默认值）
│   │   ├── database.py             # SQLAlchemy + SQLite
│   │   ├── scheduler.py            # APScheduler 定时任务
│   │   ├── models/models.py        # 7 个数据模型
│   │   ├── collectors/             # 数据采集器
│   │   │   ├── portwatch_collector.py   # IMF 卫星AIS
│   │   │   ├── firms_collector.py       # NASA 火点
│   │   │   ├── oil_price_collector.py   # 新浪油价
│   │   │   ├── ukmto_collector.py       # UKMTO 事件
│   │   │   └── shipping_index_collector.py # BDTI 估算
│   │   ├── services/
│   │   │   ├── risk_engine.py      # 6 维度风险评分
│   │   │   └── data_validator.py   # 数据新鲜度+异常检测
│   │   └── api/
│   │       ├── dashboard.py        # 看板汇总 API
│   │       ├── data.py             # 数据查询 API
│   │       ├── risk.py             # 风险评估 API
│   │       └── admin.py            # 管理+手动录入 API
│   ├── tests/                      # pytest 测试 (39 个)
│   ├── seed.py                     # 种子数据
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── OverviewPage.tsx    # 总览看板
│   │   │   ├── StraitDetailPage.tsx # 海峡详情（双数据源）
│   │   │   └── RiskPage.tsx        # 风险评估+UKMTO时间线
│   │   ├── components/
│   │   │   ├── charts/             # ECharts + Leaflet 图表
│   │   │   └── widgets/            # RiskGauge, MetricCard, SourceStatusBar
│   │   ├── services/api.ts         # Axios API 层
│   │   └── types/index.ts          # TypeScript 类型
│   ├── vite.config.ts              # Vite + 代理配置
│   └── package.json
├── start.bat                       # 一键启动脚本
└── README.md
```

## 风险引擎

6 维度加权评分，综合判定 4 级风险：

| 维度 | 权重 | 数据源 |
|------|------|--------|
| 海峡通行量 | 25% | IEA + PortWatch AIS |
| 港口装船量 | 20% | IEA 港口基线 |
| 油价 | 15% | 布伦特/WTI |
| 运价指数 | 15% | BDTI 估算 |
| 卫星火点 | 10% | NASA FIRMS |
| 安全事件 | 15% | UKMTO |

风险等级：情绪冲击(Lv.1) → 中度实质影响(Lv.2) → 严重供应冲击(Lv.3) → 极端冲击(Lv.4)

## 技术栈

**后端**: FastAPI + SQLAlchemy + SQLite + APScheduler + httpx + xlrd

**前端**: React 18 + TypeScript + Vite + Ant Design 5 + ECharts + Leaflet

**测试**: pytest + pytest-cov（核心模块 >80% 覆盖）

## License

MIT
