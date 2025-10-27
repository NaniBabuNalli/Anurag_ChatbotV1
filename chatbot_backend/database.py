# chatbot_backend/database.py
import motor.motor_asyncio
import os
from typing import Optional

# MongoDB configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://22eg106b52_db_user:ID1HC1Jt7iSQTZD8@anurag-chatbot.1zycn8n.mongodb.net/")
DATABASE_NAME = "university_db"

# Global MongoDB client
_client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
_db: Optional[motor.motor_asyncio.AsyncIOMotorDatabase] = None

async def get_database():
    """Get database connection with proper error handling"""
    global _client, _db
    
    if _client is None:
        try:
            _client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
            # Test connection
            await _client.admin.command('ping')
            _db = _client[DATABASE_NAME]
            print(f"✅ MongoDB connected successfully to database: {DATABASE_NAME}")
        except Exception as e:
            # Don't crash the whole application on DB connection failure during startup.
            # Log the error and allow the app to continue running (knowledge base still works).
            print(f"❌ MongoDB connection failed: {e}")
            _client = None
            _db = None
            return None
    
    return _db

async def close_database():
    """Close database connection"""
    global _client
    if _client:
        _client.close()
        print("MongoDB connection closed.")