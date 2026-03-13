import os
from supabase import create_client, Client

# Load .env only for local development (not in production)
if os.getenv("FLASK_ENV") != "production":
    from dotenv import load_dotenv
    load_dotenv()

# Configuration Constants - extracted from hardcoding
SUPABASE_URL_ERROR = "Missing SUPABASE_URL in .env"
SUPABASE_KEY_ERROR = "Missing SUPABASE_KEY in .env"


def get_db() -> Client:
    """Create a Supabase client using environment variables."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url:
        raise ValueError(SUPABASE_URL_ERROR)
    
    if not key:
        raise ValueError(SUPABASE_KEY_ERROR)
    
    return create_client(url, key)


def main():
    try:
        db = get_db()
        print("Connected to Supabase successfully!")
        
        # Test query: list tables
        result = db.table("query_records").select("*").limit(1).execute()
        print("Tables accessible:", result.data if result.data else "Table may not exist yet")
        
    except Exception as e:
        print("Connection/Query failed:")
        print(e)


if __name__ == "__main__":
    main()
