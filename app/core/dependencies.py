"""
Core dependencies for multi-tenant FastAPI application
Following Rule 2.3: Use Dependency Injection for Everything

NOTE: This file is temporarily simplified as we're migrating from SQLAlchemy to Supabase.
Many functions are stubbed out and will be reimplemented with Supabase client.
"""

from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from functools import lru_cache
import logging

# from app.core.config import get_settings  # Commented out - not used in simplified version
from app.models.tenant import Tenant
from app.models.user import User

logger = logging.getLogger(__name__)
security = HTTPBearer()


# Función temporal para evitar errores mientras se migra a Supabase
def get_db():
    """Función temporal para compatibilidad mientras se migra a Supabase"""
    return None


# Función temporal para get_current_tenant
async def get_current_tenant() -> Tenant:
    """Función temporal para compatibilidad mientras se migra a Supabase"""
    return Tenant(
        id="default-tenant",
        name="Default Tenant",
        domain="default.com",
        is_active=True,
        features_enabled=["analytics", "outreach", "scheduling"],
        api_limits={"api_calls_per_minute": 100},
    )


# Función temporal para get_current_user
async def get_current_user() -> User:
    """Función temporal para compatibilidad mientras se migra a Supabase"""
    return User(email="user@default.com", full_name="Default User")


class TenantSecurityContext:
    """
    Security context with tenant and user information
    Following Rule 3.3: Configuration and Customization per Tenant
    """

    def __init__(self, user: User, tenant: Tenant, permissions: list[str]):
        self.user = user
        self.tenant = tenant
        self.permissions = permissions
        self.features_enabled = getattr(tenant, "features_enabled", []) or []
        self.api_limits = getattr(tenant, "api_limits", {}) or {}

    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        return permission in self.permissions or "admin" in self.permissions

    def has_feature(self, feature: str) -> bool:
        """Check if tenant has feature enabled"""
        return feature in self.features_enabled

    def get_api_limit(self, limit_type: str) -> Optional[int]:
        """Get API limit for tenant"""
        return self.api_limits.get(limit_type)


class TenantService:
    """
    Service class for tenant-specific operations
    Following Rule 3.1: Data Isolation by Tenant ID

    NOTE: Temporarily simplified for Supabase migration
    """

    def __init__(self, db=None, tenant: Optional[Tenant] = None):
        self.db = db
        self.tenant = tenant

    async def get_tenant_data(
        self, model_class, filters: Optional[Dict[str, Any]] = None
    ):
        """
        Get data filtered by tenant with automatic isolation
        NOTE: Temporarily returns empty list during Supabase migration
        """
        return []

    async def create_tenant_data(self, model_class, data_dict: Dict[str, Any]):
        """
        Create data with automatic tenant assignment
        NOTE: Temporarily returns mock data during Supabase migration
        """
        if self.tenant:
            data_dict["tenant_id"] = self.tenant.id
        return {"id": "mock-id", **data_dict}

    async def update_tenant_data(
        self, model_class, item_id: str, updates: Dict[str, Any]
    ):
        """
        Update data with tenant isolation check
        NOTE: Temporarily returns mock data during Supabase migration
        """
        return {"id": item_id, **updates}


# ============================================================================
# DEPENDENCY FUNCTIONS (Temporarily simplified)
# ============================================================================


async def get_tenant_from_header(
    x_tenant_id: str = Header(
        "default-tenant", description="Tenant ID for multi-tenancy"
    ),
) -> Tenant:
    """
    Get tenant context from header
    Following Rule 3.1: Data Isolation by Tenant ID

    NOTE: Temporarily returns default tenant during Supabase migration
    """
    return Tenant(
        id=x_tenant_id,
        name="Default Tenant",
        domain="default.com",
        is_active=True,
        features_enabled=["analytics", "outreach", "scheduling"],
        api_limits={"api_calls_per_minute": 100},
    )


async def get_current_security_context(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    tenant: Tenant = Depends(get_tenant_from_header),
) -> TenantSecurityContext:
    """
    Get complete security context with tenant and permissions
    Following Rule 3.2: Shared Resource Pool with Limits

    NOTE: Temporarily simplified during Supabase migration
    """
    # Create mock user for now
    user = User(email="user@default.com", full_name="Default User")

    # Default permissions
    permissions = ["admin", "lead:read", "lead:write"]

    return TenantSecurityContext(user, tenant, permissions)


def get_tenant_service(
    tenant: Tenant = Depends(get_tenant_from_header),
) -> TenantService:
    """
    Get tenant service for data operations
    """
    return TenantService(None, tenant)


def require_permission(permission: str):
    """
    Decorator to require specific permissions
    Following Rule 3.3: Configuration and Customization per Tenant
    """

    def dependency(
        context: TenantSecurityContext = Depends(get_current_security_context),
    ):
        if not context.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required",
            )
        return context

    return dependency


def require_feature(feature: str):
    """
    Decorator to require tenant feature
    """

    def dependency(
        context: TenantSecurityContext = Depends(get_current_security_context),
    ):
        if not context.has_feature(feature):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Feature '{feature}' not available for this tenant",
            )
        return context

    return dependency


# ============================================================================
# RATE LIMITING DEPENDENCIES (Temporarily simplified)
# ============================================================================

# Imports moved to top of file


@lru_cache()
def get_supabase_auth_client():
    """Get Supabase auth client"""
    from app.auth.supabase_auth_client import SupabaseAuthClient

    return SupabaseAuthClient()


async def check_rate_limit(
    limit_type: str,
    requests_per_minute: int,
    context: TenantSecurityContext = Depends(get_current_security_context),
):
    """
    Check rate limits per tenant
    Following Rule 3.2: Shared Resource Pool with Limits

    NOTE: Temporarily disabled during Supabase migration
    """
    # Temporarily always allow requests
    return 1


# ============================================================================
# SPECIALIZED DEPENDENCY FUNCTIONS
# ============================================================================


def get_lead_operations_context():
    """Get context for lead operations with required permissions"""
    return Depends(require_permission("lead:read"))


def get_admin_context():
    """Get context for admin operations"""
    return Depends(require_permission("admin"))


def get_analytics_context():
    """Get context for analytics operations"""
    return Depends(require_feature("analytics"))


async def validate_tenant_resource_access(
    resource_id: str,
    resource_type: str,
    context: TenantSecurityContext = Depends(get_current_security_context),
):
    """
    Validate that a resource belongs to the current tenant

    NOTE: Temporarily simplified during Supabase migration
    """
    # Temporarily always allow access
    return {"id": resource_id, "type": resource_type, "tenant_id": context.tenant.id}
