"""
config.py
─────────
Centralised application configuration.
Loads environment variables from .env file.
All other modules import from here — never import os.environ directly.
"""

import os
from dotenv import load_dotenv

# Load .env file from the same directory as this file
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))


class Config:
    """Base configuration shared across all environments."""

    # MongoDB
    MONGO_URI: str = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
    DB_NAME: str = os.environ.get('DB_NAME', 'diana_beach')

    # JWT
    JWT_SECRET_KEY: str = os.environ.get('JWT_SECRET_KEY', 'dev-secret-change-in-prod')
    JWT_ACCESS_TOKEN_EXPIRES: int = 60 * 60 * 24  # 24 hours in seconds

    # Flask
    DEBUG: bool = os.environ.get('FLASK_ENV', 'development') == 'development'

    # Admin seed credentials
    ADMIN_EMAIL: str = os.environ.get('ADMIN_EMAIL', 'admin@dianabeach.lk')
    ADMIN_PASSWORD: str = os.environ.get('ADMIN_PASSWORD', 'Admin@Diana2025')


config = Config()
