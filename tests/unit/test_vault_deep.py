"""Deep coverage tests for security.vault module."""

import pytest


@pytest.mark.unit
class TestVaultEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        from security.vault import SecretVault

        vault = SecretVault(master_key="test-master-key-for-vault")
        encrypted = vault.encrypt("my-secret-api-key")
        decrypted = vault.decrypt(encrypted)
        assert decrypted == "my-secret-api-key"

    def test_encrypt_different_each_time(self):
        from security.vault import SecretVault

        vault = SecretVault(master_key="test-key")
        e1 = vault.encrypt("same-value")
        e2 = vault.encrypt("same-value")
        # Fernet uses different IVs, so ciphertexts should differ
        assert e1 != e2

    def test_decrypt_wrong_key_fails(self):
        from security.vault import SecretVault

        vault1 = SecretVault(master_key="key-one")
        vault2 = SecretVault(master_key="key-two")
        encrypted = vault1.encrypt("secret")
        with pytest.raises(Exception):
            vault2.decrypt(encrypted)

    def test_encrypt_empty_string(self):
        from security.vault import SecretVault

        vault = SecretVault(master_key="test-key")
        encrypted = vault.encrypt("")
        assert vault.decrypt(encrypted) == ""

    def test_encrypt_long_string(self):
        from security.vault import SecretVault

        vault = SecretVault(master_key="test-key")
        long_value = "x" * 10000
        encrypted = vault.encrypt(long_value)
        assert vault.decrypt(encrypted) == long_value

    def test_mask_secret_short(self):
        from security.vault import mask_secret

        result = mask_secret("ab")
        assert "*" in result

    def test_mask_secret_normal(self):
        from security.vault import mask_secret

        result = mask_secret("my-secret-key-12345")
        assert "***" in result


@pytest.mark.unit
class TestEncryptedField:
    def test_encrypted_field_import(self):
        from security.vault import EncryptedField

        assert EncryptedField is not None

    def test_encrypted_field_type(self):
        from security.vault import EncryptedField

        field = EncryptedField()
        assert hasattr(field, "process_bind_param")
        assert hasattr(field, "process_result_value")

    def test_process_bind_param_none(self):
        from security.vault import EncryptedField

        field = EncryptedField()
        result = field.process_bind_param(None, None)
        assert result is None

    def test_process_result_value_none(self):
        from security.vault import EncryptedField

        field = EncryptedField()
        result = field.process_result_value(None, None)
        assert result is None
