"""Utility functions for AQI, location, and request handling"""
import os

# Constants
DEFAULT_CITY = "Kuala Lumpur"

# Placeholder AQI data
PLACEHOLDER_AQI = {
    "aqi": "N/A",
    "level": "Unknown",
    "color": "#888888",
    "text_color": "#ffffff",
    "advice": "No data available",
    "dominentpol": "Unknown",
    "time_s": "Unknown"
}


def normalize_city(city):
    """Normalize city name for API queries"""
    if not city:
        return ""
    # Limit length and normalize whitespace
    city = city[:100].strip()
    return " ".join(city.split()).title()


def classify_aqi(aqi, config):
    """Classify AQI value based on configuration levels"""
    for level in config["aqi_levels"]:
        if level["min"] <= aqi <= level["max"]:
            return level
    # Fallback to highest level if no match (should not happen with proper config)
    return config["aqi_levels"][-1]


def get_client_info(request):
    """
    Extract client IP and User-Agent from Flask request.
    Handles proxy headers (X-Forwarded-For).
    
    Returns: (ip, ua)
    """
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        # X-Forwarded-For: client, proxy1, proxy2
        ip = xff.split(",")[0].strip()
    else:
        ip = request.remote_addr
    
    ua = request.headers.get("User-Agent", "")
    return ip, ua


def parse_device_type(user_agent):
    """
    Parse device type from User-Agent string.
    
    Returns: 'mobile' or 'desktop'
    """
    if not user_agent:
        return "desktop"
    
    ua_lower = user_agent.lower()
    mobile_keywords = ["mobile", "android", "iphone", "ipad", "ipod", "webos", "opera mini"]
    
    return "mobile" if any(kw in ua_lower for kw in mobile_keywords) else "desktop"


def get_request_context(request):
    """
    Extract common request context for analytics.
    
    Args:
        request: Flask request object
        
    Returns:
        dict with ip, ua, user_country, device_type
    """
    ip, ua = get_client_info(request)
    user_country = request.args.get("user_country")
    
    # Truncate if too long
    if user_country and len(user_country) > 100:
        user_country = user_country[:100]
    
    return {
        "ip": ip,
        "ua": ua,
        "user_country": user_country,
        "device_type": parse_device_type(ua)
    }