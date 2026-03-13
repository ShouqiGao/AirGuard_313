"""
AirGuard - Real-time Air Quality Monitoring Platform
Main Flask application with caching and concurrent queries
"""
import os
import json
from flask import Flask, jsonify, render_template, request
from flask_caching import Cache
from services.response_service import success, error

from services.aqi_service import fetch_aqi_for_multiple_cities, get_aqi
from services.subscription_service import validate_subscription_payload, subscription_exists, create_subscription
from services.scheduler_service import start_scheduler
from services.query_record_service import record_query
from services.utils import get_client_info, normalize_city, parse_device_type

# Load .env only for local development (not in production)
if os.getenv("FLASK_ENV") != "production":
    from dotenv import load_dotenv
    load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configure caching (popular cities cached for 10 minutes)
cache = Cache(app, config={
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 600
})

# Load configuration
with open("config/settings.json") as f:
    CONFIG = json.load(f)


# Cached AQI lookup (3 minute cache per city)
@cache.memoize(timeout=180)
def get_aqi_cached(city):
    """Get AQI with caching."""
    return get_aqi(city, CONFIG)


# ===== ROUTES =====
@app.route("/")
def index():
    """Homepage with search and popular cities"""
    return render_template("index.html", subscription_cities=CONFIG["api"]["popular_cities"])


@app.route("/about")
def about():
    """About page with mission, features, and data sources"""
    return render_template("about.html")


# ===== HELPER FUNCTIONS =====
def get_request_context():
    """
    Extract common request context for analytics.
    Returns: dict with ip, ua, user_country, device_type
    """
    ip, ua = get_client_info(request)
    user_country = request.args.get("user_country")
    
    # Truncate user_country if too long
    if user_country and len(user_country) > 100:
        user_country = user_country[:100]
    
    return {
        "ip": ip,
        "ua": ua,
        "user_country": user_country,
        "device_type": parse_device_type(ua)
    }


def fetch_and_record(city, query_type, source, ctx):
    """
    Fetch AQI for a city and record the query.
    
    Args:
        city: Raw city name from request
        query_type: 'single' or 'compare'
        source: 'auto' or 'search'
        ctx: Request context from get_request_context()
        
    Returns:
        (result, error_msg) - result is AQI data or None, error_msg is str or None
    """
    # Validate city length
    if len(city) > 100:
        return None, "City name too long"
    
    normalized = normalize_city(city)
    result = get_aqi_cached(normalized)
    
    if not result:
        return None, f"No air quality data available for '{normalized}'"
    
    # Record query for analytics
    record_query(
        city=normalized,
        aqi=result.get("aqi"),
        level=result.get("level"),
        dominentpol=result.get("dominentpol"),
        query_type=query_type,
        source=source,
        user_country=ctx["user_country"],
        device_type=ctx["device_type"],
        ip_address=ctx["ip"],
        user_agent=ctx["ua"]
    )
    
    return result, None


# ===== API ENDPOINTS =====
@app.route("/api/aqi")
def aqi():
    """
    Get AQI for a specific city (cached for 3 minutes per city).
    Query params: city (required), source (optional: 'auto' or 'search'), user_country (optional)
    """
    city = request.args.get("city")
    if not city:
        return error("City parameter is required")
    
    source = request.args.get("source", "search")
    ctx = get_request_context()
    
    result, err = fetch_and_record(city, "single", source, ctx)
    if err:
        return error(err)
    
    return success(result)


@app.route("/api/compare")
def compare():
    """
    Compare AQI between two cities (cached + recorded).
    Query params: city1, city2 (at least one required), user_country (optional)
    """
    city1 = request.args.get("city1")
    city2 = request.args.get("city2")
    
    if not city1 and not city2:
        return error("Please provide at least one city")
    
    ctx = get_request_context()
    data = {}
    
    for key, city in [("city1", city1), ("city2", city2)]:
        if city:
            result, err = fetch_and_record(city, "compare", "search", ctx)
            data[key] = result if result else {"error": err}
    
    return success(data)


@app.route("/api/popular")
@cache.cached()
def popular():
    """
    Get AQI for popular cities with concurrent queries and caching.
    No query parameters required.
    """
    cities = CONFIG["api"]["popular_cities"]
    max_workers = CONFIG.get("query", {}).get("max_workers", 5)
    results = fetch_aqi_for_multiple_cities(cities, CONFIG, max_workers)
    return success(results)

@app.route("/api/subscriptions", methods=["POST"])
def create_email_subscription():
    """Create daily AQI email subscription."""
    payload = request.get_json(silent=True) or {}
    valid_cities = CONFIG["api"].get("popular_cities", [])

    validated, validation_error = validate_subscription_payload(payload, valid_cities)
    if validation_error:
        return error(validation_error, 400)

    try:
        if subscription_exists(validated["email"], validated["city"], validated["alert_time"]):
            return error("Subscription already exists for this city and alert time", 409)

        created = create_subscription(validated)
        return jsonify({
            "status": "success",
            "data": {
                "message": "Subscription registered successfully.",
                "subscription": created,
            },
        }), 201
    except Exception as exc:
        return error(f"Failed to register subscription: {exc}", 500)
# ===== CACHE WARMUP (background) =====
def warmup_cache_background():
    """Pre-load cache in background thread on startup."""
    import threading
    from services.utils import DEFAULT_CITY
    from concurrent.futures import ThreadPoolExecutor
    
    def do_warmup():
        cities = [DEFAULT_CITY] + CONFIG["api"]["popular_cities"]
        max_workers = CONFIG.get("query", {}).get("max_workers", 5)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            executor.map(lambda c: get_aqi_cached(c), cities)
        
        print(f"Cache warmed: {len(cities)} cities")
    
    thread = threading.Thread(target=do_warmup, daemon=True)
    thread.start()

# Start warmup immediately when module loads
warmup_cache_background()

# ===== RUN =====
start_scheduler(CONFIG)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))
    app.run(host="0.0.0.0", port=port, debug=True)
