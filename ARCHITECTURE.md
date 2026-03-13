# AirGuard 架构文档：Search/Compare 功能数据流

本文档详细说明 Search（单城市查询）和 Compare（双城市对比）功能的完整数据流，涵盖前端、后端、服务层和数据库。

---

## 目录

1. [整体架构](#整体架构)
2. [Search 单城市查询流程](#search-单城市查询流程)
3. [Compare 双城市对比流程](#compare-双城市对比流程)
4. [数据库记录](#数据库记录)
5. [缓存机制](#缓存机制)
6. [函数调用链路图](#函数调用链路图)

---

## 整体架构

```
┌─────────────────┐     HTTP      ┌─────────────────┐
│     Frontend    │ ─────────────▶│     Backend     │
│   (main.js)     │◀───────────── │    (app.py)     │
└─────────────────┘     JSON      └────────┬────────┘
        │                                   │
        │ ipapi.co                          │
        ▼                                   ▼
┌─────────────────┐              ┌─────────────────────────┐
│   IP Location   │              │      Services           │
│   (external)    │              │  ├── aqi_service.py     │
└─────────────────┘              │  ├── query_record_...   │
                                 │  ├── response_service   │
                                 │  └── utils.py           │
                                 └────────────┬────────────┘
                                              │
                        ┌─────────────────────┴────────────────────┐
                        ▼                                          ▼
               ┌─────────────────┐                      ┌─────────────────┐
               │   External API  │                      │     Supabase    │
               │   (WAQI API)    │                      │   (PostgreSQL)  │
               └─────────────────┘                      └─────────────────┘
```

---

## Search 单城市查询流程

### 用户操作
用户在搜索框输入城市名（如 "Tokyo"），点击 Go 按钮。

### 详细流程

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (main.js)                               │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. handleSearchCompare()                                                    │
│     ├── 获取输入框值: city1 = "Tokyo"                                         │
│     ├── 检查: 只有 city1，没有 city2                                          │
│     ├── 构建 URL: /api/aqi?city=Tokyo&user_country=Malaysia                  │
│     │              (userCountry 在页面加载时由 getLocationFromIP() 设置)      │
│     └── 调用 fetchAPI(url)                                                   │
│                                                                              │
│  2. fetchAPI(url)                                                            │
│     ├── fetch(url) → HTTP GET 请求                                           │
│     └── 返回 { success: true, data: {...} }                                  │
│                                                                              │
│  3. renderDetailedCards([data], "aqi-card-container")                        │
│     ├── 创建卡片 HTML (使用 escapeHtml 防止 XSS)                              │
│     └── 插入 DOM                                                             │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP GET /api/aqi?city=Tokyo&user_country=Malaysia
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND (app.py)                                 │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  @app.route("/api/aqi")                                                      │
│  def aqi():                                                                  │
│      │                                                                       │
│      ├── 1. 获取参数                                                         │
│      │   city = request.args.get("city")        # "Tokyo"                    │
│      │   source = request.args.get("source")    # "search" (default)         │
│      │                                                                       │
│      ├── 2. 获取请求上下文                                                    │
│      │   ctx = get_request_context()                                         │
│      │   → {                                                                 │
│      │       "ip": "203.1.2.3",                                              │
│      │       "ua": "Mozilla/5.0...",                                         │
│      │       "user_country": "Malaysia",                                     │
│      │       "device_type": "desktop"                                        │
│      │     }                                                                 │
│      │                                                                       │
│      ├── 3. 查询并记录                                                        │
│      │   result, err = fetch_and_record(city, "single", source, ctx)         │
│      │                                                                       │
│      └── 4. 返回响应                                                          │
│          return success(result)  # JSON 响应                                 │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ fetch_and_record()
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         fetch_and_record() 内部流程                           │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  def fetch_and_record(city, query_type, source, ctx):                        │
│      │                                                                       │
│      ├── 1. 验证城市名长度 (max 100 字符)                                     │
│      │                                                                       │
│      ├── 2. 标准化城市名                                                      │
│      │   normalized = normalize_city(city)                                   │
│      │   "tokyo" → "Tokyo"                                                   │
│      │                                                                       │
│      ├── 3. 获取 AQI 数据 (带缓存)                                            │
│      │   result = get_aqi_cached(normalized)                                 │
│      │                    │                                                  │
│      │                    ▼                                                  │
│      │         ┌─────────────────────────────────────────┐                   │
│      │         │  @cache.memoize(timeout=180)           │                   │
│      │         │  def get_aqi_cached(city):             │                   │
│      │         │      先检查缓存 (3分钟有效)             │                   │
│      │         │      若无缓存 → get_aqi(city, CONFIG)  │                   │
│      │         └─────────────────────────────────────────┘                   │
│      │                                                                       │
│      ├── 4. 记录查询到数据库                                                  │
│      │   record_query(                                                       │
│      │       city="Tokyo",                                                   │
│      │       aqi=45,                                                         │
│      │       level="Good",                                                   │
│      │       dominentpol="pm25",                                             │
│      │       query_type="single",                                            │
│      │       source="search",                                                │
│      │       user_country="Malaysia",                                        │
│      │       device_type="desktop",                                          │
│      │       ip_address="203.1.2.3",                                         │
│      │       user_agent="Mozilla/5.0..."                                     │
│      │   )                                                                   │
│      │                                                                       │
│      └── 5. 返回结果                                                          │
│          return result, None                                                 │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Compare 双城市对比流程

### 用户操作
用户输入两个城市（如 "Tokyo" 和 "Seoul"），点击 Go 按钮。

### 详细流程

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (main.js)                               │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. handleSearchCompare()                                                    │
│     ├── 获取输入框值: city1 = "Tokyo", city2 = "Seoul"                        │
│     ├── 检查: 有 city2，所以用 compare API                                    │
│     ├── 构建 URL:                                                            │
│     │   /api/compare?city1=Tokyo&city2=Seoul&user_country=Malaysia           │
│     └── 调用 fetchAPI(url)                                                   │
│                                                                              │
│  2. 处理响应                                                                  │
│     ├── data.city1 = Tokyo 的 AQI 数据                                       │
│     ├── data.city2 = Seoul 的 AQI 数据                                       │
│     └── cards = [data.city1, data.city2]                                     │
│                                                                              │
│  3. renderDetailedCards(cards, "aqi-card-container")                         │
│     ├── 比较 AQI 值，给较好的城市添加皇冠标记                                  │
│     │   if (aqi1 <= aqi2) { cities[0]._crown = true }                        │
│     ├── 创建两张卡片                                                         │
│     └── 添加 "comparison-mode" CSS 类                                        │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP GET /api/compare?city1=Tokyo&city2=Seoul&user_country=Malaysia
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND (app.py)                                 │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  @app.route("/api/compare")                                                  │
│  def compare():                                                              │
│      │                                                                       │
│      ├── 1. 获取参数                                                         │
│      │   city1 = "Tokyo"                                                     │
│      │   city2 = "Seoul"                                                     │
│      │                                                                       │
│      ├── 2. 获取请求上下文                                                    │
│      │   ctx = get_request_context()                                         │
│      │                                                                       │
│      ├── 3. 循环处理每个城市                                                  │
│      │   for key, city in [("city1", city1), ("city2", city2)]:              │
│      │       result, err = fetch_and_record(city, "compare", "search", ctx)  │
│      │       data[key] = result if result else {"error": err}                │
│      │                                                                       │
│      │   ⚠️ 注意: 每个城市都会:                                               │
│      │      - 独立查询 AQI API (或从缓存获取)                                 │
│      │      - 独立记录到数据库                                                │
│      │                                                                       │
│      └── 4. 返回响应                                                          │
│          return success({                                                    │
│              "city1": { Tokyo AQI data },                                    │
│              "city2": { Seoul AQI data }                                     │
│          })                                                                  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 数据库记录

### 表结构

```sql
CREATE TABLE public.query_records (
    id BIGSERIAL PRIMARY KEY,
    city TEXT NOT NULL,              -- 查询的城市名 (标准化后)
    aqi INTEGER,                     -- AQI 数值
    level TEXT,                      -- 等级: Good, Moderate, Unhealthy...
    dominentpol TEXT,                -- 主要污染物: pm25, pm10, o3...
    query_type TEXT DEFAULT 'single',-- 查询类型: 'single' 或 'compare'
    source TEXT DEFAULT 'search',    -- 来源: 'auto' (自动定位) 或 'search' (搜索)
    user_country TEXT,               -- 用户所在国家 (从 IP 获取)
    device_type TEXT,                -- 设备类型: 'mobile' 或 'desktop'
    ip_address TEXT,                 -- 用户 IP 地址
    user_agent TEXT,                 -- 用户浏览器 UA
    created_at TIMESTAMP             -- 查询时间
);
```

### 数据流程

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                     query_record_service.py                                   │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  def record_query(...):                                                      │
│      │                                                                       │
│      ├── 1. 获取数据库连接                                                    │
│      │   db = get_db()  # → database/connection.py                           │
│      │                                                                       │
│      ├── 2. 构建数据对象                                                      │
│      │   data = {                                                            │
│      │       "city": "Tokyo",                                                │
│      │       "aqi": 45,                                                      │
│      │       "level": "Good",                                                │
│      │       "dominentpol": "pm25",                                          │
│      │       "query_type": "single",                                         │
│      │       "source": "search",                                             │
│      │       "user_country": "Malaysia",                                     │
│      │       "device_type": "desktop",                                       │
│      │       "ip_address": "203.1.2.3",                                      │
│      │       "user_agent": "Mozilla/5.0...",                                 │
│      │       "created_at": "2026-03-12T15:30:00"                             │
│      │   }                                                                   │
│      │                                                                       │
│      └── 3. 插入数据库                                                        │
│          db.table("query_records").insert(data).execute()                    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP POST (Supabase REST API)
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                        Supabase (PostgreSQL)                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  INSERT INTO query_records (city, aqi, level, ...) VALUES ('Tokyo', 45, ...) │
│                                                                              │
│  数据库中的记录:                                                              │
│  ┌────┬────────┬─────┬───────┬────────────┬────────┬──────┬──────────────┐   │
│  │ id │  city  │ aqi │ level │ query_type │ source │ ...  │  created_at  │   │
│  ├────┼────────┼─────┼───────┼────────────┼────────┼──────┼──────────────┤   │
│  │ 1  │ Tokyo  │ 45  │ Good  │  single    │ search │ ...  │ 2026-03-12   │   │
│  │ 2  │ Seoul  │ 68  │ Mod.  │  compare   │ search │ ...  │ 2026-03-12   │   │
│  │ 3  │ Tokyo  │ 45  │ Good  │  compare   │ search │ ...  │ 2026-03-12   │   │
│  └────┴────────┴─────┴───────┴────────────┴────────┴──────┴──────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 缓存机制

```
                    ┌─────────────────────────────────────┐
                    │         Flask-Caching               │
                    │      (SimpleCache, in-memory)       │
                    └─────────────────────────────────────┘
                                     │
     ┌───────────────────────────────┼───────────────────────────────┐
     │                               │                               │
     ▼                               ▼                               ▼
┌─────────────┐            ┌─────────────────┐            ┌─────────────────┐
│  memoize    │            │     cached      │            │  Cache Warmup   │
│  per-city   │            │   (popular)     │            │   (startup)     │
├─────────────┤            ├─────────────────┤            ├─────────────────┤
│ timeout=180 │            │  timeout=600    │            │ Background      │
│ (3 minutes) │            │  (10 minutes)   │            │ thread          │
│             │            │                 │            │                 │
│ Key: city   │            │ Key: endpoint   │            │ Pre-loads:      │
│ "Tokyo"→AQI │            │ "/api/popular"  │            │ DEFAULT_CITY +  │
│ "Seoul"→AQI │            │ → [results]     │            │ popular_cities  │
└─────────────┘            └─────────────────┘            └─────────────────┘

流程:
1. 请求 /api/aqi?city=Tokyo
2. get_aqi_cached("Tokyo") 被调用
3. 检查缓存:
   - HIT  → 直接返回缓存数据 (快速)
   - MISS → 调用 get_aqi() 查询外部 API → 存入缓存 → 返回
```

---

## 函数调用链路图

### Search 完整调用链

```
Frontend                    Backend                     Services                    External
─────────────────────────────────────────────────────────────────────────────────────────────────

handleSearchCompare()
        │
        │ fetch("/api/aqi?city=Tokyo&user_country=Malaysia")
        │
        └──────────────────▶ aqi()
                                │
                                ├── get_request_context()
                                │         │
                                │         ├── get_client_info(request) ─────▶ utils.py
                                │         └── parse_device_type(ua) ────────▶ utils.py
                                │
                                └── fetch_and_record()
                                          │
                                          ├── normalize_city("Tokyo") ──────▶ utils.py
                                          │         └── "Tokyo" (标准化)
                                          │
                                          ├── get_aqi_cached("Tokyo")
                                          │         │
                                          │         └── [CACHE MISS] ──▶ get_aqi() ──▶ aqi_service.py
                                          │                                   │
                                          │                                   ├── _fetch_aqi_raw()
                                          │                                   │       │
                                          │                                   │       └──────────────▶ WAQI API
                                          │                                   │                          │
                                          │                                   │       ◀──────────────────┘
                                          │                                   │       { aqi: 45, dominentpol: "pm25", time_s: "..." }
                                          │                                   │
                                          │                                   └── classify_aqi(45, config) ──▶ utils.py
                                          │                                             │
                                          │                                             └── { level: "Good", color: "#00e400", advice: [...] }
                                          │
                                          └── record_query(...) ────────────▶ query_record_service.py
                                                      │
                                                      └── get_db() ─────────▶ database/connection.py
                                                                │
                                                                └──────────────────────────────▶ Supabase
                                                                                                   │
                                                                                                   ▼
                                                                                             INSERT INTO
                                                                                            query_records
```

### Compare 完整调用链

```
handleSearchCompare()
        │
        │ fetch("/api/compare?city1=Tokyo&city2=Seoul&user_country=Malaysia")
        │
        └──────────────────▶ compare()
                                │
                                ├── get_request_context()
                                │
                                └── for each city:
                                          │
                                          ├── fetch_and_record("Tokyo", "compare", ...)
                                          │         │
                                          │         ├── get_aqi_cached("Tokyo") → 可能命中缓存
                                          │         └── record_query(..., query_type="compare")
                                          │
                                          └── fetch_and_record("Seoul", "compare", ...)
                                                    │
                                                    ├── get_aqi_cached("Seoul") → 可能命中缓存
                                                    └── record_query(..., query_type="compare")

                                返回:
                                {
                                    "status": "success",
                                    "data": {
                                        "city1": { Tokyo AQI },
                                        "city2": { Seoul AQI }
                                    }
                                }
        │
        ◀──────────────────────────────────────────────────────────────────────
        │
        └── renderDetailedCards([city1, city2], "aqi-card-container")
                    │
                    ├── 比较 AQI: aqi1=45 vs aqi2=68
                    ├── Tokyo 更好 → _crown = true
                    └── 渲染两张卡片 (并排显示)
```

---

## 关键文件职责总结

| 文件 | 职责 |
|------|------|
| `static/main.js` | 前端交互、IP 定位、API 调用、卡片渲染、XSS 防护 |
| `app.py` | Flask 路由、请求处理、缓存配置、响应构建 |
| `services/aqi_service.py` | 外部 AQI API 调用、数据解析、AQI 分类 |
| `services/query_record_service.py` | 数据库写入、查询历史 |
| `services/utils.py` | 城市名标准化、设备类型解析、请求上下文提取 |
| `services/response_service.py` | 统一 JSON 响应格式 |
| `database/connection.py` | Supabase 连接管理 |
| `database/schema.sql` | 数据库表结构定义 |
| `config/settings.json` | AQI 等级配置、热门城市列表 |

---

## user_country 字段说明

`user_country` 记录的是 **用户所在国家**（通过 IP 定位获取），而不是查询城市所在的国家。

```
用户在马来西亚 → 查询 Tokyo → user_country = "Malaysia"
用户在日本     → 查询 Tokyo → user_country = "Japan"
```

这个字段用于分析：哪些国家的用户在查询哪些城市。
