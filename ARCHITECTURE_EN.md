# AirGuard Architecture: Search/Compare Data Flow

This document provides a detailed explanation of the Search (single city query) and Compare (dual city comparison) features, covering frontend, backend, services, and database layers.

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Search: Single City Query Flow](#search-single-city-query-flow)
3. [Compare: Dual City Comparison Flow](#compare-dual-city-comparison-flow)
4. [Database Recording](#database-recording)
5. [Caching Mechanism](#caching-mechanism)
6. [Function Call Chain Diagrams](#function-call-chain-diagrams)

---

## System Architecture

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

## Search: Single City Query Flow

### User Action
User enters a city name (e.g., "Tokyo") in the search box and clicks the Go button.

### Detailed Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (main.js)                               │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. handleSearchCompare()                                                    │
│     ├── Get input value: city1 = "Tokyo"                                     │
│     ├── Check: only city1, no city2                                          │
│     ├── Build URL: /api/aqi?city=Tokyo&user_country=Malaysia                 │
│     │              (userCountry set by getLocationFromIP() on page load)     │
│     └── Call fetchAPI(url)                                                   │
│                                                                              │
│  2. fetchAPI(url)                                                            │
│     ├── fetch(url) → HTTP GET request                                        │
│     └── Returns { success: true, data: {...} }                               │
│                                                                              │
│  3. renderDetailedCards([data], "aqi-card-container")                        │
│     ├── Create card HTML (using escapeHtml for XSS prevention)               │
│     └── Insert into DOM                                                      │
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
│      ├── 1. Get parameters                                                   │
│      │   city = request.args.get("city")        # "Tokyo"                    │
│      │   source = request.args.get("source")    # "search" (default)         │
│      │                                                                       │
│      ├── 2. Get request context                                              │
│      │   ctx = get_request_context()                                         │
│      │   → {                                                                 │
│      │       "ip": "203.1.2.3",                                              │
│      │       "ua": "Mozilla/5.0...",                                         │
│      │       "user_country": "Malaysia",                                     │
│      │       "device_type": "desktop"                                        │
│      │     }                                                                 │
│      │                                                                       │
│      ├── 3. Fetch and record                                                 │
│      │   result, err = fetch_and_record(city, "single", source, ctx)         │
│      │                                                                       │
│      └── 4. Return response                                                  │
│          return success(result)  # JSON response                             │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ fetch_and_record()
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         fetch_and_record() Internal Flow                      │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  def fetch_and_record(city, query_type, source, ctx):                        │
│      │                                                                       │
│      ├── 1. Validate city name length (max 100 chars)                        │
│      │                                                                       │
│      ├── 2. Normalize city name                                              │
│      │   normalized = normalize_city(city)                                   │
│      │   "tokyo" → "Tokyo"                                                   │
│      │                                                                       │
│      ├── 3. Get AQI data (with caching)                                      │
│      │   result = get_aqi_cached(normalized)                                 │
│      │                    │                                                  │
│      │                    ▼                                                  │
│      │         ┌─────────────────────────────────────────┐                   │
│      │         │  @cache.memoize(timeout=180)           │                   │
│      │         │  def get_aqi_cached(city):             │                   │
│      │         │      Check cache first (3 min TTL)     │                   │
│      │         │      If miss → get_aqi(city, CONFIG)   │                   │
│      │         └─────────────────────────────────────────┘                   │
│      │                                                                       │
│      ├── 4. Record query to database                                         │
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
│      └── 5. Return result                                                    │
│          return result, None                                                 │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Compare: Dual City Comparison Flow

### User Action
User enters two cities (e.g., "Tokyo" and "Seoul") and clicks the Go button.

### Detailed Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (main.js)                               │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. handleSearchCompare()                                                    │
│     ├── Get input values: city1 = "Tokyo", city2 = "Seoul"                   │
│     ├── Check: city2 exists, so use compare API                              │
│     ├── Build URL:                                                           │
│     │   /api/compare?city1=Tokyo&city2=Seoul&user_country=Malaysia           │
│     └── Call fetchAPI(url)                                                   │
│                                                                              │
│  2. Process response                                                         │
│     ├── data.city1 = Tokyo's AQI data                                        │
│     ├── data.city2 = Seoul's AQI data                                        │
│     └── cards = [data.city1, data.city2]                                     │
│                                                                              │
│  3. renderDetailedCards(cards, "aqi-card-container")                         │
│     ├── Compare AQI values, add crown badge to better city                   │
│     │   if (aqi1 <= aqi2) { cities[0]._crown = true }                        │
│     ├── Create two cards                                                     │
│     └── Add "comparison-mode" CSS class                                      │
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
│      ├── 1. Get parameters                                                   │
│      │   city1 = "Tokyo"                                                     │
│      │   city2 = "Seoul"                                                     │
│      │                                                                       │
│      ├── 2. Get request context                                              │
│      │   ctx = get_request_context()                                         │
│      │                                                                       │
│      ├── 3. Loop through each city                                           │
│      │   for key, city in [("city1", city1), ("city2", city2)]:              │
│      │       result, err = fetch_and_record(city, "compare", "search", ctx)  │
│      │       data[key] = result if result else {"error": err}                │
│      │                                                                       │
│      │   ⚠️ Note: Each city will:                                            │
│      │      - Query AQI API independently (or get from cache)                │
│      │      - Record to database independently                               │
│      │                                                                       │
│      └── 4. Return response                                                  │
│          return success({                                                    │
│              "city1": { Tokyo AQI data },                                    │
│              "city2": { Seoul AQI data }                                     │
│          })                                                                  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Database Recording

### Table Schema

```sql
CREATE TABLE public.query_records (
    id BIGSERIAL PRIMARY KEY,
    city TEXT NOT NULL,              -- Queried city name (normalized)
    aqi INTEGER,                     -- AQI value
    level TEXT,                      -- Level: Good, Moderate, Unhealthy...
    dominentpol TEXT,                -- Dominant pollutant: pm25, pm10, o3...
    query_type TEXT DEFAULT 'single',-- Query type: 'single' or 'compare'
    source TEXT DEFAULT 'search',    -- Source: 'auto' (geolocation) or 'search'
    user_country TEXT,               -- User's country (from IP geolocation)
    device_type TEXT,                -- Device type: 'mobile' or 'desktop'
    ip_address TEXT,                 -- User's IP address
    user_agent TEXT,                 -- User's browser UA
    created_at TIMESTAMP             -- Query timestamp
);
```

### Data Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                     query_record_service.py                                   │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  def record_query(...):                                                      │
│      │                                                                       │
│      ├── 1. Get database connection                                          │
│      │   db = get_db()  # → database/connection.py                           │
│      │                                                                       │
│      ├── 2. Build data object                                                │
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
│      └── 3. Insert into database                                             │
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
│  Database records:                                                           │
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

## Caching Mechanism

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

Flow:
1. Request /api/aqi?city=Tokyo
2. get_aqi_cached("Tokyo") is called
3. Check cache:
   - HIT  → Return cached data immediately (fast)
   - MISS → Call get_aqi() to query external API → Store in cache → Return
```

---

## Function Call Chain Diagrams

### Search: Complete Call Chain

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
                                          │         └── "Tokyo" (normalized)
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

### Compare: Complete Call Chain

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
                                          │         ├── get_aqi_cached("Tokyo") → May hit cache
                                          │         └── record_query(..., query_type="compare")
                                          │
                                          └── fetch_and_record("Seoul", "compare", ...)
                                                    │
                                                    ├── get_aqi_cached("Seoul") → May hit cache
                                                    └── record_query(..., query_type="compare")

                                Returns:
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
                    ├── Compare AQI: aqi1=45 vs aqi2=68
                    ├── Tokyo is better → _crown = true
                    └── Render two cards (side by side)
```

---

## File Responsibilities Summary

| File | Responsibility |
|------|----------------|
| `static/main.js` | Frontend interactions, IP geolocation, API calls, card rendering, XSS protection |
| `app.py` | Flask routes, request handling, cache configuration, response building |
| `services/aqi_service.py` | External AQI API calls, data parsing, AQI classification |
| `services/query_record_service.py` | Database writes, query history retrieval |
| `services/utils.py` | City name normalization, device type parsing, request context extraction |
| `services/response_service.py` | Unified JSON response format |
| `database/connection.py` | Supabase connection management |
| `database/schema.sql` | Database table schema definition |
| `config/settings.json` | AQI level configuration, popular cities list |

---

## user_country Field Explanation

The `user_country` field records the **user's location country** (obtained via IP geolocation), NOT the country where the queried city is located.

```
User in Malaysia → Queries Tokyo → user_country = "Malaysia"
User in Japan    → Queries Tokyo → user_country = "Japan"
```

This field is used for analytics: analyzing which countries' users are querying which cities.
