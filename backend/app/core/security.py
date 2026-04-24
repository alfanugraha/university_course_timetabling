"""
backend/app/core/security.py
Password hashing utilities using bcrypt directly.

NOTE: passlib[bcrypt]==1.7.4 is incompatible with bcrypt>=4.0.0 (AttributeError on
__about__ and changed hashpw API). We use the bcrypt library directly — consistent
with scripts/seed.py — to avoid this version mismatch.
"""

import bcrypt


def hash_password(plain_password: str) -> str:
    """Hash a plain-text password using bcrypt.

    Args:
        plain_password: The raw password string from the user.

    Returns:
        A bcrypt hash string suitable for storing in the database.
    """
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a stored bcrypt hash.

    Args:
        plain_password: The raw password to check.
        hashed_password: The bcrypt hash stored in the database.

    Returns:
        True if the password matches, False otherwise.
    """
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
