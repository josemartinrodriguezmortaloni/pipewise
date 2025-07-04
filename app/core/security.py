"""
Security utilities for PipeWise

Provides encryption/decryption functions for OAuth tokens and other sensitive data.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

logger = logging.getLogger(__name__)


def _get_encryption_key() -> bytes:
    """
    Get or generate encryption key for OAuth tokens.

    Returns:
        Encryption key bytes
    """
    # Try to get key from environment
    env_key = os.getenv("OAUTH_ENCRYPTION_KEY")
    if env_key:
        try:
            return base64.urlsafe_b64decode(env_key)
        except Exception as e:
            logger.warning(f"Invalid OAUTH_ENCRYPTION_KEY in environment: {e}")

    # Generate key from password/salt
    password = os.getenv(
        "OAUTH_ENCRYPTION_PASSWORD", "pipewise-default-password"
    ).encode()
    salt = os.getenv("OAUTH_ENCRYPTION_SALT", "pipewise-default-salt").encode()

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))

    # Log warning about using default encryption
    if not env_key:
        logger.warning(
            "Using default encryption key. Set OAUTH_ENCRYPTION_KEY environment variable for production."
        )

    return key


def encrypt_oauth_tokens(tokens: Dict[str, Any]) -> str:
    """
    Encrypt OAuth tokens for secure storage.

    Args:
        tokens: Dictionary containing OAuth tokens and metadata

    Returns:
        Encrypted token string (base64 encoded)

    Raises:
        Exception: If encryption fails
    """
    try:
        # Convert tokens to JSON string
        tokens_json = json.dumps(tokens, default=str)
        tokens_bytes = tokens_json.encode("utf-8")

        # Get encryption key and create Fernet instance
        key = _get_encryption_key()
        fernet = Fernet(key)

        # Encrypt the tokens
        encrypted_tokens = fernet.encrypt(tokens_bytes)

        # Return base64 encoded string for database storage
        return base64.urlsafe_b64encode(encrypted_tokens).decode("utf-8")

    except Exception as e:
        logger.error(f"Failed to encrypt OAuth tokens: {e}")
        raise Exception(f"Token encryption failed: {str(e)}")


def decrypt_oauth_tokens(encrypted_tokens: str) -> Dict[str, Any]:
    """
    Decrypt OAuth tokens from storage.

    Args:
        encrypted_tokens: Base64 encoded encrypted token string

    Returns:
        Dictionary containing decrypted OAuth tokens

    Raises:
        Exception: If decryption fails
    """
    try:
        # Decode from base64
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_tokens.encode("utf-8"))

        # Get encryption key and create Fernet instance
        key = _get_encryption_key()
        fernet = Fernet(key)

        # Decrypt the tokens
        decrypted_bytes = fernet.decrypt(encrypted_bytes)
        tokens_json = decrypted_bytes.decode("utf-8")

        # Parse JSON back to dictionary
        tokens = json.loads(tokens_json)

        return tokens

    except Exception as e:
        logger.error(f"Failed to decrypt OAuth tokens: {e}")
        raise Exception(f"Token decryption failed: {str(e)}")


def safe_decrypt(encrypted_tokens: Optional[str]) -> Dict[str, Any]:
    """
    Safely decrypt OAuth tokens with error handling.

    Args:
        encrypted_tokens: Base64 encoded encrypted token string (can be None)

    Returns:
        Dictionary containing decrypted OAuth tokens, or empty dict if decryption fails
    """
    if not encrypted_tokens:
        logger.warning("No encrypted tokens provided for decryption")
        return {}

    try:
        return decrypt_oauth_tokens(encrypted_tokens)
    except Exception as e:
        logger.error(f"Safe decrypt failed: {e}")
        return {}


def generate_encryption_key() -> str:
    """
    Generate a new encryption key for OAuth tokens.

    Returns:
        Base64 encoded encryption key string
    """
    key = Fernet.generate_key()
    return base64.urlsafe_b64encode(key).decode("utf-8")


def validate_encryption_setup() -> bool:
    """
    Validate that encryption setup is working correctly.

    Returns:
        True if encryption/decryption works, False otherwise
    """
    try:
        # Test data
        test_tokens = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

        # Test encryption
        encrypted = encrypt_oauth_tokens(test_tokens)

        # Test decryption
        decrypted = decrypt_oauth_tokens(encrypted)

        # Verify data integrity
        return decrypted == test_tokens

    except Exception as e:
        logger.error(f"Encryption validation failed: {e}")
        return False


# Additional security utilities


def mask_sensitive_data(
    data: Dict[str, Any], sensitive_keys: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Mask sensitive data in dictionaries for logging.

    Args:
        data: Dictionary that may contain sensitive data
        sensitive_keys: List of keys to mask (default: common OAuth keys)

    Returns:
        Dictionary with sensitive values masked
    """
    if sensitive_keys is None:
        sensitive_keys = [
            "access_token",
            "refresh_token",
            "client_secret",
            "password",
            "totp_secret",
            "backup_codes",
        ]

    masked_data = data.copy()

    for key in sensitive_keys:
        if key in masked_data:
            value = str(masked_data[key])
            if len(value) > 8:
                masked_data[key] = f"{value[:4]}***{value[-4:]}"
            else:
                masked_data[key] = "***"

    return masked_data


def secure_compare(a: str, b: str) -> bool:
    """
    Secure string comparison to prevent timing attacks.

    Args:
        a: First string
        b: Second string

    Returns:
        True if strings are equal, False otherwise
    """
    if len(a) != len(b):
        return False

    result = 0
    for x, y in zip(a, b):
        result |= ord(x) ^ ord(y)

    return result == 0
