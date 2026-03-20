"""
database.py
───────────
MongoDB Atlas connection module.
Provides a single shared MongoClient instance via get_db().

Collections used:
  - users     : registered users + admin accounts
  - dishes    : menu items
  - reviews   : guest reviews linked to dishes + nationality
"""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from config import config
import logging

logger = logging.getLogger(__name__)

_client: MongoClient = None


def get_client() -> MongoClient:
    """
    Return the shared MongoClient, creating it on first call.
    Uses a module-level singleton to avoid opening multiple connections.
    """
    global _client
    if _client is None:
        _client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=5000)
        try:
            # Ping to verify connection is alive
            _client.admin.command('ping')
            logger.info('MongoDB connection established.')
        except ConnectionFailure as e:
            logger.error(f'MongoDB connection failed: {e}')
            raise
    return _client


def get_db():
    """Return the application database object."""
    return get_client()[config.DB_NAME]
