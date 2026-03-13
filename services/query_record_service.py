"""Service for recording and retrieving user AQI queries from database"""
import os
from datetime import datetime, timedelta
from database.connection import get_db

DB_TABLE_NAME = os.getenv("DB_TABLE_NAME", "query_records")


def record_query(city, aqi=None, level=None, dominentpol=None, query_type="single", source="search", user_country=None, 
    device_type=None, ip_address=None, user_agent=None):
    """
    Record a query to the database.
    Silently fails if table doesn't exist (app continues working).
    
    Args:
        city: City name queried
        aqi: AQI value (optional)
        level: AQI level (optional)
        dominentpol: Dominant pollutant (optional)
        query_type: 'single' or 'compare' (default: single)
        source: 'auto' or 'search' (default: search)
        user_country: User's country from IP geolocation (optional)
        device_type: 'mobile' or 'desktop' (optional)
        ip_address: User's IP address (optional)
        user_agent: User's browser agent (optional)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        db = get_db()
        
        data = {
            "city": city,
            "aqi": aqi,
            "level": level,
            "dominentpol": dominentpol,
            "query_type": query_type,
            "source": source,
            "user_country": user_country,
            "device_type": device_type,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": (datetime.utcnow() + timedelta(hours=8)).isoformat()
        }
        
        db.table(DB_TABLE_NAME).insert(data).execute()
        print(f"✓ Recorded query: {city} (AQI: {aqi})")
        return True
        
    except Exception as e:
        error_str = str(e)
        # Table doesn't exist - silently continue
        if DB_TABLE_NAME in error_str or "PGRST205" in error_str:
            print(f"ℹ️  Note: {DB_TABLE_NAME} table not yet created")
        else:
            print(f"⚠️  Error recording query: {error_str}")
        return False


def get_query_history(city=None, limit=10):
    """
    Retrieve query history from database.
    
    Args:
        city: Optional city name to filter by
        limit: Maximum number of records to return
        
    Returns:
        List of query records (empty if table doesn't exist)
    """
    try:
        db = get_db()
        query = db.table(DB_TABLE_NAME).select("*").limit(limit).order("created_at", desc=True)
        
        if city:
            query = query.eq("city", city)
        
        result = query.execute()
        return result.data
                    
    except Exception:
        # Table doesn't exist or other error - return empty list
        return []
