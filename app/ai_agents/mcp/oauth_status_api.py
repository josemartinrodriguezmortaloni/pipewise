"""
OAuth Status API

This module provides API endpoints to check the status of user OAuth integrations.
It allows checking integration status, validating permissions, and getting analytics
data for OAuth integrations.

Key Features:
- Check integration status for users
- Validate OAuth permissions for services
- Get analytics data for integrations
- Real-time status updates
- Comprehensive error handling

Following PRD: Task 3.0 - Integrar MCP con Sistema OAuth Existente
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .mcp_server_manager import validate_oauth_tokens_for_service
from .oauth_integration import (
    OAuthProvider,
    MCPServiceType,
    validate_oauth_scopes,
    get_supported_services,
)
from .oauth_analytics_logger import get_oauth_analytics_logger
from .oauth_token_refresh import get_token_refresh_manager

logger = logging.getLogger(__name__)

# Create router for OAuth status endpoints
oauth_status_router = APIRouter(prefix="/oauth-status", tags=["OAuth Status"])


class OAuthIntegrationStatus(BaseModel):
    """OAuth integration status response model"""

    service_name: str
    provider: Optional[str] = None
    is_connected: bool
    is_valid: bool
    expires_at: Optional[datetime] = None
    expires_soon: bool = False
    has_required_scopes: bool = False
    last_used: Optional[datetime] = None
    error_message: Optional[str] = None


class UserOAuthStatusResponse(BaseModel):
    """User OAuth status response model"""

    user_id: str
    integrations: List[OAuthIntegrationStatus]
    total_integrations: int
    connected_integrations: int
    valid_integrations: int
    last_check: datetime


class OAuthAnalyticsResponse(BaseModel):
    """OAuth analytics response model"""

    user_id: str
    period_days: int
    total_events: int
    success_rate: float
    services_used: List[str]
    event_types: Dict[str, int]
    providers: Dict[str, int]
    daily_usage: Dict[str, int]


class SystemOAuthStatusResponse(BaseModel):
    """System OAuth status response model"""

    supported_services: List[Dict[str, str]]
    total_users: int
    active_integrations: int
    system_health: Dict[str, Any]
    last_check: datetime


@oauth_status_router.get("/user/{user_id}", response_model=UserOAuthStatusResponse)
async def get_user_oauth_status(
    user_id: str,
    check_permissions: bool = True,
    refresh_expired: bool = False,
) -> UserOAuthStatusResponse:
    """
    Get OAuth integration status for a specific user.

    Args:
        user_id: User identifier
        check_permissions: Whether to check OAuth permissions
        refresh_expired: Whether to refresh expired tokens

    Returns:
        User OAuth status with integration details
    """
    try:
        # Get supported services
        supported_services = get_supported_services()

        # Get token refresh manager
        refresh_manager = get_token_refresh_manager()

        # Get analytics logger
        analytics_logger = get_oauth_analytics_logger()

        integrations = []

        for service_info in supported_services:
            service_name = service_info["service_name"]
            provider_name = service_info["oauth_provider"]

            try:
                # Check if tokens exist and are valid
                is_connected = await _check_integration_connection(
                    user_id, service_name
                )
                is_valid = (
                    validate_oauth_tokens_for_service(user_id, service_name)
                    if is_connected
                    else False
                )

                # Get token info
                token_info = await _get_token_info(user_id, service_name)

                expires_at = token_info.get("expires_at")
                expires_soon = False

                if expires_at and is_valid:
                    expires_soon = datetime.now() >= (
                        expires_at - timedelta(minutes=10)
                    )

                    # Refresh expired tokens if requested
                    if refresh_expired and expires_soon:
                        refresh_result = await refresh_manager.refresh_mcp_token(
                            user_id, service_name
                        )
                        if refresh_result.success:
                            is_valid = True
                            expires_at = refresh_result.expires_at
                            expires_soon = False

                            # Log refresh success
                            analytics_logger.log_token_refresh(
                                user_id=user_id,
                                service_name=service_name,
                                oauth_provider=_get_oauth_provider_from_name(
                                    provider_name
                                ),
                                success=True,
                            )

                # Check OAuth scopes if requested
                has_required_scopes = False
                if check_permissions and is_valid:
                    oauth_tokens = await _get_oauth_tokens_for_validation(
                        user_id, service_name
                    )
                    if oauth_tokens:
                        service_type = _get_service_type_from_name(service_name)
                        if service_type:
                            has_required_scopes = validate_oauth_scopes(
                                oauth_tokens, service_type
                            )

                # Get last used info
                last_used = await _get_last_used_date(user_id, service_name)

                # Create integration status
                integration_status = OAuthIntegrationStatus(
                    service_name=service_name,
                    provider=provider_name,
                    is_connected=is_connected,
                    is_valid=is_valid,
                    expires_at=expires_at,
                    expires_soon=expires_soon,
                    has_required_scopes=has_required_scopes,
                    last_used=last_used,
                    error_message=None,
                )

                integrations.append(integration_status)

                # Log status check
                analytics_logger.log_token_validation(
                    user_id=user_id,
                    service_name=service_name,
                    oauth_provider=_get_oauth_provider_from_name(provider_name),
                    success=is_valid,
                )

            except Exception as e:
                logger.error(
                    f"❌ Error checking {service_name} status for user {user_id}: {e}"
                )

                # Create error status
                integration_status = OAuthIntegrationStatus(
                    service_name=service_name,
                    provider=provider_name,
                    is_connected=False,
                    is_valid=False,
                    has_required_scopes=False,
                    error_message=str(e),
                )

                integrations.append(integration_status)

                # Log error
                analytics_logger.log_authentication_failure(
                    user_id=user_id,
                    service_name=service_name,
                    oauth_provider=_get_oauth_provider_from_name(provider_name),
                    error_message=str(e),
                )

        # Calculate summary statistics
        connected_integrations = sum(1 for i in integrations if i.is_connected)
        valid_integrations = sum(1 for i in integrations if i.is_valid)

        return UserOAuthStatusResponse(
            user_id=user_id,
            integrations=integrations,
            total_integrations=len(integrations),
            connected_integrations=connected_integrations,
            valid_integrations=valid_integrations,
            last_check=datetime.now(),
        )

    except Exception as e:
        logger.error(f"❌ Error getting OAuth status for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@oauth_status_router.get(
    "/user/{user_id}/analytics", response_model=OAuthAnalyticsResponse
)
async def get_user_oauth_analytics(
    user_id: str,
    days: int = 7,
) -> OAuthAnalyticsResponse:
    """
    Get OAuth analytics for a specific user.

    Args:
        user_id: User identifier
        days: Number of days to look back

    Returns:
        User OAuth analytics data
    """
    try:
        analytics_logger = get_oauth_analytics_logger()

        # Get analytics summary
        analytics_data = analytics_logger.get_analytics_summary(user_id, days)

        return OAuthAnalyticsResponse(
            user_id=user_id,
            period_days=days,
            total_events=analytics_data["total_events"],
            success_rate=analytics_data["success_rate"],
            services_used=analytics_data["services_used"],
            event_types=analytics_data["event_types"],
            providers=analytics_data["providers"],
            daily_usage=analytics_data["daily_usage"],
        )

    except Exception as e:
        logger.error(f"❌ Error getting OAuth analytics for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@oauth_status_router.get("/system", response_model=SystemOAuthStatusResponse)
async def get_system_oauth_status() -> SystemOAuthStatusResponse:
    """
    Get system-wide OAuth status and health information.

    Returns:
        System OAuth status and health metrics
    """
    try:
        # Get supported services
        supported_services = get_supported_services()

        # Get system analytics
        analytics_logger = get_oauth_analytics_logger()
        system_analytics = analytics_logger.get_system_analytics()

        # Get system health info
        system_health = await _get_system_health()

        return SystemOAuthStatusResponse(
            supported_services=supported_services,
            total_users=system_analytics["unique_users"],
            active_integrations=system_analytics["total_events"],
            system_health=system_health,
            last_check=datetime.now(),
        )

    except Exception as e:
        logger.error(f"❌ Error getting system OAuth status: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@oauth_status_router.post("/user/{user_id}/refresh")
async def refresh_user_oauth_tokens(
    user_id: str,
    service_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Refresh OAuth tokens for a user.

    Args:
        user_id: User identifier
        service_name: Specific service to refresh (optional)

    Returns:
        Refresh results
    """
    try:
        refresh_manager = get_token_refresh_manager()

        if service_name:
            # Refresh specific service
            result = await refresh_manager.refresh_mcp_token(user_id, service_name)

            return {
                "service_name": service_name,
                "success": result.success,
                "error_message": result.error_message,
                "expires_at": result.expires_at.isoformat()
                if result.expires_at
                else None,
            }
        else:
            # Refresh all expiring tokens
            results = await refresh_manager.refresh_all_expiring_tokens(user_id)

            return {
                "refreshed_services": len(results),
                "results": {
                    service: {
                        "success": result.success,
                        "error_message": result.error_message,
                        "expires_at": result.expires_at.isoformat()
                        if result.expires_at
                        else None,
                    }
                    for service, result in results.items()
                },
            }

    except Exception as e:
        logger.error(f"❌ Error refreshing OAuth tokens for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@oauth_status_router.get("/user/{user_id}/validate/{service_name}")
async def validate_user_oauth_permissions(
    user_id: str,
    service_name: str,
) -> Dict[str, Any]:
    """
    Validate OAuth permissions for a specific service.

    Args:
        user_id: User identifier
        service_name: Name of the service to validate

    Returns:
        Validation results
    """
    try:
        # Check if service is supported
        supported_services = get_supported_services()
        service_names = [s["service_name"] for s in supported_services]

        if service_name not in service_names:
            raise HTTPException(
                status_code=404, detail=f"Service {service_name} not supported"
            )

        # Validate tokens
        is_valid = validate_oauth_tokens_for_service(user_id, service_name)

        # Check OAuth scopes
        has_required_scopes = False
        scope_details = {}

        if is_valid:
            oauth_tokens = await _get_oauth_tokens_for_validation(user_id, service_name)
            if oauth_tokens:
                service_type = _get_service_type_from_name(service_name)
                if service_type:
                    has_required_scopes = validate_oauth_scopes(
                        oauth_tokens, service_type
                    )
                    scope_details = {
                        "current_scopes": oauth_tokens.scope.split()
                        if oauth_tokens.scope
                        else [],
                        "required_scopes": _get_required_scopes_for_service(
                            service_type
                        ),
                    }

        # Log validation
        analytics_logger = get_oauth_analytics_logger()
        analytics_logger.log_token_validation(
            user_id=user_id,
            service_name=service_name,
            oauth_provider=_get_oauth_provider_from_name(service_name),
            success=is_valid and has_required_scopes,
        )

        return {
            "service_name": service_name,
            "is_valid": is_valid,
            "has_required_scopes": has_required_scopes,
            "scope_details": scope_details,
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error validating OAuth permissions for {service_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# Helper functions
async def _check_integration_connection(user_id: str, service_name: str) -> bool:
    """Check if integration is connected"""
    try:
        from app.supabase.supabase_client import get_supabase_client

        supabase = get_supabase_client()

        response = (
            supabase.table("user_accounts")
            .select("connected")
            .eq("user_id", user_id)
            .eq("service", service_name)
            .single()
            .execute()
        )

        return bool(response.data and response.data.get("connected"))

    except Exception:
        return False


async def _get_token_info(user_id: str, service_name: str) -> Dict[str, Any]:
    """Get token information"""
    try:
        from app.supabase.supabase_client import get_supabase_client

        supabase = get_supabase_client()

        response = (
            supabase.table("user_accounts")
            .select("account_data, created_at, updated_at")
            .eq("user_id", user_id)
            .eq("service", service_name)
            .single()
            .execute()
        )

        if not response.data:
            return {}

        data = response.data
        account_data = data.get("account_data", {})
        expires_at = None

        # Get expires_at from account_data
        if account_data.get("expires_at"):
            expires_at = datetime.fromisoformat(
                account_data["expires_at"].replace("Z", "+00:00")
            )

        return {
            "expires_at": expires_at,
            "created_at": datetime.fromisoformat(
                data["created_at"].replace("Z", "+00:00")
            )
            if data.get("created_at")
            else None,
            "updated_at": datetime.fromisoformat(
                data["updated_at"].replace("Z", "+00:00")
            )
            if data.get("updated_at")
            else None,
        }

    except Exception:
        return {}


async def _get_oauth_tokens_for_validation(user_id: str, service_name: str):
    """Get OAuth tokens for validation"""
    try:
        from .mcp_server_manager import _get_oauth_tokens_from_supabase

        return await _get_oauth_tokens_from_supabase(user_id, service_name)
    except Exception:
        return None


async def _get_last_used_date(user_id: str, service_name: str) -> Optional[datetime]:
    """Get last used date for a service"""
    try:
        from app.supabase.supabase_client import get_supabase_client

        supabase = get_supabase_client()

        response = (
            supabase.table("oauth_analytics")
            .select("timestamp")
            .eq("user_id", user_id)
            .eq("service_name", service_name)
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )

        if response.data:
            return datetime.fromisoformat(response.data[0]["timestamp"])

        return None

    except Exception:
        return None


async def _get_system_health() -> Dict[str, Any]:
    """Get system health information"""
    try:
        from app.supabase.supabase_client import get_supabase_client

        supabase = get_supabase_client()

        # Check database connectivity using user_accounts table
        response = supabase.table("user_accounts").select("id").execute()

        total_integrations = len(response.data) if response.data else 0

        # Check recent activity if analytics table exists
        recent_cutoff = datetime.now() - timedelta(hours=24)
        recent_activity = 0

        try:
            recent_response = (
                supabase.table("oauth_analytics")
                .select("id")
                .gte("timestamp", recent_cutoff.isoformat())
                .execute()
            )
            recent_activity = len(recent_response.data) if recent_response.data else 0
        except Exception:
            # oauth_analytics table may not exist, that's okay
            recent_activity = 0

        return {
            "database_connected": True,
            "total_integrations": total_integrations,
            "recent_activity_24h": recent_activity,
            "last_check": datetime.now().isoformat(),
        }

    except Exception as e:
        return {
            "database_connected": False,
            "error": str(e),
            "last_check": datetime.now().isoformat(),
        }


def _get_oauth_provider_from_name(provider_name: str) -> Optional[OAuthProvider]:
    """Get OAuth provider from name"""
    try:
        return OAuthProvider(provider_name)
    except ValueError:
        return None


def _get_service_type_from_name(service_name: str) -> Optional[MCPServiceType]:
    """Get service type from name"""
    try:
        return MCPServiceType(service_name)
    except ValueError:
        return None


def _get_required_scopes_for_service(service_type: MCPServiceType) -> List[str]:
    """Get required scopes for a service"""
    scope_mapping = {
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
        ],
        MCPServiceType.CALENDLY_V2: [
            "scheduling",
        ],
        MCPServiceType.PIPEDRIVE: [
            "deals:read",
            "deals:write",
        ],
        MCPServiceType.SALESFORCE_REST_API: [
            "api",
        ],
        MCPServiceType.ZOHO_CRM: [
            "ZohoCRM.modules.ALL",
        ],
    }

    return scope_mapping.get(service_type, [])


# Export router for use in main application
def get_oauth_status_router() -> APIRouter:
    """Get the OAuth status router"""
    return oauth_status_router
