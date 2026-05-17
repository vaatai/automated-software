"""Unit tests for utils/data_generator.py — random data generation."""

import pytest

from utils.data_generator import (
    generate_password,
    generate_registration_data,
    generate_username,
)


@pytest.mark.unit
class TestGenerateUsername:
    def test_default_prefix(self):
        username = generate_username()
        assert username.startswith("user_")
        assert len(username) > 5

    def test_custom_prefix(self):
        username = generate_username(prefix="bot")
        assert username.startswith("bot_")

    def test_uniqueness(self):
        usernames = {generate_username() for _ in range(50)}
        assert len(usernames) == 50


@pytest.mark.unit
class TestGeneratePassword:
    def test_default_length(self):
        pw = generate_password()
        assert len(pw) == 14

    def test_custom_length(self):
        pw = generate_password(length=20)
        assert len(pw) == 20

    def test_has_uppercase(self):
        pw = generate_password()
        assert any(c.isupper() for c in pw)

    def test_has_lowercase(self):
        pw = generate_password()
        assert any(c.islower() for c in pw)

    def test_has_digit(self):
        pw = generate_password()
        assert any(c.isdigit() for c in pw)

    def test_has_special_char(self):
        pw = generate_password()
        assert any(c in "!@#$%" for c in pw)

    def test_uniqueness(self):
        passwords = {generate_password() for _ in range(50)}
        assert len(passwords) == 50


@pytest.mark.unit
class TestGenerateRegistrationData:
    def test_has_required_fields(self):
        data = generate_registration_data()
        assert "username" in data
        assert "first_name" in data
        assert "last_name" in data
        assert "full_name" in data
        assert "password" in data

    def test_full_name_composed(self):
        data = generate_registration_data()
        assert data["full_name"] == f"{data['first_name']} {data['last_name']}"

    def test_username_format(self):
        data = generate_registration_data()
        assert data["username"].startswith("user_")

    def test_password_strength(self):
        data = generate_registration_data()
        pw = data["password"]
        assert len(pw) >= 14
        assert any(c.isupper() for c in pw)
        assert any(c.isdigit() for c in pw)
