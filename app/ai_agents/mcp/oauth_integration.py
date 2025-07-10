"""
OAuth Integration for MCP

This module handles the integration between OAuth tokens and MCP credentials.
It provides functions to map OAuth tokens to MCP-compatible credentials and
manages token validation, refresh, and formatting for different services.

Key Components:
- OAuth token to MCP credential mapping
- Service-specific credential formatting
- Token validation and refresh logic
- Integration with Supabase OAuth storage
- Support for multiple OAuth providers

Following PRD: Task 3.0 - Integrar MCP con Sistema OAuth Existente
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from .error_handler import (
    MCPAuthenticationError,
    MCPConfigurationError,
    MCPValidationError,
    get_error_handler,
)
from .retry_handler import retry_mcp_operation

logger = logging.getLogger(__name__)


class OAuthProvider(Enum):
    """Supported OAuth providers for MCP integration"""

    GOOGLE = "google"
    TWITTER = "twitter"
    MICROSOFT = "microsoft"
    SALESFORCE = "salesforce"
    PIPEDRIVE = "pipedrive"
    ZOHO = "zoho"
    SENDGRID = "sendgrid"
    CALENDLY = "calendly"


class MCPServiceType(Enum):
    """MCP service types with their OAuth requirements"""

    GOOGLE_CALENDAR = "google_calendar"
    TWITTER = "twitter"
    SENDGRID = "sendgrid"
    CALENDLY_V2 = "calendly_v2"
    PIPEDRIVE = "pipedrive"
    SALESFORCE_REST_API = "salesforce_rest_api"
    ZOHO_CRM = "zoho_crm"


@dataclass
class OAuthTokens:
    """OAuth token container with metadata"""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_at: Optional[datetime] = None
    scope: Optional[str] = None
    provider: Optional[OAuthProvider] = None
    user_id: Optional[str] = None
    service_account_id: Optional[str] = None  # For service-specific IDs

    def is_expired(self) -> bool:
        """Check if token is expired"""
        if not self.expires_at:
            return False
        return datetime.now() >= self.expires_at

    def expires_soon(self, minutes: int = 10) -> bool:
        """Check if token expires within specified minutes"""
        if not self.expires_at:
            return False
        return datetime.now() >= (self.expires_at - timedelta(minutes=minutes))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization"""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "scope": self.scope,
            "provider": self.provider.value if self.provider else None,
            "user_id": self.user_id,
            "service_account_id": self.service_account_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OAuthTokens":
        """Create from dictionary"""
        expires_at = None
        if data.get("expires_at"):
            try:
                expires_at = datetime.fromisoformat(data["expires_at"])
            except ValueError:
                logger.warning(f"Invalid expires_at format: {data.get('expires_at')}")

        provider = None
        if data.get("provider"):
            try:
                provider = OAuthProvider(data["provider"])
            except ValueError:
                logger.warning(f"Unknown OAuth provider: {data.get('provider')}")

        return cls(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            token_type=data.get("token_type", "Bearer"),
            expires_at=expires_at,
            scope=data.get("scope"),
            provider=provider,
            user_id=data.get("user_id"),
            service_account_id=data.get("service_account_id"),
        )


@dataclass
class MCPCredentials:
    """MCP-formatted credentials for service access"""

    service_name: str
    headers: Dict[str, str]
    auth_type: str = "bearer"
    additional_config: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None
    user_id: Optional[str] = None

    def is_valid(self) -> bool:
        """Check if credentials are still valid"""
        if self.expires_at and datetime.now() >= self.expires_at:
            return False
        return bool(self.headers.get("Authorization"))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MCP server configuration"""
        return {
            "service_name": self.service_name,
            "headers": self.headers,
            "auth_type": self.auth_type,
            "additional_config": self.additional_config or {},
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "user_id": self.user_id,
        }


class OAuthToMCPMapper:
    """
    Maps OAuth tokens to MCP-compatible credentials for different services.

    Each service has specific requirements for how OAuth tokens should be
    formatted and presented to the MCP server.
    """

    # Service-specific OAuth provider mapping
    SERVICE_PROVIDER_MAPPING = {
        MCPServiceType.GOOGLE_CALENDAR: OAuthProvider.GOOGLE,
        MCPServiceType.TWITTER: OAuthProvider.TWITTER,
        MCPServiceType.SENDGRID: OAuthProvider.SENDGRID,
        MCPServiceType.CALENDLY_V2: OAuthProvider.CALENDLY,
        MCPServiceType.PIPEDRIVE: OAuthProvider.PIPEDRIVE,
        MCPServiceType.SALESFORCE_REST_API: OAuthProvider.SALESFORCE,
        MCPServiceType.ZOHO_CRM: OAuthProvider.ZOHO,
    }

    def __init__(self):
        self.error_handler = get_error_handler()

    @retry_mcp_operation(max_attempts=2, service_name="oauth_mapper", log_attempts=True)
    def map_oauth_to_mcp_credentials(
        self,
        oauth_tokens: OAuthTokens,
        service_type: MCPServiceType,
        user_id: str,
    ) -> MCPCredentials:
        """
        Map OAuth tokens to MCP credentials for a specific service.

        Args:
            oauth_tokens: OAuth tokens from provider
            service_type: Target MCP service type
            user_id: User identifier

        Returns:
            MCPCredentials: Formatted credentials for MCP server

        Raises:
            MCPAuthenticationError: If token validation fails
            MCPConfigurationError: If service mapping is invalid
        """
        try:
            # Validate inputs
            self._validate_oauth_tokens(oauth_tokens)
            self._validate_service_compatibility(oauth_tokens, service_type)

            # Map based on service type
            if service_type == MCPServiceType.GOOGLE_CALENDAR:
                return self._map_google_calendar_credentials(oauth_tokens, user_id)
            elif service_type == MCPServiceType.TWITTER:
                return self._map_twitter_credentials(oauth_tokens, user_id)
            elif service_type == MCPServiceType.SENDGRID:
                return self._map_sendgrid_credentials(oauth_tokens, user_id)
            elif service_type == MCPServiceType.CALENDLY_V2:
                return self._map_calendly_credentials(oauth_tokens, user_id)
            elif service_type == MCPServiceType.PIPEDRIVE:
                return self._map_pipedrive_credentials(oauth_tokens, user_id)
            elif service_type == MCPServiceType.SALESFORCE_REST_API:
                return self._map_salesforce_credentials(oauth_tokens, user_id)
            elif service_type == MCPServiceType.ZOHO_CRM:
                return self._map_zoho_credentials(oauth_tokens, user_id)
            else:
                raise MCPConfigurationError(
                    service_name=service_type.value,
                    config_key="service_mapping",
                    message=f"Unsupported service type: {service_type.value}",
                    context={"supported_services": list(MCPServiceType)},
                )

        except Exception as raw_error:
            if isinstance(raw_error, (MCPAuthenticationError, MCPConfigurationError)):
                raise

            mcp_error = self.error_handler.handle_error(
                raw_error,
                service_name=service_type.value,
                operation="map_oauth_credentials",
                context={
                    "user_id": user_id,
                    "oauth_provider": oauth_tokens.provider.value
                    if oauth_tokens.provider
                    else None,
                    "has_refresh_token": bool(oauth_tokens.refresh_token),
                },
            )
            raise mcp_error

    def _validate_oauth_tokens(self, oauth_tokens: OAuthTokens) -> None:
        """Validate OAuth tokens"""
        if not oauth_tokens.access_token:
            raise MCPAuthenticationError(
                service_name="oauth_validation",
                message="Access token is required",
                context={"token_type": oauth_tokens.token_type},
            )

        if oauth_tokens.is_expired():
            raise MCPAuthenticationError(
                service_name="oauth_validation",
                message="OAuth token has expired",
                context={
                    "expires_at": oauth_tokens.expires_at.isoformat()
                    if oauth_tokens.expires_at
                    else None,
                    "has_refresh_token": bool(oauth_tokens.refresh_token),
                },
            )

    def _validate_service_compatibility(
        self, oauth_tokens: OAuthTokens, service_type: MCPServiceType
    ) -> None:
        """Validate that OAuth provider matches service requirements"""
        expected_provider = self.SERVICE_PROVIDER_MAPPING.get(service_type)

        if not expected_provider:
            raise MCPConfigurationError(
                service_name=service_type.value,
                config_key="oauth_provider",
                message=f"No OAuth provider defined for service: {service_type.value}",
                context={"service_type": service_type.value},
            )

        if oauth_tokens.provider != expected_provider:
            raise MCPValidationError(
                service_name=service_type.value,
                field="oauth_provider",
                message=f"OAuth provider mismatch. Expected: {expected_provider.value}, Got: {oauth_tokens.provider.value if oauth_tokens.provider else 'None'}",
                context={
                    "expected": expected_provider.value,
                    "actual": oauth_tokens.provider.value
                    if oauth_tokens.provider
                    else None,
                },
            )

    def _map_google_calendar_credentials(
        self, oauth_tokens: OAuthTokens, user_id: str
    ) -> MCPCredentials:
        """Map Google OAuth tokens to Google Calendar MCP credentials"""
        return MCPCredentials(
            service_name="google_calendar",
            headers={
                "Authorization": f"Bearer {oauth_tokens.access_token}",
                "Content-Type": "application/json",
                "x-user-id": user_id,
            },
            auth_type="oauth2",
            additional_config={
                "scope": oauth_tokens.scope
                or "https://www.googleapis.com/auth/calendar",
                "refresh_token": oauth_tokens.refresh_token,
                "calendar_api_version": "v3",
            },
            expires_at=oauth_tokens.expires_at,
            user_id=user_id,
        )

    def _map_twitter_credentials(
        self, oauth_tokens: OAuthTokens, user_id: str
    ) -> MCPCredentials:
        """Map Twitter OAuth tokens to Twitter MCP credentials"""
        return MCPCredentials(
            service_name="twitter",
            headers={
                "Authorization": f"Bearer {oauth_tokens.access_token}",
                "Content-Type": "application/json",
                "x-user-id": user_id,
            },
            auth_type="oauth2",
            additional_config={
                "api_version": "2.0",
                "user_context": True,
                "account_id": oauth_tokens.service_account_id,
            },
            expires_at=oauth_tokens.expires_at,
            user_id=user_id,
        )

    def _map_sendgrid_credentials(
        self, oauth_tokens: OAuthTokens, user_id: str
    ) -> MCPCredentials:
        """Map SendGrid OAuth tokens to SendGrid MCP credentials"""
        return MCPCredentials(
            service_name="sendgrid",
            headers={
                "Authorization": f"Bearer {oauth_tokens.access_token}",
                "Content-Type": "application/json",
                "x-user-id": user_id,
            },
            auth_type="oauth2",
            additional_config={
                "api_version": "v3",
                "sender_verification": True,
            },
            expires_at=oauth_tokens.expires_at,
            user_id=user_id,
        )

    def _map_calendly_credentials(
        self, oauth_tokens: OAuthTokens, user_id: str
    ) -> MCPCredentials:
        """Map Calendly OAuth tokens to Calendly MCP credentials"""
        return MCPCredentials(
            service_name="calendly_v2",
            headers={
                "Authorization": f"Bearer {oauth_tokens.access_token}",
                "Content-Type": "application/json",
                "x-user-id": user_id,
            },
            auth_type="oauth2",
            additional_config={
                "api_version": "v2",
                "organization_uri": oauth_tokens.service_account_id,  # Calendly organization URI
            },
            expires_at=oauth_tokens.expires_at,
            user_id=user_id,
        )

    def _map_pipedrive_credentials(
        self, oauth_tokens: OAuthTokens, user_id: str
    ) -> MCPCredentials:
        """Map Pipedrive OAuth tokens to Pipedrive MCP credentials"""
        return MCPCredentials(
            service_name="pipedrive",
            headers={
                "Authorization": f"Bearer {oauth_tokens.access_token}",
                "Content-Type": "application/json",
                "x-user-id": user_id,
            },
            auth_type="oauth2",
            additional_config={
                "company_domain": oauth_tokens.service_account_id,  # Pipedrive company domain
                "api_version": "v1",
            },
            expires_at=oauth_tokens.expires_at,
            user_id=user_id,
        )

    def _map_salesforce_credentials(
        self, oauth_tokens: OAuthTokens, user_id: str
    ) -> MCPCredentials:
        """Map Salesforce OAuth tokens to Salesforce MCP credentials"""
        return MCPCredentials(
            service_name="salesforce_rest_api",
            headers={
                "Authorization": f"Bearer {oauth_tokens.access_token}",
                "Content-Type": "application/json",
                "x-user-id": user_id,
            },
            auth_type="oauth2",
            additional_config={
                "instance_url": oauth_tokens.service_account_id,  # Salesforce instance URL
                "api_version": "v60.0",
                "sobject_api": True,
            },
            expires_at=oauth_tokens.expires_at,
            user_id=user_id,
        )

    def _map_zoho_credentials(
        self, oauth_tokens: OAuthTokens, user_id: str
    ) -> MCPCredentials:
        """Map Zoho OAuth tokens to Zoho CRM MCP credentials"""
        return MCPCredentials(
            service_name="zoho_crm",
            headers={
                "Authorization": f"Zoho-oauthtoken {oauth_tokens.access_token}",
                "Content-Type": "application/json",
                "x-user-id": user_id,
            },
            auth_type="oauth2",
            additional_config={
                "api_domain": oauth_tokens.service_account_id
                or "https://www.zohoapis.com",
                "api_version": "v2",
                "org_id": None,  # Will be set from token response
            },
            expires_at=oauth_tokens.expires_at,
            user_id=user_id,
        )


def get_mcp_credentials_for_service(
    oauth_tokens: OAuthTokens,
    service_name: str,
    user_id: str,
) -> MCPCredentials:
    """
    Convenience function to get MCP credentials for a service by name.

    Args:
        oauth_tokens: OAuth tokens from provider
        service_name: Name of the MCP service
        user_id: User identifier

    Returns:
        MCPCredentials: Formatted credentials for MCP server

    Raises:
        MCPConfigurationError: If service name is invalid
    """
    # Map service name to service type
    service_mapping = {
        "google_calendar": MCPServiceType.GOOGLE_CALENDAR,
        "twitter": MCPServiceType.TWITTER,
        "sendgrid": MCPServiceType.SENDGRID,
        "calendly_v2": MCPServiceType.CALENDLY_V2,
        "pipedrive": MCPServiceType.PIPEDRIVE,
        "salesforce_rest_api": MCPServiceType.SALESFORCE_REST_API,
        "zoho_crm": MCPServiceType.ZOHO_CRM,
    }

    service_type = service_mapping.get(service_name)
    if not service_type:
        raise MCPConfigurationError(
            service_name=service_name,
            config_key="service_name",
            message=f"Unknown service name: {service_name}",
            context={"supported_services": list(service_mapping.keys())},
        )

    mapper = OAuthToMCPMapper()
    return mapper.map_oauth_to_mcp_credentials(oauth_tokens, service_type, user_id)


def validate_oauth_scopes(
    oauth_tokens: OAuthTokens,
    service_type: MCPServiceType,
) -> bool:
    """
    Validate that OAuth tokens have required scopes for the service.

    Args:
        oauth_tokens: OAuth tokens to validate
        service_type: Target service type

    Returns:
        bool: True if scopes are sufficient, False otherwise
    """
    if not oauth_tokens.scope:
        logger.warning(f"No scope information available for {service_type.value}")
        return True  # Assume valid if no scope info

    # Define required scopes for each service
    required_scopes = {
        MCPServiceType.GOOGLE_CALENDAR: [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/calendar.events",
        ],
        MCPServiceType.TWITTER: [
            "tweet.read",
            "tweet.write",
            "users.read",
        ],
        MCPServiceType.SENDGRID: [
            "mail.send",
            "mail.batch",
        ],
        MCPServiceType.CALENDLY_V2: [
            "scheduling",
            "event_types",
        ],
        MCPServiceType.PIPEDRIVE: [
            "deals:read",
            "deals:write",
            "persons:read",
            "persons:write",
        ],
        MCPServiceType.SALESFORCE_REST_API: [
            "api",
            "refresh_token",
        ],
        MCPServiceType.ZOHO_CRM: [
            "ZohoCRM.modules.ALL",
            "ZohoCRM.users.READ",
        ],
    }

    service_required_scopes = required_scopes.get(service_type, [])
    if not service_required_scopes:
        return True  # No specific requirements

    # Check if any required scope is present
    token_scopes = oauth_tokens.scope.split() if oauth_tokens.scope else []

    for required_scope in service_required_scopes:
        if any(required_scope in scope for scope in token_scopes):
            return True

    logger.warning(
        f"OAuth token missing required scopes for {service_type.value}. "
        f"Required: {service_required_scopes}, Available: {token_scopes}"
    )
    return False


def create_demo_oauth_tokens(
    provider: OAuthProvider,
    user_id: str,
    service_account_id: Optional[str] = None,
) -> OAuthTokens:
    """
    Create demo OAuth tokens for development/testing purposes.

    Args:
        provider: OAuth provider
        user_id: User identifier
        service_account_id: Service-specific account ID

    Returns:
        OAuthTokens: Demo tokens for testing
    """
    return OAuthTokens(
        access_token=f"demo_token_{provider.value}_{user_id}",
        refresh_token=f"demo_refresh_{provider.value}_{user_id}",
        token_type="Bearer",
        expires_at=datetime.now() + timedelta(hours=1),
        scope=_get_demo_scope_for_provider(provider),
        provider=provider,
        user_id=user_id,
        service_account_id=service_account_id or f"demo_account_{provider.value}",
    )


def _get_demo_scope_for_provider(provider: OAuthProvider) -> str:
    """Get demo scope for OAuth provider"""
    demo_scopes = {
        OAuthProvider.GOOGLE: "https://www.googleapis.com/auth/calendar",
        OAuthProvider.TWITTER: "tweet.read tweet.write users.read",
        OAuthProvider.SENDGRID: "mail.send mail.batch",
        OAuthProvider.CALENDLY: "scheduling event_types",
        OAuthProvider.PIPEDRIVE: "deals:read deals:write persons:read persons:write",
        OAuthProvider.SALESFORCE: "api refresh_token",
        OAuthProvider.ZOHO: "ZohoCRM.modules.ALL ZohoCRM.users.READ",
    }
    return demo_scopes.get(provider, "read write")


def get_supported_services() -> List[Dict[str, str]]:
    """
    Get list of supported MCP services with their OAuth providers.

    Returns:
        List of service information dictionaries
    """
    return [
        {
            "service_name": service.value,
            "oauth_provider": provider.value,
            "description": _get_service_description(service),
        }
        for service, provider in OAuthToMCPMapper.SERVICE_PROVIDER_MAPPING.items()
    ]


def _get_service_description(service: MCPServiceType) -> str:
    """Get description for service type"""
    descriptions = {
        MCPServiceType.GOOGLE_CALENDAR: "Google Calendar integration for scheduling and event management",
        MCPServiceType.TWITTER: "Twitter integration for social media posting and engagement",
        MCPServiceType.SENDGRID: "SendGrid integration for email marketing and transactional emails",
        MCPServiceType.CALENDLY_V2: "Calendly integration for appointment scheduling",
        MCPServiceType.PIPEDRIVE: "Pipedrive CRM integration for sales pipeline management",
        MCPServiceType.SALESFORCE_REST_API: "Salesforce CRM integration for enterprise sales management",
        MCPServiceType.ZOHO_CRM: "Zoho CRM integration for customer relationship management",
    }
    return descriptions.get(service, f"Integration for {service.value}")
