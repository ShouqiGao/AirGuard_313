# AirGuard - 实时空气质量监测

一个响应式 Web 应用，用于监测和比较全球城市的空气质量指数 (AQI)。

> 📖 [English README](readme.md) | [架构文档 (中文)](ARCHITECTURE.md) | [Architecture (EN)](ARCHITECTURE_EN.md)

---

## 目录

- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [API 接口](#api-接口)
- [数据库结构](#数据库结构)
- [缓存策略](#缓存策略)
- [关键实现细节](#关键实现细节)
- [常见问题](#常见问题)
- [参考资料](#参考资料)

---

## 功能特性

- **实时 AQI 监测** - 获取全球任意城市的当前空气质量数据
- **前端 IP 定位** - 通过 ipapi.co 在浏览器端获取用户真实位置（非服务器位置）
- **城市对比** - 并排比较两个城市的 AQI，空气更好的城市显示皇冠徽章
- **热门城市仪表盘** - 预配置的马来西亚城市，并发获取数据
- **查询分析** - 完整日志记录：`user_country`、`device_type`、`query_type`、`source`、`dominentpol`
- **多层缓存** - 单城市缓存 (3分钟) + 端点缓存 (10分钟) + 启动时后台预热
- **安全防护** - XSS 防护 (`escapeHtml()`)，输入验证 (100字符限制)

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Flask 3.0.3, Python 3.8+ |
| 数据库 | Supabase (PostgreSQL) |
| 缓存 | Flask-Caching (SimpleCache, 内存缓存) |
| 前端 | 原生 ES6+ JavaScript, CSS3, Jinja2 |
| AQI API | World Air Quality Index API (waqi.info) |
| IP 定位 | ipapi.co (前端调用) |

---

## 项目结构

```
air_guard/
├── app.py                      # Flask 应用入口
├── requirements.txt            # Python 依赖
├── readme.md                   # 英文 README
├── README_CN.md                # 中文 README（本文件）
├── ARCHITECTURE.md             # 架构文档（中文）
├── ARCHITECTURE_EN.md          # 架构文档（英文）
│
├── config/
│   └── settings.json           # AQI 等级 & 热门城市配置
│
├── database/
│   ├── __init__.py             # 包标识
│   ├── connection.py           # Supabase 客户端工厂
│   └── schema.sql              # 数据库表结构
│
├── services/
│   ├── aqi_service.py          # AQI 数据获取 & 分类
│   ├── query_record_service.py # 数据库日志操作
│   ├── response_service.py     # JSON 响应格式化
│   └── utils.py                # 工具函数 & 常量
│
├── static/
│   ├── main.js                 # 前端 JavaScript
│   └── style.css               # CSS 样式
│
├── templates/
│   ├── base.html               # 基础模板
│   ├── index.html              # 首页
│   └── about.html              # 关于页面
│
└── .env                        # 环境变量（不提交到 git）
```

---

## 快速开始

### 1. 克隆仓库

```bash
git clone git@github.com:iriszhang1121/AirGuard.git
cd AirGuard
```

### 2. 创建 Conda 环境

```bash
conda create -n airguard python=3.11 -y
conda activate airguard
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

在项目根目录创建 `.env` 文件：

```env
# Supabase 数据库
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key

# World Air Quality Index API
AQI_API_URL=https://api.waqi.info/feed
AQI_API_TOKEN=your_waqi_token

# 数据库表名
DB_TABLE_NAME=query_records

# Flask 设置（可选）
FLASK_ENV=development
PORT=8001
```

### 5. 设置数据库（可选）

数据库日志功能是可选的，应用在没有数据库的情况下也能正常工作。

如需启用查询日志，在 Supabase 中创建表：
1. 进入 Supabase Dashboard → SQL Editor
2. 复制并执行 `database/schema.sql`

**验证数据库连接：**
```bash
python -c "from database.connection import get_db; print(get_db().table('query_records').select('*').limit(1).execute())"
```

### 6. 运行应用

```bash
python app.py
```

在浏览器中打开 http://localhost:8001

---

## 配置说明

### settings.json

位于 `config/settings.json`：

```json
{
  "api": {
    "popular_cities": [
      "Kuala Lumpur",
      "George Town",
      "Kuching",
      "Johor Bahru",
      "Malacca",
      "Seremban",
      "Kota Kinabalu",
      "Petaling Jaya"
    ]
  },
  "aqi_levels": [
    {
      "min": 0,
      "max": 50,
      "level": "Good",
      "color": "#10b981",
      "text_color": "#fff",
      "advice": "空气质量良好，适合户外活动。"
    },
    {
      "min": 51,
      "max": 100,
      "level": "Moderate",
      "color": "#eab308",
      "text_color": "#000",
      "advice": "空气质量中等，敏感人群应限制户外活动。"
    },
    {
      "min": 101,
      "max": 150,
      "level": "Unhealthy for Sensitive Groups",
      "color": "#f97316",
      "text_color": "#fff",
      "advice": "敏感人群可能出现健康影响。"
    },
    {
      "min": 151,
      "max": 200,
      "level": "Unhealthy",
      "color": "#ef4444",
      "text_color": "#fff",
      "advice": "公众可能出现健康影响，避免户外活动。"
    },
    {
      "min": 201,
      "max": 99999,
      "level": "Hazardous",
      "color": "#7c3aed",
      "text_color": "#fff",
      "advice": "健康警报！所有人都有风险，请待在室内。"
    }
  ]
}
```

可修改配置：
- **popular_cities** - 仪表盘显示的城市
- **aqi_levels** - AQI 分类范围、颜色、健康建议

---

## API 接口

### GET `/api/aqi`

获取单个城市的 AQI。

| 参数 | 必填 | 说明 |
|------|------|------|
| `city` | 是 | 城市名 |
| `source` | 否 | `auto`（定位）或 `search`（搜索），默认 `search` |
| `user_country` | 否 | 用户所在国家（用于分析） |

**示例：**
```
GET /api/aqi?city=Tokyo&user_country=Malaysia
```

**响应：**
```json
{
  "status": "success",
  "data": {
    "city": "Tokyo",
    "aqi": 45,
    "level": "Good",
    "color": "#10b981",
    "text_color": "#fff",
    "advice": "空气质量良好...",
    "dominentpol": "pm25",
    "time_s": "2026-03-12 15:30:00"
  }
}
```

### GET `/api/compare`

比较两个城市的 AQI。

| 参数 | 必填 | 说明 |
|------|------|------|
| `city1` | 至少一个 | 第一个城市 |
| `city2` | 至少一个 | 第二个城市 |
| `user_country` | 否 | 用户所在国家 |

**示例：**
```
GET /api/compare?city1=Tokyo&city2=Seoul&user_country=Malaysia
```

### GET `/api/popular`

获取所有热门城市的 AQI（缓存 10 分钟）。

**示例：**
```
GET /api/popular
```

---

## 数据库结构

`query_records` 表存储所有用户查询，用于分析：

```sql
CREATE TABLE query_records (
    id BIGSERIAL PRIMARY KEY,
    city TEXT NOT NULL,              -- 查询的城市
    aqi INTEGER,                     -- AQI 值
    level TEXT,                      -- Good, Moderate, Unhealthy 等
    dominentpol TEXT,                -- 主要污染物 (pm25, o3 等)
    query_type TEXT DEFAULT 'single',-- 'single' 或 'compare'
    source TEXT DEFAULT 'search',    -- 'auto' 或 'search'
    user_country TEXT,               -- 用户所在国家（从 IP 获取）
    device_type TEXT,                -- 'mobile' 或 'desktop'
    ip_address TEXT,                 -- 用户 IP
    user_agent TEXT,                 -- 浏览器 UA
    created_at TIMESTAMP             -- 查询时间
);
```

> **重要：** `user_country` 是 **用户的位置**（从 IP 定位获取），不是查询城市所在的国家。

### 分析查询示例

```sql
-- 最常查询的城市
SELECT city, COUNT(*) as count FROM query_records 
GROUP BY city ORDER BY count DESC LIMIT 10;

-- 用户来源国家分布
SELECT user_country, COUNT(*) FROM query_records 
WHERE user_country IS NOT NULL GROUP BY user_country;

-- 设备类型分布
SELECT device_type, COUNT(*) FROM query_records GROUP BY device_type;

-- 查询类型比例（单城市 vs 对比）
SELECT query_type, COUNT(*) FROM query_records GROUP BY query_type;
```

---

## 缓存策略

| 缓存类型 | TTL | 范围 | 用途 |
|----------|-----|------|------|
| `@cache.memoize` | 3 分钟 | 每个城市 | 单独 AQI 查询 |
| `@cache.cached` | 10 分钟 | 端点 | `/api/popular` 结果 |
| `warmup_cache_background()` | 启动时 | 9 个城市 | 应用启动时预加载 |

---

## 关键实现细节

### 前端 IP 定位

IP 定位在 **浏览器端** 执行，获取用户真实位置（而非服务器位置）：

```javascript
const getLocationFromIP = async () => {
    const data = await fetchWithTimeout("https://ipapi.co/json/", 2000);
    userCountry = data?.country_name || null;
    return data?.city || null;
};
```

### XSS 防护

所有动态内容在插入 DOM 前都会转义：

```javascript
const escapeHtml = (str) => {
    if (!str) return '';
    return String(str).replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
};
```

### 缓存预热

启动时，在后台线程中预加载热门城市：

```python
def warmup_cache_background():
    def do_warmup():
        cities = [DEFAULT_CITY] + CONFIG["api"]["popular_cities"]
        with ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(lambda c: get_aqi_cached(c), cities)
    
    threading.Thread(target=do_warmup, daemon=True).start()
```

---

## 常见问题

### "No air quality data available"
- 城市名可能无法被 API 识别
- 尝试其他拼写（如 "George Town" 而非 "Georgetown"）

### 数据库连接错误
- 检查 `.env` 中的 `SUPABASE_URL` 和 `SUPABASE_KEY`
- 使用上述验证命令确认表是否存在

### IP 定位不工作
- ipapi.co 可能被浏览器或网络阻止
- 应用会回退到默认城市（Kuala Lumpur）

---

## 参考资料

- [World Air Quality Index API](https://aqicn.org/api/)
- [Supabase 文档](https://supabase.com/docs)
- [Flask 文档](https://flask.palletsprojects.com/)

---

**最后更新：** 2026年3月
