"""
Application configuration using Pydantic Settings
Following FastAPI best practices for configuration management
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field
import os


class Settings(BaseSettings):
    """
    Application settings with environment variable support
    """
    
    # Application
    APP_NAME: str = "PipeWise"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = Field(default=False, description="Debug mode")
    ENVIRONMENT: str = Field(default="development", description="Environment name")
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = Field(..., description="Secret key for signing")
    JWT_SECRET_KEY: str = Field(..., description="JWT secret key")
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="Token expiration in minutes")
    
    # Database
    DATABASE_URL: str = Field(..., description="Database connection URL")
    DATABASE_POOL_SIZE: int = Field(default=10, description="Database pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=20, description="Database max overflow")
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    
    # Celery
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/0", description="Celery broker URL")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/0", description="Celery result backend")
    
    # OpenAI
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key")
    OPENAI_MODEL: str = Field(default="gpt-4o", description="Default OpenAI model")
    
    # Supabase (for legacy compatibility)
    SUPABASE_URL: Optional[str] = Field(default=None, description="Supabase URL")
    SUPABASE_ANON_KEY: Optional[str] = Field(default=None, description="Supabase anonymous key")
    SUPABASE_SERVICE_KEY: Optional[str] = Field(default=None, description="Supabase service key")
    
    # Email Configuration
    SMTP_HOST: Optional[str] = Field(default=None, description="SMTP host")
    SMTP_PORT: int = Field(default=587, description="SMTP port")
    SMTP_USERNAME: Optional[str] = Field(default=None, description="SMTP username")
    SMTP_PASSWORD: Optional[str] = Field(default=None, description="SMTP password")
    SMTP_TLS: bool = Field(default=True, description="SMTP TLS enabled")
    
    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins"
    )
    
    # Security
    BCRYPT_ROUNDS: int = Field(default=12, description="Bcrypt rounds")
    PASSWORD_MIN_LENGTH: int = Field(default=8, description="Minimum password length")
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=100, description="Default rate limit per minute")
    
    # Monitoring
    PROMETHEUS_METRICS_PATH: str = Field(default="/metrics", description="Prometheus metrics path")
    ENABLE_METRICS: bool = Field(default=True, description="Enable Prometheus metrics")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(default="json", description="Logging format (json or text)")
    
    # Multi-tenancy
    DEFAULT_TENANT_FEATURES: List[str] = Field(
        default=[
            "basic_crm",
            "lead_qualification", 
            "email_integration",
            "basic_analytics"
        ],
        description="Default features for new tenants"
    )
    
    PREMIUM_TENANT_FEATURES: List[str] = Field(
        default=[
            "basic_crm",
            "lead_qualification",
            "email_integration", 
            "basic_analytics",
            "advanced_analytics",
            "custom_integrations",
            "priority_support",
            "advanced_automation"
        ],
        description="Features for premium tenants"
    )
    
    # External Integrations
    CALENDLY_API_KEY: Optional[str] = Field(default=None, description="Calendly API key")
    SALESFORCE_CLIENT_ID: Optional[str] = Field(default=None, description="Salesforce client ID")
    SALESFORCE_CLIENT_SECRET: Optional[str] = Field(default=None, description="Salesforce client secret")
    HUBSPOT_API_KEY: Optional[str] = Field(default=None, description="HubSpot API key")
    
    # File Storage
    UPLOAD_MAX_SIZE: int = Field(default=10 * 1024 * 1024, description="Max upload size in bytes")
    UPLOAD_ALLOWED_EXTENSIONS: List[str] = Field(
        default=[".pdf", ".doc", ".docx", ".txt", ".csv"],
        description="Allowed file extensions"
    )
    
    # Background Tasks
    CELERY_TASK_ROUTES: dict = Field(
        default={
            'app.tasks.crm_sync.*': {'queue': 'crm_sync'},
            'app.tasks.analysis.*': {'queue': 'analysis'},
            'app.tasks.notifications.*': {'queue': 'notifications'},
            'app.tasks.reports.*': {'queue': 'reports'},
        },
        description="Celery task routing"
    )
    
    # Development/Testing
    TESTING: bool = Field(default=False, description="Testing mode")
    TEST_DATABASE_URL: Optional[str] = Field(default=None, description="Test database URL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        
    def get_database_url(self) -> str:
        """Get database URL, using test database if in testing mode"""
        if self.TESTING and self.TEST_DATABASE_URL:
            return self.TEST_DATABASE_URL
        return self.DATABASE_URL
    
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.ENVIRONMENT.lower() in ["development", "dev", "local"]
    
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.ENVIRONMENT.lower() in ["production", "prod"]
    
    def get_cors_origins(self) -> List[str]:
        """Get CORS origins, including all origins in development"""
        if self.is_development():
            return ["*"]
        return self.CORS_ORIGINS


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get application settings (singleton pattern)
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def override_settings(**kwargs) -> None:
    """
    Override settings for testing
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    
    for key, value in kwargs.items():
        if hasattr(_settings, key):
            setattr(_settings, key, value)


# Tenant-specific configuration
class TenantConfig:
    """
    Configuration manager for tenant-specific settings
    """
    
    def __init__(self, tenant_id: str, features: List[str], limits: dict):
        self.tenant_id = tenant_id
        self.features = features
        self.limits = limits
    
    def has_feature(self, feature: str) -> bool:
        """Check if tenant has a specific feature"""
        return feature in self.features
    
    def get_limit(self, limit_name: str, default: int = 0) -> int:
        """Get tenant-specific limit"""
        return self.limits.get(limit_name, default)
    
    def get_api_limits(self) -> dict:
        """Get all API limits for tenant"""
        return {
            "requests_per_minute": self.get_limit("requests_per_minute", 100),
            "leads_per_month": self.get_limit("leads_per_month", 1000),
            "integrations_count": self.get_limit("integrations_count", 3),
            "users_count": self.get_limit("users_count", 5),
            "storage_mb": self.get_limit("storage_mb", 100)
        }


def get_tenant_config(tenant_id: str, features: List[str], limits: dict) -> TenantConfig:
    """
    Create tenant configuration
    """
    return TenantConfig(tenant_id, features, limits)


# Environment-specific configurations
class DevelopmentConfig(Settings):
    """Development-specific configuration"""
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    
    class Config:
        env_file = ".env.development"


class ProductionConfig(Settings):
    """Production-specific configuration"""
    DEBUG: bool = False
    LOG_LEVEL: str = "WARNING"
    
    class Config:
        env_file = ".env.production"


class TestingConfig(Settings):
    """Testing-specific configuration"""
    TESTING: bool = True
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite:///./test.db"
    
    class Config:
        env_file = ".env.testing"


def get_config_by_environment(environment: str) -> Settings:
    """
    Get configuration based on environment
    """
    configs = {
        "development": DevelopmentConfig,
        "production": ProductionConfig,
        "testing": TestingConfig,
    }
    
    config_class = configs.get(environment.lower(), Settings)
    return config_class()