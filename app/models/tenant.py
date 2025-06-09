"""
Tenant model for multi-tenancy support
Following Rule 3.1: Data Isolation by Tenant ID
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, JSON, Integer, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


class Tenant(Base):
    """
    Tenant model for B2B SaaS multi-tenancy
    """
    __tablename__ = "tenants"
    
    # Primary identification
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    domain = Column(String(255), unique=True, nullable=False, index=True)
    subdomain = Column(String(100), unique=True, nullable=True, index=True)
    
    # Status and metadata
    is_active = Column(Boolean, default=True, nullable=False)
    is_premium = Column(Boolean, default=False, nullable=False)
    plan_type = Column(String(50), default="basic", nullable=False)  # basic, premium, enterprise
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)
    
    # Contact information
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    billing_email = Column(String(255), nullable=True)
    
    # Configuration - Following Rule 3.3: Configuration and Customization per Tenant
    features_enabled = Column(JSON, default=list, nullable=False)
    api_limits = Column(JSON, default=dict, nullable=False)
    custom_branding = Column(JSON, default=dict, nullable=False)
    webhook_urls = Column(JSON, default=list, nullable=False)
    integration_config = Column(JSON, default=dict, nullable=False)
    
    # Business information
    company_size = Column(String(50), nullable=True)  # 1-10, 11-50, 51-200, 201-1000, 1000+
    industry = Column(String(100), nullable=True)
    country = Column(String(2), nullable=True)  # ISO country code
    timezone = Column(String(50), default="UTC", nullable=False)
    
    # Usage tracking
    monthly_api_calls = Column(Integer, default=0, nullable=False)
    storage_used_mb = Column(Integer, default=0, nullable=False)
    
    # Notes and description
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    leads = relationship("Lead", back_populates="tenant", cascade="all, delete-orphan")
    integrations = relationship("Integration", back_populates="tenant", cascade="all, delete-orphan")
    
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
    
    def get_feature_config(self, feature: str) -> Dict[str, Any]:
        """Get configuration for a specific feature"""
        if not self.integration_config:
            return {}
        return self.integration_config.get(feature, {})
    
    def update_usage_stats(self, api_calls_increment: int = 0, storage_increment_mb: int = 0):
        """Update usage statistics"""
        self.monthly_api_calls += api_calls_increment
        self.storage_used_mb += storage_increment_mb
    
    def reset_monthly_usage(self):
        """Reset monthly usage counters"""
        self.monthly_api_calls = 0
    
    def is_over_limit(self, limit_type: str) -> bool:
        """Check if tenant is over a specific limit"""
        limit = self.get_api_limit(limit_type)
        if not limit:
            return False
        
        if limit_type == "api_calls_per_month":
            return self.monthly_api_calls >= limit
        elif limit_type == "storage_mb":
            return self.storage_used_mb >= limit
        
        return False
    
    def get_webhook_urls(self, event_type: str = None) -> List[str]:
        """Get webhook URLs for specific event type or all"""
        if not self.webhook_urls:
            return []
        
        if event_type:
            # Filter by event type if specified
            return [
                url for webhook in self.webhook_urls 
                for url in webhook.get("urls", [])
                if event_type in webhook.get("events", [])
            ]
        
        # Return all URLs
        return [
            url for webhook in self.webhook_urls
            for url in webhook.get("urls", [])
        ]
    
    def add_webhook_url(self, url: str, events: List[str], description: str = ""):
        """Add a webhook URL for specific events"""
        if not self.webhook_urls:
            self.webhook_urls = []
        
        webhook = {
            "url": url,
            "events": events,
            "description": description,
            "created_at": datetime.utcnow().isoformat(),
            "active": True
        }
        
        self.webhook_urls.append(webhook)
    
    def get_branding_config(self) -> Dict[str, Any]:
        """Get custom branding configuration"""
        default_branding = {
            "primary_color": "#3B82F6",
            "secondary_color": "#10B981", 
            "logo_url": None,
            "company_name": self.name,
            "support_email": self.contact_email,
            "custom_css": None
        }
        
        if not self.custom_branding:
            return default_branding
        
        return {**default_branding, **self.custom_branding}
    
    def update_branding(self, branding_config: Dict[str, Any]):
        """Update custom branding configuration"""
        if not self.custom_branding:
            self.custom_branding = {}
        
        self.custom_branding.update(branding_config)
    
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
            "country": self.country,
            "timezone": self.timezone,
            "contact_email": self.contact_email,
            "branding": self.get_branding_config(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class TenantUsage(Base):
    """
    Tenant usage tracking for billing and limits
    """
    __tablename__ = "tenant_usage"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False, index=True)
    
    # Usage period
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    
    # Usage metrics
    api_calls = Column(Integer, default=0, nullable=False)
    storage_mb = Column(Integer, default=0, nullable=False)
    users_count = Column(Integer, default=0, nullable=False)
    leads_processed = Column(Integer, default=0, nullable=False)
    integrations_count = Column(Integer, default=0, nullable=False)
    
    # Detailed usage breakdown
    usage_details = Column(JSON, default=dict, nullable=False)
    
    # Billing information
    billable_amount = Column(Integer, default=0, nullable=False)  # Amount in cents
    billed = Column(Boolean, default=False, nullable=False)
    billed_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<TenantUsage(tenant_id={self.tenant_id}, period_start={self.period_start})>"


class TenantInvitation(Base):
    """
    Tenant invitations for user onboarding
    """
    __tablename__ = "tenant_invitations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False, index=True)
    
    # Invitation details
    email = Column(String(255), nullable=False, index=True)
    invited_by = Column(String, nullable=False)  # User ID who sent invitation
    role = Column(String(50), default="user", nullable=False)
    
    # Status
    status = Column(String(20), default="pending", nullable=False)  # pending, accepted, expired
    token = Column(String(255), unique=True, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Additional data
    invitation_data = Column(JSON, default=dict, nullable=False)
    
    def __repr__(self):
        return f"<TenantInvitation(email={self.email}, tenant_id={self.tenant_id}, status={self.status})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if invitation is expired"""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_pending(self) -> bool:
        """Check if invitation is still pending"""
        return self.status == "pending" and not self.is_expired