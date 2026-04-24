from pymongo import MongoClient
from pymongo.database import Database

from app.config import settings

_client: MongoClient | None = None


def get_mongo_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(settings.mongodb_url)
    return _client


def get_db() -> Database:
    client = get_mongo_client()
    return client[settings.mongodb_db_name]
