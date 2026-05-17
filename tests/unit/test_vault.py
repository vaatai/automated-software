"""Unit tests for security/vault.py — Fernet encryption, masking."""

import pytest

from security.vault import SecretVault, mask_secret


@pytest.mark.unit
class TestSecretVault:
    def setup_method(self):
        self.vault = SecretVault(master_key="test-master-key-12345")

    def test_encrypt_decrypt_roundtrip(self):
        plaintext = "sk-abc123-my-api-key"
        encrypted = self.vault.encrypt(plaintext)
        assert encrypted != plaintext
        assert self.vault.decrypt(encrypted) == plaintext

    def test_encrypt_produces_different_tokens(self):
        plaintext = "same-secret"
        t1 = self.vault.encrypt(plaintext)
        t2 = self.vault.encrypt(plaintext)
        assert t1 != t2  # Fernet tokens include timestamps

    def test_decrypt_wrong_key_raises(self):
        from cryptography.fernet import InvalidToken

        encrypted = self.vault.encrypt("secret")
        other_vault = SecretVault(master_key="different-key-entirely")
        with pytest.raises(InvalidToken):
            other_vault.decrypt(encrypted)

    def test_empty_string_roundtrip(self):
        encrypted = self.vault.encrypt("")
        assert self.vault.decrypt(encrypted) == ""

    def test_unicode_roundtrip(self):
        text = "sensitive-data-\u2603-\u00e9\u00e0\u00fc"
        assert self.vault.decrypt(self.vault.encrypt(text)) == text

    def test_long_string_roundtrip(self):
        text = "a" * 10000
        assert self.vault.decrypt(self.vault.encrypt(text)) == text

    def test_rotate_key(self):
        old_vault = SecretVault(master_key="old-key")
        new_vault = SecretVault(master_key="new-key")
        token = old_vault.encrypt("my-secret")
        new_token = old_vault.rotate(token, new_vault)
        assert new_vault.decrypt(new_token) == "my-secret"

    def test_generate_key_length(self):
        key = SecretVault.generate_key()
        assert len(key) == 64  # 32 bytes hex-encoded

    def test_generate_key_uniqueness(self):
        keys = {SecretVault.generate_key() for _ in range(10)}
        assert len(keys) == 10

    def test_custom_salt(self):
        vault1 = SecretVault(master_key="key", salt=b"salt-a")
        vault2 = SecretVault(master_key="key", salt=b"salt-b")
        token = vault1.encrypt("test")
        from cryptography.fernet import InvalidToken

        with pytest.raises(InvalidToken):
            vault2.decrypt(token)


@pytest.mark.unit
class TestMaskSecret:
    def test_normal_string(self):
        result = mask_secret("sk-abc123xyz789")
        assert result.startswith("sk-a")
        assert result.endswith("z789")
        assert "***" in result

    def test_short_string_fully_masked(self):
        result = mask_secret("abc")
        assert result == "***"  # len("abc") < 2*4+3=11, so "*"*3

    def test_empty_string(self):
        assert mask_secret("") == "***"

    def test_custom_visible(self):
        result = mask_secret("abcdefghijklmnop", visible=2)
        assert result == "ab***op"

    def test_exact_min_length(self):
        result = mask_secret("abcdefghijk")  # 11 chars, 2*4+3=11
        assert result.startswith("abcd")
        assert result.endswith("hijk")
