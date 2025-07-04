"""
OAuth Handler for PipeWise Integrations

Centralized OAuth 2.0 flow management for external service integrations.
Handles authorization URL generation, token exchange, and secure storage.
"""

import secrets
import urllib.parse
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
import httpx
from fastapi import HTTPException
import uuid
import base64

from app.core.oauth_config import (
    get_oauth_config,
    build_redirect_uri,
    generate_pkce_pair,
    get_services_requiring_pkce,
)
from app.core.security import encrypt_oauth_tokens, decrypt_oauth_tokens, safe_decrypt
from app.supabase.supabase_client import get_supabase_client, get_supabase_admin_client

logger = logging.getLogger(__name__)


class OAuthHandler:
    """Handles OAuth 2.0 flows for external service integrations"""

    def __init__(self):
        # Add debug logs for initialization
        logger.info("🔧 Initializing OAuthHandler...")
        try:
            self.supabase = get_supabase_client()
            self.supabase_admin = get_supabase_admin_client()
            logger.info("✅ Supabase clients initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase clients: {e}")
            raise

        # Store CSRF state tokens temporarily (in production, use Redis)
        self._state_store: Dict[str, Dict[str, Any]] = {}
        logger.info("✅ OAuthHandler initialized successfully")

    async def generate_authorization_url(
        self, service: str, user_id: str, redirect_url: Optional[str] = None
    ) -> str:
        """
        Generate OAuth authorization URL for a service

        Args:
            service: Service name (e.g., 'calendly', 'google_calendar')
            user_id: User ID for state tracking
            redirect_url: Optional frontend redirect URL after completion

        Returns:
            Authorization URL for the service
        """
        # Validar que user_id es un UUID válido
        try:
            uuid_obj = uuid.UUID(str(user_id))
        except Exception:
            logger.error(f"❌ user_id recibido no es un UUID válido: {user_id}")
            raise HTTPException(
                status_code=400, detail="user_id debe ser un UUID válido (auth.uid())"
            )

        logger.info(f"🚀 Starting OAuth flow for service: {service}, user: {user_id}")
        logger.debug(f"📋 Redirect URL provided: {redirect_url}")

        oauth_config = get_oauth_config(service)
        if not oauth_config:
            logger.error(f"❌ OAuth config not found for service: {service}")
            raise HTTPException(
                status_code=400, detail=f"OAuth not configured for service: {service}"
            )

        logger.info(f"✅ OAuth config found for {service}")
        logger.debug(
            f"📋 OAuth config: client_id={oauth_config.client_id[:10]}..., scope={oauth_config.scope}"
        )

        # Generate CSRF state token
        state = secrets.token_urlsafe(32)
        logger.debug(f"🔐 Generated state token: {state[:10]}...")

        # Initialize state data
        state_data = {
            "user_id": user_id,
            "service": service,
            "timestamp": datetime.utcnow(),
            "redirect_url": redirect_url,
        }

        # Generate PKCE if required for this service
        pkce_data = None
        if service in get_services_requiring_pkce():
            pkce_data = generate_pkce_pair()
            state_data["code_verifier"] = pkce_data["code_verifier"]
            logger.info(f"🔐 Generated PKCE pair for {service}")
            logger.debug(f"📋 Code challenge: {pkce_data['code_challenge'][:10]}...")

        # Store state with user context
        self._state_store[state] = state_data
        logger.info(f"💾 Stored state for user {user_id}, service {service}")

        # Build authorization URL
        try:
            redirect_uri = build_redirect_uri(service)
            logger.info(f"🔗 Built redirect URI: {redirect_uri}")
        except Exception as e:
            logger.error(f"❌ Failed to build redirect URI for {service}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to build redirect URI: {str(e)}"
            )

        params = {
            "client_id": oauth_config.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state,
        }

        if oauth_config.scope:
            params["scope"] = oauth_config.scope
            logger.debug(f"📋 Added scope: {oauth_config.scope}")

        # Add PKCE parameters if required
        if pkce_data:
            params["code_challenge"] = pkce_data["code_challenge"]
            params["code_challenge_method"] = pkce_data["code_challenge_method"]
            logger.debug(f"📋 Added PKCE parameters for {service}")

        # Add extra parameters if specified
        if oauth_config.extra_params:
            params.update(oauth_config.extra_params)
            logger.debug(f"📋 Added extra params: {oauth_config.extra_params}")

        # Build the URL
        query_string = urllib.parse.urlencode(params)
        authorization_url = f"{oauth_config.authorize_url}?{query_string}"

        logger.info(f"✅ Generated OAuth URL for {service}: {authorization_url}")
        return authorization_url

    async def handle_oauth_callback(
        self, service: str, code: str, state: str, error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle OAuth callback and exchange code for tokens

        Args:
            service: Service name
            code: Authorization code from provider
            state: CSRF state token
            error: Error from OAuth provider

        Returns:
            Result dictionary with success status and user info
        """
        if error:
            logger.error(f"OAuth error from {service}: {error}")
            raise HTTPException(status_code=400, detail=f"OAuth error: {error}")

        # Validate state token
        state_data = self._state_store.get(state)
        if not state_data:
            logger.error(f"Invalid or expired state token: {state}")
            raise HTTPException(
                status_code=400, detail="Invalid or expired state token"
            )

        # Check state expiration (15 minutes)
        if datetime.utcnow() - state_data["timestamp"] > timedelta(minutes=15):
            del self._state_store[state]
            raise HTTPException(status_code=400, detail="State token expired")

        # Validate service matches
        if state_data["service"] != service:
            raise HTTPException(status_code=400, detail="Service mismatch in state")

        # Validar que el user_id en state_data es un UUID válido
        user_id = state_data["user_id"]
        try:
            uuid_obj = uuid.UUID(str(user_id))
        except Exception:
            logger.error(f"❌ user_id en state_data no es un UUID válido: {user_id}")
            raise HTTPException(
                status_code=400, detail="user_id debe ser un UUID válido (auth.uid())"
            )

        try:
            # Exchange code for tokens (passing state_data for PKCE)
            tokens = await self._exchange_code_for_tokens(service, code, state_data)

            # Clean up state after successful token exchange
            del self._state_store[state]

            # Get user profile if available
            user_profile = await self._get_user_profile(service, tokens)

            # Store encrypted tokens in database
            await self._store_tokens(
                user_id=user_id,
                service=service,
                tokens=tokens,
                user_profile=user_profile,
            )

            return {
                "success": True,
                "service": service,
                "user_id": user_id,
                "profile": user_profile,
                "redirect_url": state_data.get("redirect_url"),
            }

        except Exception as e:
            logger.error(f"OAuth callback error for {service}: {e}")
            # Clean up state on error
            if state in self._state_store:
                del self._state_store[state]
            raise HTTPException(
                status_code=500, detail=f"Failed to complete OAuth flow: {str(e)}"
            )

    async def _exchange_code_for_tokens(
        self, service: str, code: str, state_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Exchange authorization code for access tokens"""
        oauth_config = get_oauth_config(service)
        if not oauth_config:
            raise ValueError(f"OAuth config not found for {service}")

        redirect_uri = build_redirect_uri(service)

        token_data = {
            "grant_type": "authorization_code",
            "client_id": oauth_config.client_id,
            "code": code,
            "redirect_uri": redirect_uri,
        }

        # Prepare headers
        headers = {"Accept": "application/json"}

        # Twitter requires Basic Authentication in header instead of client_secret in body
        if service == "twitter_account":
            credentials = f"{oauth_config.client_id}:{oauth_config.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            headers["Authorization"] = f"Basic {encoded_credentials}"
            logger.info(f"🔐 Using Basic Authentication for Twitter token exchange")
        else:
            # For other services, include client_secret in body
            token_data["client_secret"] = oauth_config.client_secret

        # Add PKCE code_verifier if required
        if service in get_services_requiring_pkce() and state_data:
            code_verifier = state_data.get("code_verifier")
            if code_verifier:
                token_data["code_verifier"] = code_verifier
                logger.info(f"🔐 Added code_verifier for {service} token exchange")
            else:
                logger.warning(
                    f"⚠️ PKCE required for {service} but no code_verifier found"
                )

        logger.debug(f"📋 Token exchange data keys: {list(token_data.keys())}")
        logger.debug(f"📋 Request headers: {list(headers.keys())}")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                oauth_config.token_url,
                data=token_data,
                headers=headers,
            )

            if response.status_code != 200:
                logger.error(f"Token exchange failed for {service}: {response.text}")
                logger.error(f"Status code: {response.status_code}")
                raise ValueError(f"Token exchange failed: {response.status_code}")

            tokens = response.json()

            # Add metadata
            tokens["service"] = service
            tokens["obtained_at"] = datetime.utcnow().isoformat()

            # Calculate expiration time if expires_in is provided
            if "expires_in" in tokens:
                expires_at = datetime.utcnow() + timedelta(seconds=tokens["expires_in"])
                tokens["expires_at"] = expires_at.isoformat()

            return tokens

    async def _get_user_profile(
        self, service: str, tokens: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get user profile information from the service"""
        access_token = tokens.get("access_token")
        if not access_token:
            return {}

        profile_urls = {
            "google_calendar": "https://www.googleapis.com/oauth2/v2/userinfo",
            "calendly": "https://api.calendly.com/users/me",
            "pipedrive": "https://api.pipedrive.com/v1/users/me",
            "salesforce_rest_api": "/services/data/v52.0/sobjects/User",
            "twitter_account": "https://api.twitter.com/2/users/me",
        }

        profile_url = profile_urls.get(service)
        if not profile_url:
            return {}

        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {access_token}"}

                # Special handling for Salesforce
                if service == "salesforce_rest_api":
                    instance_url = tokens.get("instance_url", "")
                    if instance_url:
                        profile_url = f"{instance_url}{profile_url}"
                    else:
                        return {}

                response = await client.get(profile_url, headers=headers)

                if response.status_code == 200:
                    profile_data = response.json()

                    # Normalize profile data across services
                    normalized_profile = self._normalize_profile(service, profile_data)
                    return normalized_profile
                else:
                    logger.warning(
                        f"Failed to get profile for {service}: {response.status_code}"
                    )
                    return {}

        except Exception as e:
            logger.warning(f"Error getting profile for {service}: {e}")
            return {}

    def _normalize_profile(
        self, service: str, profile_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Normalize profile data across different services"""
        normalized = {"service": service, "raw_profile": profile_data}

        # Extract common fields based on service
        if service == "google_calendar":
            normalized.update(
                {
                    "email": profile_data.get("email"),
                    "name": profile_data.get("name"),
                    "picture": profile_data.get("picture"),
                    "user_id": profile_data.get("id"),
                }
            )
        elif service == "calendly":
            resource = profile_data.get("resource", {})
            normalized.update(
                {
                    "email": resource.get("email"),
                    "name": resource.get("name"),
                    "user_id": resource.get("uri", "").split("/")[-1],
                }
            )
        elif service == "pipedrive":
            data = profile_data.get("data", {})
            normalized.update(
                {
                    "email": data.get("email"),
                    "name": data.get("name"),
                    "user_id": str(data.get("id")),
                }
            )
        elif service == "twitter_account":
            data = profile_data.get("data", {})
            normalized.update(
                {
                    "username": data.get("username"),
                    "name": data.get("name"),
                    "user_id": data.get("id"),
                }
            )

        return normalized

    async def _store_tokens(
        self,
        user_id: str,
        service: str,
        tokens: Dict[str, Any],
        user_profile: Dict[str, Any],
    ) -> None:
        """Store encrypted tokens in the database"""
        try:
            # Validar que user_id es UUID válido
            try:
                uuid_obj = uuid.UUID(str(user_id))
            except Exception:
                logger.error(
                    f"❌ user_id para guardar en user_accounts no es UUID válido: {user_id}"
                )
                raise Exception(
                    "user_id debe ser UUID válido (auth.uid()) para cumplir RLS"
                )

            # Encrypt the tokens
            encrypted_tokens = encrypt_oauth_tokens(tokens)

            # Prepare account data - ensure user_id is a valid UUID string
            account_data = {
                "user_id": str(user_id),  # Ensure it's a string representation of UUID
                "service": service,
                "account_data": encrypted_tokens,
                "connected": True,
                "connected_at": datetime.utcnow().isoformat(),
                "profile_data": user_profile,
            }

            logger.info(
                f"Guardando en user_accounts con user_id={user_id} (UUID válido)"
            )
            logger.debug(f"Account data keys: {list(account_data.keys())}")

            # Upsert the account using the admin client to bypass RLS
            result = (
                self.supabase_admin.table("user_accounts")
                .upsert(account_data, on_conflict="user_id,service")
                .execute()
            )

            if result.data:
                logger.info(
                    f"Successfully stored OAuth tokens for {service} user {user_id}"
                )
            else:
                logger.error(f"Failed to store tokens for {service}: {result}")
                raise Exception(f"No data returned when storing tokens for {service}")

        except Exception as e:
            logger.error(f"Error storing tokens for {service}: {e}")
            logger.error(f"Account data was: {account_data}")
            raise

    async def refresh_token_if_needed(self, user_id: str, service: str) -> bool:
        """
        Refresh OAuth token if it's expired or about to expire

        Returns:
            True if token was refreshed or is still valid, False if refresh failed
        """
        try:
            # Get current tokens using admin client to bypass RLS
            result = (
                self.supabase_admin.table("user_accounts")
                .select("account_data")
                .eq("user_id", user_id)
                .eq("service", service)
                .execute()
            )

            if not result.data:
                return False

            encrypted_tokens = result.data[0]["account_data"]
            tokens = safe_decrypt(encrypted_tokens)

            # Check if token needs refresh
            if not self._needs_refresh(tokens):
                return True

            # Attempt to refresh
            refresh_token = tokens.get("refresh_token")
            if not refresh_token:
                logger.warning(
                    f"No refresh token available for {service} user {user_id}"
                )
                return False

            new_tokens = await self._refresh_access_token(service, refresh_token)
            if new_tokens:
                # Update stored tokens
                await self._store_tokens(user_id, service, new_tokens, {})
                return True

            return False

        except Exception as e:
            logger.error(f"Error refreshing token for {service}: {e}")
            return False

    def _needs_refresh(self, tokens: Dict[str, Any]) -> bool:
        """Check if token needs to be refreshed"""
        expires_at = tokens.get("expires_at")
        if not expires_at:
            return False

        try:
            expiry_time = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            # Refresh if expires within 5 minutes
            return datetime.utcnow() >= expiry_time - timedelta(minutes=5)
        except Exception:
            return False

    async def _refresh_access_token(
        self, service: str, refresh_token: str
    ) -> Optional[Dict[str, Any]]:
        """Refresh an access token using the refresh token"""
        oauth_config = get_oauth_config(service)
        if not oauth_config:
            return None

        token_data = {
            "grant_type": "refresh_token",
            "client_id": oauth_config.client_id,
            "client_secret": oauth_config.client_secret,
            "refresh_token": refresh_token,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    oauth_config.token_url,
                    data=token_data,
                    headers={"Accept": "application/json"},
                )

                if response.status_code == 200:
                    new_tokens = response.json()

                    # Preserve refresh token if not provided in response
                    if "refresh_token" not in new_tokens:
                        new_tokens["refresh_token"] = refresh_token

                    # Add metadata
                    new_tokens["service"] = service
                    new_tokens["obtained_at"] = datetime.utcnow().isoformat()

                    if "expires_in" in new_tokens:
                        expires_at = datetime.utcnow() + timedelta(
                            seconds=new_tokens["expires_in"]
                        )
                        new_tokens["expires_at"] = expires_at.isoformat()

                    return new_tokens
                else:
                    logger.error(f"Token refresh failed for {service}: {response.text}")
                    return None

        except Exception as e:
            logger.error(f"Error refreshing token for {service}: {e}")
            return None


# Global OAuth handler instance
oauth_handler = OAuthHandler()
