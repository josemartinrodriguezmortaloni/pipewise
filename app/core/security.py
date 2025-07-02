"""
Security utilities for PipeWise OAuth integrations

Provides encryption/decryption functions for sensitive data like OAuth tokens,
API keys, and other credentials stored in the database.
"""

import os
import base64
import json
from typing import Any, Dict, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)


class SecurityManager:
    """Manages encryption and decryption of sensitive data"""

    def __init__(self):
        self._cipher_suite: Optional[Fernet] = None
        self._initialize_cipher()

    def _initialize_cipher(self) -> None:
        """Initialize the Fernet cipher suite using environment variables"""
        encryption_key = os.getenv("ENCRYPTION_KEY")

        if not encryption_key:
            # Generate a new key if none exists (for development)
            logger.warning(
                "No ENCRYPTION_KEY found in environment. Generating new key for development."
            )
            encryption_key = self._generate_key()
            logger.info(f"Generated encryption key: {encryption_key}")
            logger.info(
                "Please add this to your environment variables: ENCRYPTION_KEY={encryption_key}"
            )

        try:
            # Try to use the key directly if it's already base64 encoded
            self._cipher_suite = Fernet(encryption_key.encode())
        except Exception:
            try:
                # If that fails, assume it's a password and derive a key
                self._cipher_suite = Fernet(
                    self._derive_key_from_password(encryption_key)
                )
            except Exception as e:
                logger.error(f"Failed to initialize encryption: {e}")
                raise ValueError(
                    "Invalid encryption key. Please check ENCRYPTION_KEY environment variable."
                )

    def _generate_key(self) -> str:
        """Generate a new Fernet key"""
        return Fernet.generate_key().decode()

    def _derive_key_from_password(self, password: str) -> bytes:
        """Derive a Fernet key from a password using PBKDF2"""
        # Use a fixed salt for consistency (in production, store this securely)
        salt = os.getenv("ENCRYPTION_SALT", "pipewise_oauth_salt").encode()

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

    def encrypt_json(self, data: Dict[str, Any]) -> str:
        """Encrypt a dictionary as JSON string"""
        if not self._cipher_suite:
            raise ValueError("Encryption not initialized")

        try:
            json_string = json.dumps(data, sort_keys=True)
            encrypted_data = self._cipher_suite.encrypt(json_string.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ValueError("Failed to encrypt data")

    def decrypt_json(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt an encrypted JSON string back to dictionary"""
        if not self._cipher_suite:
            raise ValueError("Encryption not initialized")

        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self._cipher_suite.decrypt(encrypted_bytes)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Failed to decrypt data")

    def encrypt_string(self, text: str) -> str:
        """Encrypt a plain text string"""
        if not self._cipher_suite:
            raise ValueError("Encryption not initialized")

        try:
            encrypted_data = self._cipher_suite.encrypt(text.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"String encryption failed: {e}")
            raise ValueError("Failed to encrypt string")

    def decrypt_string(self, encrypted_text: str) -> str:
        """Decrypt an encrypted string"""
        if not self._cipher_suite:
            raise ValueError("Encryption not initialized")

        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_text.encode())
            decrypted_data = self._cipher_suite.decrypt(encrypted_bytes)
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"String decryption failed: {e}")
            raise ValueError("Failed to decrypt string")


# Global security manager instance
security_manager = SecurityManager()


def encrypt_oauth_tokens(tokens: Dict[str, Any]) -> str:
    """
    Encrypt OAuth tokens for secure storage

    Args:
        tokens: Dictionary containing OAuth tokens (access_token, refresh_token, etc.)

    Returns:
        Encrypted string representation of tokens
    """
    return security_manager.encrypt_json(tokens)


def decrypt_oauth_tokens(encrypted_tokens: str) -> Dict[str, Any]:
    """
    Decrypt OAuth tokens from secure storage

    Args:
        encrypted_tokens: Encrypted string representation of tokens

    Returns:
        Dictionary containing decrypted OAuth tokens
    """
    return security_manager.decrypt_json(encrypted_tokens)


def encrypt_api_key(api_key: str) -> str:
    """
    Encrypt a single API key for secure storage

    Args:
        api_key: Plain text API key

    Returns:
        Encrypted API key string
    """
    return security_manager.encrypt_string(api_key)


def decrypt_api_key(encrypted_api_key: str) -> str:
    """
    Decrypt a single API key from secure storage

    Args:
        encrypted_api_key: Encrypted API key string

    Returns:
        Plain text API key
    """
    return security_manager.decrypt_string(encrypted_api_key)


def safe_decrypt(
    encrypted_data: str, fallback: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Safely decrypt data with fallback for legacy unencrypted data

    Args:
        encrypted_data: Potentially encrypted data
        fallback: Fallback value if decryption fails

    Returns:
        Decrypted data or fallback
    """
    try:
        # Try to decrypt as JSON
        return decrypt_oauth_tokens(encrypted_data)
    except Exception:
        try:
            # If that fails, try to parse as plain JSON (legacy data)
            return json.loads(encrypted_data)
        except Exception:
            logger.warning("Failed to decrypt or parse data, using fallback")
            return fallback or {}


def is_encrypted(data: str) -> bool:
    """
    Check if data appears to be encrypted

    Args:
        data: String to check

    Returns:
        True if data appears encrypted, False otherwise
    """
    try:
        # Try to decode as base64 - encrypted data should be base64 encoded
        base64.urlsafe_b64decode(data.encode())
        # If successful and doesn't look like JSON, likely encrypted
        return not (data.strip().startswith("{") and data.strip().endswith("}"))
    except Exception:
        return False
