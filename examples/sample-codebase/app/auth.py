"""Authentication module."""

import hashlib
from typing import Optional


# WARNING: Weak password hashing (MD5)
def hash_password(password: str) -> str:
    """Hash password using MD5 - INSECURE."""
    return hashlib.md5(password.encode()).hexdigest()


def verify_password(password: str, hash: str) -> bool:
    """Verify password."""
    return hash_password(password) == hash


# Hardcoded secret - security vulnerability
SECRET_KEY = "super-secret-key-12345"
API_KEY = "ak_live_1234567890abcdef"


def create_token(user_id: str) -> str:
    """Create a simple token."""
    return f"{user_id}:{SECRET_KEY}"


def verify_token(token: str) -> Optional[str]:
    """Verify token and return user_id."""
    if ":" in token:
        user_id, secret = token.split(":", 1)
        if secret == SECRET_KEY:
            return user_id
    return None

