#!/usr/bin/env python3
"""
Test OAuth encryption system
"""

import os
from app.core.security import (
    validate_encryption_setup,
    encrypt_oauth_tokens,
    decrypt_oauth_tokens,
)


def test_encryption():
    print("OAuth encryption environment variables:")
    print(
        f"OAUTH_ENCRYPTION_KEY: {'Set' if os.getenv('OAUTH_ENCRYPTION_KEY') else 'Not set'}"
    )
    print(
        f"OAUTH_ENCRYPTION_PASSWORD: {'Set' if os.getenv('OAUTH_ENCRYPTION_PASSWORD') else 'Not set'}"
    )
    print(
        f"OAUTH_ENCRYPTION_SALT: {'Set' if os.getenv('OAUTH_ENCRYPTION_SALT') else 'Not set'}"
    )
    print()

    # Test encryption validation
    print("Testing encryption validation:")
    is_valid = validate_encryption_setup()
    print(f"Encryption setup is valid: {is_valid}")
    print()

    # Test with basic encryption
    print("Testing basic encryption/decryption:")
    test_data = {"access_token": "test123", "refresh_token": "refresh456"}
    try:
        encrypted = encrypt_oauth_tokens(test_data)
        print(f"Encryption successful: {bool(encrypted)}")

        decrypted = decrypt_oauth_tokens(encrypted)
        print(f"Decryption successful: {bool(decrypted)}")
        print(f"Data integrity: {decrypted == test_data}")
    except Exception as e:
        print(f"Encryption/decryption failed: {e}")


if __name__ == "__main__":
    test_encryption()
