"""
Core dependencies for multi-tenant FastAPI application
Following Rule 2.3: Use Dependency Injection for Everything
"""

from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
import logging

from app.core.config import get_settings
from app.models.tenant import Tenant
from app.models.user import User
from app.database import get_db

logger = logging.getLogger(__name__)
security = HTTPBearer()


class TenantSecurityContext:
    """
    Security context with tenant and user information
    Following Rule 3.3: Configuration and Customization per Tenant
    """
    
    def __init__(self, user: User, tenant: Tenant, permissions: list[str]):
        self.user = user
        self.tenant = tenant
        self.permissions = permissions
        self.features_enabled = tenant.features_enabled or []
        self.api_limits = tenant.api_limits or {}
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        return permission in self.permissions or 'admin' in self.permissions
    
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
    """
    
    def __init__(self, db: Session, tenant: Tenant):
        self.db = db
        self.tenant = tenant
    
    async def get_tenant_data(self, model_class, filters: Dict[str, Any] = None):
        """
        Get data filtered by tenant with automatic isolation
        """
        query = self.db.query(model_class).filter(
            model_class.tenant_id == self.tenant.id
        )
        
        if filters:
            for key, value in filters.items():
                if hasattr(model_class, key):
                    query = query.filter(getattr(model_class, key) == value)
        
        return query.all()
    
    async def create_tenant_data(self, model_class, data_dict: Dict[str, Any]):
        """
        Create data with automatic tenant assignment
        """
        data_dict['tenant_id'] = self.tenant.id
        instance = model_class(**data_dict)
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        return instance
    
    async def update_tenant_data(self, model_class, item_id: str, updates: Dict[str, Any]):
        """
        Update data with tenant isolation check
        """
        item = self.db.query(model_class).filter(
            model_class.id == item_id,
            model_class.tenant_id == self.tenant.id
        ).first()
        
        if not item:
            raise HTTPException(
                status_code=404,
                detail="Item not found or not accessible"
            )
        
        for key, value in updates.items():
            if hasattr(item, key):
                setattr(item, key, value)
        
        self.db.commit()
        self.db.refresh(item)
        return item


# ============================================================================
# DEPENDENCY FUNCTIONS
# ============================================================================

async def get_tenant_from_header(
    x_tenant_id: str = Header(..., description="Tenant ID for multi-tenancy"),
    db: Session = Depends(get_db)
) -> Tenant:
    """
    Get tenant context from header
    Following Rule 3.1: Data Isolation by Tenant ID
    """
    if not x_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-ID header is required"
        )
    
    tenant = db.query(Tenant).filter(Tenant.id == x_tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant is inactive"
        )
    
    return tenant


async def get_current_security_context(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    tenant: Tenant = Depends(get_tenant_from_header),
    db: Session = Depends(get_db)
) -> TenantSecurityContext:
    """
    Get complete security context with tenant and permissions
    Following Rule 3.2: Shared Resource Pool with Limits
    """
    settings = get_settings()
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        user_email: str = payload.get("sub")
        token_tenant_id: str = payload.get("tenant_id")
        
        if user_email is None or token_tenant_id is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
    
    # Get user from database
    user = db.query(User).filter(User.email == user_email).first()
    if user is None:
        raise credentials_exception
    
    # Verify user belongs to the requested tenant
    if user.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to requested tenant"
        )
    
    # Verify token tenant matches requested tenant
    if token_tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token tenant does not match requested tenant"
        )
    
    # Get user permissions
    permissions = [role.name for role in user.roles] if user.roles else []
    
    return TenantSecurityContext(user, tenant, permissions)


def get_tenant_service(
    tenant: Tenant = Depends(get_tenant_from_header),
    db: Session = Depends(get_db)
) -> TenantService:
    """
    Get tenant service for data operations
    """
    return TenantService(db, tenant)


def require_permission(permission: str):
    """
    Decorator to require specific permissions
    Following Rule 3.3: Configuration and Customization per Tenant
    """
    def dependency(context: TenantSecurityContext = Depends(get_current_security_context)):
        if not context.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        return context
    return dependency


def require_feature(feature: str):
    """
    Decorator to require tenant feature
    """
    def dependency(context: TenantSecurityContext = Depends(get_current_security_context)):
        if not context.has_feature(feature):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Feature '{feature}' not available for this tenant"
            )
        return context
    return dependency


# ============================================================================
# RATE LIMITING DEPENDENCIES
# ============================================================================

from functools import lru_cache
from datetime import datetime, timedelta
import redis

@lru_cache()
def get_redis_client():
    """Get Redis client for rate limiting"""
    settings = get_settings()
    return redis.from_url(settings.REDIS_URL)


async def check_rate_limit(
    limit_type: str,
    requests_per_minute: int,
    context: TenantSecurityContext = Depends(get_current_security_context)
):
    """
    Check rate limits per tenant
    Following Rule 3.2: Shared Resource Pool with Limits
    """
    redis_client = get_redis_client()
    
    # Get tenant-specific limit if configured
    tenant_limit = context.get_api_limit(f"{limit_type}_per_minute")
    if tenant_limit:
        requests_per_minute = min(requests_per_minute, tenant_limit)
    
    # Create rate limit key
    key = f"rate_limit:{context.tenant.id}:{limit_type}:{datetime.now().strftime('%Y-%m-%d-%H-%M')}"
    
    # Check current count
    current_count = redis_client.incr(key)
    
    # Set expiration on first request
    if current_count == 1:
        redis_client.expire(key, 60)  # 1 minute
    
    # Check if limit exceeded
    if current_count > requests_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded for {limit_type}. Limit: {requests_per_minute}/minute"
        )
    
    return current_count


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
    db: Session = Depends(get_db)
):
    """
    Validate that a resource belongs to the current tenant
    """
    # This would be implemented based on your specific models
    # Example for leads:
    if resource_type == "lead":
        from app.models.lead import Lead
        lead = db.query(Lead).filter(
            Lead.id == resource_id,
            Lead.tenant_id == context.tenant.id
        ).first()
        
        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resource not found or not accessible"
            )
        
        return lead
    
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unknown resource type"
    )