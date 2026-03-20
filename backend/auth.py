"""
auth.py
───────
Authentication helpers: password hashing, user creation, JWT utilities.
Uses bcrypt for password hashing (industry standard, resistant to brute-force).
Uses Flask-JWT-Extended for token generation and verification.
"""

import bcrypt
from flask_jwt_extended import create_access_token, get_jwt_identity, get_jwt
from database import get_db
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


# ─── Password Helpers ────────────────────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """
    Hash a plain-text password using bcrypt with a random salt.

    Args:
        plain_password: The user's raw password string.

    Returns:
        A UTF-8 encoded bcrypt hash string.
    """
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed: str) -> bool:
    """
    Verify a plain-text password against a stored bcrypt hash.

    Args:
        plain_password: The password the user submitted.
        hashed: The stored bcrypt hash from the database.

    Returns:
        True if the password matches, False otherwise.
    """
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed.encode('utf-8'))


# ─── User Helpers ─────────────────────────────────────────────────────────────

def find_user_by_email(email: str) -> dict | None:
    """Find a user document by email (case-insensitive)."""
    db = get_db()
    return db.users.find_one({'email': email.lower().strip()})


def create_user(name: str, email: str, password: str, role: str = 'user') -> dict:
    """
    Create and persist a new user document.

    Args:
        name:     Display name.
        email:    Email address (stored lowercase).
        password: Plain-text password (will be hashed before storage).
        role:     'user' or 'admin'.

    Returns:
        The inserted user document (without password_hash).

    Raises:
        ValueError: If the email is already registered.
    """
    db = get_db()
    email = email.lower().strip()

    if db.users.find_one({'email': email}):
        raise ValueError('Email already registered.')

    user_doc = {
        'name': name.strip(),
        'email': email,
        'password_hash': hash_password(password),
        'role': role,
        'nationality': '',
        'created_at': __import__('datetime').datetime.utcnow()
    }
    result = db.users.insert_one(user_doc)
    user_doc['_id'] = result.inserted_id
    logger.info(f'New user created: {email} (role={role})')
    return user_doc


def generate_token(user_id: str, role: str) -> str:
    """
    Generate a JWT access token encoding user identity and role.

    Args:
        user_id: The MongoDB ObjectId string of the user.
        role:    'user' or 'admin'.

    Returns:
        A signed JWT access token string.
    """
    additional_claims = {'role': role}
    return create_access_token(
        identity=user_id,
        additional_claims=additional_claims,
        expires_delta=timedelta(hours=24)
    )


def is_admin() -> bool:
    """
    Check if the currently authenticated JWT belongs to an admin user.
    Must be called inside a JWT-protected route.
    """
    claims = get_jwt()
    return claims.get('role') == 'admin'
