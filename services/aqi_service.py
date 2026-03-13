"""Service for fetching and querying AQI data"""
import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from services.utils import normalize_city, classify_aqi, PLACEHOLDER_AQI

# API Configuration
AQI_API_URL = os.getenv("AQI_API_URL")
AQI_API_TOKEN = os.getenv("AQI_API_TOKEN")
AQI_API_TIMEOUT = 5


def _fetch_aqi_raw(city):
    """
    Low-level function: Fetch raw AQI data for a city from external API.
    
    Args:
        city: Normalized city name to query
        
    Returns:
        Dict with raw AQI data or None if request fails
    """
    if not city:
        return None
    
    try:
        url = f"{AQI_API_URL}/{city}/?token={AQI_API_TOKEN}"
        response = requests.get(url, timeout=AQI_API_TIMEOUT).json()
        
        # Check API response status
        if response.get("status") != "ok":
            return None
        
        # Extract and validate AQI value
        aqi_raw = response["data"].get("aqi")
        try:
            aqi = int(aqi_raw)
        except (ValueError, TypeError):
            return None
        
        # Gather additional info (use 'or' to handle empty strings)
        dominentpol = response["data"].get("dominentpol") or "Unknown"
        time_s = response["data"].get("time", {}).get("s") or "Unknown"
        
        return {
            "aqi": aqi,
            "dominentpol": dominentpol,
            "time_s": time_s
        }
    
    except (requests.RequestException, KeyError, ValueError):
        return None


def get_aqi(city, config):
    """
    Fetch and classify AQI data for a city.
    
    Args:
        city: City name to query
        config: Configuration dict with aqi_levels
        
    Returns:
        Dict with classified AQI data or None if request fails
    """
    raw_data = _fetch_aqi_raw(city)
    if not raw_data:
        return None
    
    # Classify AQI
    info = classify_aqi(raw_data["aqi"], config)
    
    return {
        "city": city,
        "aqi": raw_data["aqi"],
        "level": info["level"],
        "color": info["color"],
        "text_color": info["text_color"],
        "advice": info["advice"],
        "dominentpol": raw_data["dominentpol"],
        "time_s": raw_data["time_s"]
    }


def fetch_aqi_for_multiple_cities(cities, config, max_workers=5):
    """
    Fetch AQI for multiple cities concurrently without recording.
    Used for popular cities list (cached).
    
    Args:
        cities: List of city names
        config: Configuration dict
        max_workers: Number of concurrent threads
        
    Returns:
        List of AQI results (with placeholders for failed queries)
    """
    results = []
    
    def fetch_city(city):
        """Fetch AQI for single city"""
        normalized = normalize_city(city)
        return city, get_aqi(normalized, config)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_city, city): city for city in cities}
        
        for future in as_completed(futures):
            original_city, aqi_result = future.result()
            if not aqi_result:
                aqi_result = {**PLACEHOLDER_AQI, "city": original_city}
            results.append(aqi_result)
    
    return results
