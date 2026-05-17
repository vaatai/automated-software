"""Password hashing using bcrypt via passlib.

Provides secure password hashing and verification for user authentication.
Uses bcrypt with automatic salt generation and configurable rounds.
"""

import hashlib
import logging
import os

logger = logging.getLogger(__name__)

# bcrypt has a 72-byte input limit; we pre-hash longer passwords with SHA-256
_MAX_BCRYPT_INPUT = 72


def _prehash(password: str) -> str:
    """Pre-hash passwords that exceed bcrypt's 72-byte limit."""
    encoded = password.encode("utf-8")
    if len(encoded) > _MAX_BCRYPT_INPUT:
        return hashlib.sha256(encoded).hexdigest()
    return password


def hash_password(password: str, rounds: int = 12) -> str:
    """Hash a plaintext password and return the bcrypt hash string.

    Args:
        password: The plaintext password to hash.
        rounds: bcrypt cost factor (default 12, ~250ms on modern hardware).

    Returns:
        A bcrypt hash string like ``$2b$12$...``.
    """
    import bcrypt

    pw = _prehash(password).encode("utf-8")
    salt = bcrypt.gensalt(rounds=rounds)
    return bcrypt.hashpw(pw, salt).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a bcrypt hash.

    Uses constant-time comparison to prevent timing attacks.
    """
    import bcrypt

    try:
        pw = _prehash(password).encode("utf-8")
        return bcrypt.checkpw(pw, password_hash.encode("ascii"))
    except Exception:
        logger.debug("Password verification failed")
        return False


def generate_temp_password(length: int = 16) -> str:
    """Generate a cryptographically random temporary password."""
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%"
    return "".join(alphabet[b % len(alphabet)] for b in os.urandom(length))
