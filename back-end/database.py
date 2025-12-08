"""
Database configuration and connection
"""
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

load_dotenv()

# MongoDB connection
MONGO_URL = os.getenv('MONGO_URL')
DATABASE_NAME = 'chess_online'

_client = None
_db = None

def get_db_connection():
    """Tạo kết nối đến MongoDB database"""
    global _client, _db
    
    if _db is None:
        try:
            _client = MongoClient(MONGO_URL)
            # Test connection
            _client.admin.command('ping')
            _db = _client[DATABASE_NAME]
            print(f"Connected to MongoDB: {DATABASE_NAME}")
        except ConnectionFailure as e:
            print(f"Failed to connect to MongoDB: {e}")
            raise
    
    return _db

def init_db():
    """Khởi tạo database và các collections"""
    from models.user import User
    
    try:
        db = get_db_connection()
        
        # Tạo unique index cho username
        users_collection = db[User.get_collection_name()]
        users_collection.create_index('username', unique=True)
        
        print("Database initialized successfully")
        print(f"Collections: {db.list_collection_names()}")
        
    except Exception as e:
        print(f"Error initializing database: {e}")

def close_db_connection():
    """Đóng kết nối database"""
    global _client
    if _client:
        _client.close()
        print("Database connection closed")

# Khởi tạo database khi import
init_db()
