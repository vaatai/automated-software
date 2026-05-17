"""Secure secret management with Fernet symmetric encryption.

Provides:
  - ``SecretVault``: Encrypts/decrypts arbitrary strings using a Fernet key
    derived from ``settings.SECRET_KEY`` via PBKDF2-HMAC-SHA256.
  - ``EncryptedField``: SQLAlchemy TypeDecorator that transparently encrypts
    column values at rest and decrypts on read.
  - ``mask_secret``: Utility to display secrets safely in logs (first/last chars).

All API keys, passwords, and sensitive tokens should be stored through these
primitives rather than in plaintext.
"""

import base64
import hashlib
import logging
import os

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import String, TypeDecorator

logger = logging.getLogger(__name__)

# Salt for key derivation — stable across restarts
_DEFAULT_SALT = b"automated-software-vault-v1"


class SecretVault:
    """Fernet-based secret encryption backed by a derived key.

    The encryption key is derived from ``master_key`` (typically
    ``settings.SECRET_KEY``) using PBKDF2 with 480 000 iterations.

    Usage::

        vault = SecretVault(master_key=settings.SECRET_KEY)
        encrypted = vault.encrypt("my-api-key")
        plaintext = vault.decrypt(encrypted)
    """

    def __init__(
        self,
        master_key: str,
        salt: bytes = _DEFAULT_SALT,
        iterations: int = 480_000,
    ) -> None:
        derived = hashlib.pbkdf2_hmac(
            "sha256",
            master_key.encode("utf-8"),
            salt,
            iterations,
        )
        fernet_key = base64.urlsafe_b64encode(derived[:32])
        self._fernet = Fernet(fernet_key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string and return a URL-safe base64 token."""
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")

    def decrypt(self, token: str) -> str:
        """Decrypt a Fernet token back to the original string.

        Raises ``InvalidToken`` if the token is corrupted or the key is wrong.
        """
        return self._fernet.decrypt(token.encode("ascii")).decode("utf-8")

    def rotate(self, token: str, new_vault: "SecretVault") -> str:
        """Re-encrypt *token* under a different vault's key."""
        plaintext = self.decrypt(token)
        return new_vault.encrypt(plaintext)

    @staticmethod
    def generate_key() -> str:
        """Generate a cryptographically random 32-byte hex key for SECRET_KEY."""
        return os.urandom(32).hex()


def mask_secret(value: str, visible: int = 4) -> str:
    """Return a masked version of *value* suitable for log output.

    Shows the first and last *visible* characters, with ``***`` in between.
    Strings shorter than ``2 * visible + 3`` are fully masked.

    >>> mask_secret("sk-abc123xyz789")
    'sk-a***9789'
    """
    if not value:
        return "***"
    min_len = 2 * visible + 3
    if len(value) < min_len:
        return "*" * len(value)
    return f"{value[:visible]}***{value[-visible:]}"


# ── SQLAlchemy encrypted column type ────────────────────────
# Lazy singleton — initialised on first use so that settings are loaded
_vault_instance: SecretVault | None = None


def _get_vault() -> SecretVault:
    global _vault_instance
    if _vault_instance is None:
        from configs.settings import settings

        _vault_instance = SecretVault(master_key=settings.SECRET_KEY)
    return _vault_instance


class EncryptedField(TypeDecorator):
    """SQLAlchemy column type that encrypts at rest using Fernet.

    Usage in models::

        api_key: Mapped[str] = mapped_column(EncryptedField(), nullable=True)
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: object) -> str | None:  # noqa: ARG002
        if value is None:
            return None
        return _get_vault().encrypt(value)

    def process_result_value(self, value: str | None, dialect: object) -> str | None:  # noqa: ARG002
        if value is None:
            return None
        try:
            return _get_vault().decrypt(value)
        except InvalidToken:
            logger.warning("Failed to decrypt column value — returning raw")
            return value
