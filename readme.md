# AirGuard - Real-time Air Quality Monitoring

A responsive web application to monitor and compare air quality index (AQI) across cities worldwide.

> 📖 [中文版 README](README_CN.md) | [Architecture Documentation (EN)](ARCHITECTURE_EN.md) | [架构文档 (中文)](ARCHITECTURE.md)


## Table of Contents

- [Features](#features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Database Schema](#database-schema)
- [Caching Strategy](#caching-strategy)
- [Key Implementation Details](#key-implementation-details)
- [Troubleshooting](#troubleshooting)
- [References](#references)

---

## Features
- **Real-time AQI Monitoring**: Fetch current air quality data for any city worldwide
- **Frontend IP Geolocation** - Accurate user location via ipapi.co (called from browser, not server)
- **City Comparison**: Compare AQI levels between multiple cities side-by-side
- **Popular Cities Dashboard**: Pre-configured popular cities with concurrent data fetching
- **Query Logging**: Persistent database storage of all user queries with metadata
- **Responsive Design**: Mobile-first design with CSS variables for adaptive scaling
- **Modern UI**: Clean, minimal aesthetic with semantic color coding
- **Performance Optimized**: 10-minute caching on popular cities endpoint, concurrent requests
- **Daily AQI Email Subscription**: Elderly-friendly form + scheduled email delivery pipeline
- **Query Analytics** - Comprehensive logging: `user_country`, `device_type`, `query_type`, `source`, `dominentpol`
- **Multi-tier Caching** - Per-city (3 min) + endpoint (10 min) + background warmup on startup
- **Security** - XSS protection via `escapeHtml()`, input validation (100 char limit)

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | Flask 3.0.3, Python 3.8+ |
| Database | Supabase (PostgreSQL) |
| Caching | Flask-Caching (SimpleCache, in-memory) |
| Frontend | Vanilla ES6+ JavaScript, CSS3, Jinja2 |
| AQI API | World Air Quality Index API (waqi.info) |
| IP Geolocation | ipapi.co (frontend call) |

---

## Project Structure

```
air_guard/
├── app.py                      # Flask application entry point
├── requirements.txt            # Python dependencies
├── readme.md                   # This file
├── README_CN.md                # Chinese README
├── ARCHITECTURE.md             # Architecture documentation (Chinese)
├── ARCHITECTURE_EN.md          # Architecture documentation (English)
│
├── config/
│   └── settings.json           # AQI levels & popular cities configuration
│
├── database/
│   ├── __init__.py             # Package marker
│   ├── connection.py           # Supabase client factory
│   └── schema.sql              # Database table schema
│
├── services/
│   ├── aqi_service.py          # AQI data fetching & classification
│   ├── query_record_service.py # Database logging operations
│   ├── response_service.py     # JSON response formatting
│   └── utils.py                # Utility functions & constants
│
├── static/
│   ├── main.js                 # Frontend JavaScript
│   └── style.css               # CSS styles
│
├── templates/
│   ├── base.html               # Base template
│   ├── index.html              # Home page
│   └── about.html              # About page
│
└── .env                        # Environment variables (not committed)
```

---

## Quick Start

### 1. Clone the Repository

```bash
git clone git@github.com:iriszhang1121/AirGuard.git
cd AirGuard
```

### 2. Create Conda Environment

```bash
conda create -n airguard python=3.11 -y
conda activate airguard
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Supabase Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key

# World Air Quality Index API
AQI_API_URL=https://api.waqi.info/feed
AQI_API_TOKEN=your_waqi_token

# Database Table Name
DB_TABLE_NAME=query_records

# Flask Settings (optional)
FLASK_ENV=development
PORT=8001
```

## 📦 Module Responsibilities

### Core Application
- **`app.py`** 
  - Flask app initialization with caching
  - Route handlers: `/`, `/about`, `/api/aqi`, `/api/compare`, `/api/popular`
  - Request/response handling and client info extraction

### Database Layer (`database/`)
- **`connection.py`** 
  - Supabase client factory with error message constants
  - Manages authentication via environment variables
  - Extracted constants: `SUPABASE_URL_ERROR`, `SUPABASE_KEY_ERROR`
  - **Usage**: `from database.connection import get_db`

- **`schema.sql`** 
  - SQL schema for manual database setup via Supabase UI
  - Includes RLS policies and role permissions
  - **Note**: Database tables must be created in Supabase before running the app

### Business Logic Layer (`services/`)

#### Data Acquisition
- **`aqi_service.py`** 
  - Unified AQI data fetching and querying module
  - Low-level API communication + business logic + database recording
  - Concurrent fetching for multiple cities
  - **Key functions**:
    - `_fetch_aqi_raw(city)` → API response
    - `get_aqi(city, config)` → dict (with classification)
    - `fetch_and_record_aqi(city, config, ip, ua)` → (result, error)
    - `fetch_aqi_for_multiple_cities(cities, config, max_workers)` → list

#### Geolocation, Database & Utilities
- **`query_record_service.py`** 
  - Persists queries to Supabase database
  - Graceful degradation if table doesn't exist
  - **Key functions**:
    - `record_query(city, aqi, level, ip, ua)` → bool
    - `get_query_history(city, limit)` → list

- **`response_service.py`** 
  - Standard Flask JSON response formatting
  - Consistent error and success message structure
  - **Key functions**:
    - `success(data)` → Flask JSON response
    - `error(message, status_code)` → Flask JSON error response

- **`utils.py`** 
  - Configuration constants & helper functions
  - IP-based geolocation with fallback
  - **Constants**: `DEFAULT_CITY`, `IP_API_TIMEOUT`, `PLACEHOLDER_AQI`
  - **Key functions**:
    - `normalize_city(city)` → str (title case, trimmed)
    - `classify_aqi(aqi, config)` → dict (returns level info)
    - `get_client_info(request)` → tuple (IP, user agent)
    - `get_user_city()` → str (IP-based location with fallback to DEFAULT_CITY)

### Frontend Assets

- **`static/main.js`** 
  - Vanilla JavaScript with ES6+ features
  - Functions: API calls, card rendering, search, comparison
  - No business logic—all backend-dependent
  - Event listeners for user interactions

- **`static/style.css`** 
  - CSS variables for responsive typography
  - Breakpoints: 480px (mobile), 768px (tablet), 1024px (desktop)
  - Design system: white nav/footer, light gray body, colored accent cards
  - Modern minimal aesthetic with subtle shadows

### Templates

- **`templates/base.html`**
  - Master Jinja2 template
  - Navigation bar, footer, content blocks
  - Prevents HTML duplication across pages

- **`templates/index.html`** 
  - Home page with hero banner
  - Search interface, AQI cards, comparison section
  - Popular cities carousel

- **`templates/about.html`**
  - About/information page
  - Credits, team info, FAQ

### Configuration

- **`config/settings.json`**
  - Popular cities list (8 Malaysian cities)
  - AQI level definitions (Healthy, Moderate, Unhealthy)
  - Color coding and advice text per AQI level
  - Query settings (max_workers for concurrent requests)


## 🧭 Product Roadmaps

- **EPIC 4.0 (Could Have): Daily AQI Email Subscription**
  See implementation guide: `EPIC_4_DAILY_SUBSCRIPTION_PLAN.md`

## 🚀 Getting Started

### Prerequisites
- Python 3.8+ with conda or virtualenv
- Supabase account (free tier available)
- External API keys (see Configuration below)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd air_guard
   ```

2. **Create Python environment** (option A: using conda.yml)
   ```bash
   conda env create -f conda.yml
   conda activate air_guard
   ```

   Or **(option B: manual conda setup)**
   ```bash
   conda create -n air_guard python=3.10
   conda activate air_guard
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Setup environment variables**
   ```bash
   # Create .env file (never commit to git)
   cat > .env << EOF
   # Supabase Configuration
   SUPABASE_URL=https://xxxxx.supabase.co
   SUPABASE_KEY=eyxxxxx...
   
   # AQI API (World Air Quality Index)
   AQI_API_URL=https://api.waqi.info
   AQI_API_TOKEN=your_token_here
   
   # Geolocation API
   IP_API_URL=https://ipapi.co/json/
   
   # Database Configuration (optional - uses defaults if not set)
   DB_TABLE_NAME=query_records
   DB_SCHEMA=public
   DB_SSLMODE=require
   DB_USER=postgres
   DB_NAME=postgres
   DB_PORT=5432
   
   # Email Subscription Settings (EPIC 4)
   ENABLE_EMAIL_SCHEDULER=false
   SUBSCRIPTION_TABLE_NAME=email_subscriptions
   NOTIFICATION_LOGS_TABLE_NAME=notification_logs

   # SMTP Email Settings (required for sending daily alerts)
   SMTP_HOST=smtp.example.com
   SMTP_PORT=587
   SMTP_USER=your_smtp_username
   SMTP_PASSWORD=your_smtp_password
   SMTP_USE_TLS=true
   EMAIL_FROM=no-reply@airguard.example.com

   # Flask Settings
   FLASK_ENV=development
   PORT=8001
   EOF
   ```

5. **Database setup** (optional—enables query logging)
  
   Tables must already be created in Supabase. Use `database/schema.sql` as reference:
   - Copy `database/schema.sql` into Supabase SQL Editor
   - Execute the queries to create tables and indexes

6. **Run the application**
   ```bash
   python app.py
   ```
   
   Application will be available at `http://localhost:8001`

## ⚙️ Configuration

### Environment Variables
| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `SUPABASE_URL` | Supabase project URL | — | https://xxxxx.supabase.co |
| `SUPABASE_KEY` | Supabase API key | — | eyJhbGc... |
| `AQI_API_URL` | World Air Quality Index API endpoint | https://api.waqi.info | https://api.waqi.info |
| `AQI_API_TOKEN` | WAQI API token | — | demo |
| `IP_API_URL` | IP geolocation API endpoint | https://ipapi.co/json/ | https://ipapi.co/json/ |
| `DB_TABLE_NAME` | Database table name | query_records | query_records |
| `DB_SCHEMA` | PostgreSQL schema name | public | public |
| `DB_SSLMODE` | PostgreSQL SSL mode | require | require |
| `DB_USER` | PostgreSQL user | postgres | postgres |
| `DB_NAME` | PostgreSQL database name | postgres | postgres |
| `DB_PORT` | PostgreSQL port | 5432 | 5432 |
| `FLASK_ENV` | Flask environment | development | development / production |
| `PORT` | Port to run Flask server on | 8001 | 8001 |

### settings.json

Located at `config/settings.json`:

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
      "advice": "Air quality is satisfactory. Safe to enjoy outdoor activities."
    },
    {
      "min": 51,
      "max": 100,
      "level": "Moderate",
      "color": "#eab308",
      "text_color": "#000",
      "advice": "Air quality is moderate. Sensitive groups should limit outdoor activity."
    },
    {
      "min": 101,
      "max": 150,
      "level": "Unhealthy for Sensitive Groups",
      "color": "#f97316",
      "text_color": "#fff",
      "advice": "Sensitive groups may experience health effects."
    },
    {
      "min": 151,
      "max": 200,
      "level": "Unhealthy",
      "color": "#ef4444",
      "text_color": "#fff",
      "advice": "General public may experience health effects. Avoid outdoor activities."
    },
    {
      "min": 201,
      "max": 99999,
      "level": "Hazardous",
      "color": "#7c3aed",
      "text_color": "#fff",
      "advice": "Health alert! Entire population at risk. Remain indoors."
    }
  ]
}
```

You can modify:
- **popular_cities** - Cities shown in the dashboard
- **aqi_levels** - AQI classification ranges, colors, and health advice

---

## API Reference

### GET `/api/aqi`

Fetch AQI for a single city.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `city` | Yes | City name to query |
| `source` | No | `auto` (geolocation) or `search` (manual). Default: `search` |
| `user_country` | No | User's country from IP (for analytics) |

**Example:**
```
GET /api/aqi?city=Tokyo&user_country=Malaysia
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "city": "Tokyo",
    "aqi": 45,
    "level": "Good",
    "color": "#10b981",
    "text_color": "#fff",
    "advice": "Air quality is satisfactory...",
    "dominentpol": "pm25",
    "time_s": "2026-03-12 15:30:00"
  }
}
```

### GET `/api/compare`

Compare AQI between two cities.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `city1` | At least one | First city |
| `city2` | At least one | Second city |
| `user_country` | No | User's country (for analytics) |

**Example:**
```
GET /api/compare?city1=Tokyo&city2=Seoul&user_country=Malaysia
```

### GET `/api/popular`

Fetch AQI for all popular cities (cached 10 minutes).

**Example:**
```
GET /api/popular
```

---

## Database Schema

The `query_records` table stores all user queries for analytics:

```sql
CREATE TABLE query_records (
    id BIGSERIAL PRIMARY KEY,
    city TEXT NOT NULL,              -- City queried
    aqi INTEGER,                     -- AQI value
    level TEXT,                      -- Good, Moderate, Unhealthy, etc.
    dominentpol TEXT,                -- Main pollutant (pm25, o3, etc.)
    query_type TEXT DEFAULT 'single',-- 'single' or 'compare'
    source TEXT DEFAULT 'search',    -- 'auto' or 'search'
    user_country TEXT,               -- User's country (from IP)
    device_type TEXT,                -- 'mobile' or 'desktop'
    ip_address TEXT,                 -- User IP
    user_agent TEXT,                 -- Browser UA
    created_at TIMESTAMP             -- Query time
);
```

> **Important:** `user_country` is the **user's location** from IP geolocation, NOT the country of the queried city.

### Sample Analytics Queries

```sql
-- Most queried cities
SELECT city, COUNT(*) as count FROM query_records 
GROUP BY city ORDER BY count DESC LIMIT 10;

-- User distribution by country
SELECT user_country, COUNT(*) FROM query_records 
WHERE user_country IS NOT NULL GROUP BY user_country;

-- Device type breakdown
SELECT device_type, COUNT(*) FROM query_records GROUP BY device_type;

-- Query type ratio (single vs compare)
SELECT query_type, COUNT(*) FROM query_records GROUP BY query_type;
```

---

## Caching Strategy

| Cache Type | TTL | Scope | Purpose |
|------------|-----|-------|---------|
| `@cache.memoize` | 3 min | Per city | Individual AQI queries |
| `@cache.cached` | 10 min | Endpoint | `/api/popular` results |
| `warmup_cache_background()` | Startup | 9 cities | Pre-load on app start |

---

## Key Implementation Details

### Frontend IP Geolocation

IP geolocation runs **in the browser** to get the user's actual location (not server location):

```javascript
const getLocationFromIP = async () => {
    const data = await fetchWithTimeout("https://ipapi.co/json/", 2000);
    userCountry = data?.country_name || null;
    return data?.city || null;
};
```

### XSS Protection

All dynamic content is escaped before DOM insertion:

```javascript
const escapeHtml = (str) => {
    if (!str) return '';
    return String(str).replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
};
```

### Cache Warmup

On startup, popular cities are pre-loaded in a background thread:

```python
def warmup_cache_background():
    def do_warmup():
        cities = [DEFAULT_CITY] + CONFIG["api"]["popular_cities"]
        with ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(lambda c: get_aqi_cached(c), cities)
    
    threading.Thread(target=do_warmup, daemon=True).start()
```

---

## Troubleshooting

### "No air quality data available"
- City name may not be recognized by the API
- Try alternative names (e.g., "George Town" not "Georgetown")

### Database connection errors
- Check `SUPABASE_URL` and `SUPABASE_KEY` in `.env`
- Verify table exists using the verification command above

### IP geolocation not working
- ipapi.co may be blocked by browser or network
- App falls back to default city (Kuala Lumpur)

---

## References

- [World Air Quality Index API](https://aqicn.org/api/)
- [Supabase Documentation](https://supabase.com/docs)
- [Flask Documentation](https://flask.palletsprojects.com/)

---

**Last Updated:** March 2026
