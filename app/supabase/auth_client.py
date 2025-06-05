from typing import Optional, Dict, Any
from supabase import create_client
from supabase.exceptions import AuthError
import logging

logger = logging.getLogger(__name__)

class AuthClient:
    def __init__(self, url: str, key: str):
        self.client = create_client(url, key)

    async def sign_up_with_email(self, email: str, password: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Register a new user in Supabase using email/password."""
        try:
            response = self.client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": metadata or {},
                },
            })
            # The python supabase client returns a UserResponse object
            return {
                "user": response.user.dict() if response.user else None,
                "access_token": response.session.access_token if response.session else None,
                "refresh_token": response.session.refresh_token if response.session else None,
                "expires_in": response.session.expires_in if response.session else None,
            }
        except AuthError as e:
            logger.error(f"Error signing up user: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during sign up: {e}")
            return None

    async def sign_in_with_email(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate an existing user via email/password."""
        try:
            response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password,
            })
            return {
                "user": response.user.dict() if response.user else None,
                "access_token": response.session.access_token if response.session else None,
                "refresh_token": response.session.refresh_token if response.session else None,
                "expires_in": response.session.expires_in if response.session else None,
            }
        except AuthError as e:
            logger.error(f"Error signing in user: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during sign in: {e}")
            return None