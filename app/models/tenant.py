"""
Tenant model for multi-tenancy support
Following Rule 3.1: Data Isolation by Tenant ID

NOTE: This file is temporarily simplified as we're using Supabase instead of SQLAlchemy.
These models will be converted to Pydantic schemas in future versions.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid


class Tenant:
    """
    Simplified Tenant class for compatibility.
    In production, this should be replaced with Pydantic schemas for Supabase.
    """

    def __init__(self, **kwargs):
        self.id = kwargs.get("id", str(uuid.uuid4()))
        self.name = kwargs.get("name", "")
        self.domain = kwargs.get("domain", "")
        self.subdomain = kwargs.get("subdomain")
        self.is_active = kwargs.get("is_active", True)
        self.is_premium = kwargs.get("is_premium", False)
        self.plan_type = kwargs.get("plan_type", "basic")
        self.created_at = kwargs.get("created_at", datetime.utcnow())
        self.updated_at = kwargs.get("updated_at")
        self.trial_ends_at = kwargs.get("trial_ends_at")
        self.contact_email = kwargs.get("contact_email")
        self.contact_phone = kwargs.get("contact_phone")
        self.billing_email = kwargs.get("billing_email")
        self.features_enabled = kwargs.get("features_enabled", [])
        self.api_limits = kwargs.get("api_limits", {})
        self.custom_branding = kwargs.get("custom_branding", {})
        self.webhook_urls = kwargs.get("webhook_urls", [])
        self.integration_config = kwargs.get("integration_config", {})
        self.company_size = kwargs.get("company_size")
        self.industry = kwargs.get("industry")
        self.country = kwargs.get("country")
        self.timezone = kwargs.get("timezone", "UTC")
        self.monthly_api_calls = kwargs.get("monthly_api_calls", 0)
        self.storage_used_mb = kwargs.get("storage_used_mb", 0)
        self.description = kwargs.get("description")
        self.notes = kwargs.get("notes")

    def __repr__(self):
        return f"<Tenant(id={self.id}, name={self.name}, domain={self.domain})>"

    @property
    def is_trial(self) -> bool:
        """Check if tenant is in trial period"""
        if not self.trial_ends_at:
            return False
        return datetime.utcnow() < self.trial_ends_at

    @property
    def trial_days_remaining(self) -> Optional[int]:
        """Get remaining trial days"""
        if not self.trial_ends_at:
            return None

        remaining = self.trial_ends_at - datetime.utcnow()
        return max(0, remaining.days)

    def has_feature(self, feature: str) -> bool:
        """Check if tenant has a specific feature enabled"""
        return feature in (self.features_enabled or [])

    def get_api_limit(self, limit_type: str) -> Optional[int]:
        """Get API limit for specific type"""
        if not self.api_limits:
            return None
        return self.api_limits.get(limit_type)

    def to_dict(self) -> Dict[str, Any]:
        """Convert tenant to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "domain": self.domain,
            "subdomain": self.subdomain,
            "is_active": self.is_active,
            "is_premium": self.is_premium,
            "plan_type": self.plan_type,
            "is_trial": self.is_trial,
            "trial_days_remaining": self.trial_days_remaining,
            "features_enabled": self.features_enabled,
            "api_limits": self.api_limits,
            "company_size": self.company_size,
            "industry": self.industry,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class TenantUsage:
    """
    Simplified TenantUsage class for compatibility.
    """

    def __init__(self, **kwargs):
        self.id = kwargs.get("id", str(uuid.uuid4()))
        self.tenant_id = kwargs.get("tenant_id", "")
        self.period_start = kwargs.get("period_start")
        self.period_end = kwargs.get("period_end")
        self.api_calls = kwargs.get("api_calls", 0)
        self.storage_mb = kwargs.get("storage_mb", 0)
        self.users_count = kwargs.get("users_count", 0)
        self.leads_processed = kwargs.get("leads_processed", 0)
        self.integrations_count = kwargs.get("integrations_count", 0)
        self.usage_details = kwargs.get("usage_details", {})
        self.billable_amount = kwargs.get("billable_amount", 0)
        self.billed = kwargs.get("billed", False)
        self.billed_at = kwargs.get("billed_at")
        self.created_at = kwargs.get("created_at", datetime.utcnow())

    def __repr__(self):
        return f"<TenantUsage(id={self.id}, tenant_id={self.tenant_id})>"


class TenantInvitation:
    """
    Simplified TenantInvitation class for compatibility.
    """

    def __init__(self, **kwargs):
        self.id = kwargs.get("id", str(uuid.uuid4()))
        self.tenant_id = kwargs.get("tenant_id", "")
        self.email = kwargs.get("email", "")
        self.invited_by = kwargs.get("invited_by", "")
        self.role = kwargs.get("role", "user")
        self.status = kwargs.get("status", "pending")
        self.token = kwargs.get("token", str(uuid.uuid4()))
        self.created_at = kwargs.get("created_at", datetime.utcnow())
        self.expires_at = kwargs.get("expires_at")
        self.accepted_at = kwargs.get("accepted_at")
        self.invitation_data = kwargs.get("invitation_data", {})

    def __repr__(self):
        return f"<TenantInvitation(id={self.id}, email={self.email})>"

    @property
    def is_expired(self) -> bool:
        """Check if invitation has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def is_pending(self) -> bool:
        """Check if invitation is still pending"""
        return self.status == "pending" and not self.is_expired
