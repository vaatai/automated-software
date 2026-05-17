"""Unit tests for security/password.py — bcrypt hashing, verification."""

import pytest

from security.password import generate_temp_password, hash_password, verify_password


@pytest.mark.unit
class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "MySecureP@ssw0rd!"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("correct-password")
        assert verify_password("wrong-password", hashed) is False

    def test_hash_uniqueness(self):
        password = "same-password"
        h1 = hash_password(password)
        h2 = hash_password(password)
        assert h1 != h2  # different salts

    def test_long_password_over_72_bytes(self):
        long_pw = "a" * 100  # >72 bytes, triggers SHA-256 pre-hashing
        hashed = hash_password(long_pw)
        assert verify_password(long_pw, hashed) is True

    def test_unicode_password(self):
        pw = "p\u00e4ssw\u00f6rd-\u2603"
        hashed = hash_password(pw)
        assert verify_password(pw, hashed) is True

    def test_empty_password(self):
        hashed = hash_password("")
        assert verify_password("", hashed) is True
        assert verify_password("not-empty", hashed) is False

    def test_hash_starts_with_bcrypt_prefix(self):
        hashed = hash_password("test")
        assert hashed.startswith("$2b$")


@pytest.mark.unit
class TestTempPasswordGeneration:
    def test_default_length(self):
        pw = generate_temp_password()
        assert len(pw) >= 16

    def test_custom_length(self):
        pw = generate_temp_password(length=24)
        assert len(pw) == 24

    def test_uniqueness(self):
        passwords = {generate_temp_password() for _ in range(10)}
        assert len(passwords) == 10
