"""
Application configuration using Pydantic Settings
Following FastAPI best practices for configuration management
"""

from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


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
    SECRET_KEY: str = Field(
        default="dev-secret-key-change-in-production",
        description="Secret key for signing",
    )
    JWT_SECRET_KEY: str = Field(
        default="dev-jwt-secret-change-in-production", description="JWT secret key"
    )
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, description="Token expiration in minutes"
    )

    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///./pipewise.db", description="Database connection URL"
    )
    DATABASE_POOL_SIZE: int = Field(default=10, description="Database pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=20, description="Database max overflow")

    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )

    # Celery
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/0", description="Celery broker URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/0", description="Celery result backend"
    )

    # OpenAI
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key")
    OPENAI_MODEL: str = Field(default="gpt-4o", description="Default OpenAI model")

    # Supabase (for legacy compatibility)
    SUPABASE_URL: Optional[str] = Field(default=None, description="Supabase URL")
    SUPABASE_ANON_KEY: Optional[str] = Field(
        default=None, description="Supabase anonymous key"
    )
    SUPABASE_SERVICE_KEY: Optional[str] = Field(
        default=None, description="Supabase service key"
    )

    # Email Configuration
    SMTP_HOST: Optional[str] = Field(default=None, description="SMTP host")
    SMTP_PORT: int = Field(default=587, description="SMTP port")
    SMTP_USERNAME: Optional[str] = Field(default=None, description="SMTP username")
    SMTP_PASSWORD: Optional[str] = Field(default=None, description="SMTP password")
    SMTP_TLS: bool = Field(default=True, description="SMTP TLS enabled")

    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins",
    )

    # Security
    BCRYPT_ROUNDS: int = Field(default=12, description="Bcrypt rounds")
    PASSWORD_MIN_LENGTH: int = Field(default=8, description="Minimum password length")

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(
        default=100, description="Default rate limit per minute"
    )

    # Monitoring
    PROMETHEUS_METRICS_PATH: str = Field(
        default="/metrics", description="Prometheus metrics path"
    )
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
            "basic_analytics",
        ],
        description="Default features for new tenants",
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
            "advanced_automation",
        ],
        description="Features for premium tenants",
    )

    # External Integrations
    CALENDLY_API_KEY: Optional[str] = Field(
        default=None, description="Calendly API key"
    )
    SALESFORCE_CLIENT_ID: Optional[str] = Field(
        default=None, description="Salesforce client ID"
    )
    SALESFORCE_CLIENT_SECRET: Optional[str] = Field(
        default=None, description="Salesforce client secret"
    )
    HUBSPOT_API_KEY: Optional[str] = Field(default=None, description="HubSpot API key")

    # File Storage
    UPLOAD_MAX_SIZE: int = Field(
        default=10 * 1024 * 1024, description="Max upload size in bytes"
    )
    UPLOAD_ALLOWED_EXTENSIONS: List[str] = Field(
        default=[".pdf", ".doc", ".docx", ".txt", ".csv"],
        description="Allowed file extensions",
    )

    # Background Tasks
    CELERY_TASK_ROUTES: dict = Field(
        default={
            "app.tasks.crm_sync.*": {"queue": "crm_sync"},
            "app.tasks.analysis.*": {"queue": "analysis"},
            "app.tasks.notifications.*": {"queue": "notifications"},
            "app.tasks.reports.*": {"queue": "reports"},
        },
        description="Celery task routing",
    )

    # Development/Testing
    TESTING: bool = Field(default=False, description="Testing mode")
    TEST_DATABASE_URL: Optional[str] = Field(
        default=None, description="Test database URL"
    )

    # Additional environment variables
    HOST: str = Field(default="0.0.0.0", description="Host to bind")
    BACKEND_PORT: int = Field(
        default=8001, description="Backend port", alias="BACEND_PORT"
    )
    ENV: str = Field(
        default="development", description="Environment", alias="ENVIRONMENT"
    )
    FRONTEND_URL: str = Field(
        default="http://localhost:3000", description="Frontend URL"
    )
    ALLOWED_ORIGINS: str = Field(
        default="http://localhost:3000", description="Allowed origins"
    )
    TRUSTED_HOSTS: str = Field(
        default="localhost,127.0.0.1", description="Trusted hosts"
    )

    # Additional Supabase fields
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = Field(
        default=None, description="Supabase service role key"
    )
    NEXT_PUBLIC_SUPABASE_URL: Optional[str] = Field(
        default=None, description="Next.js public Supabase URL"
    )
    NEXT_PUBLIC_SUPABASE_ANON_KEY: Optional[str] = Field(
        default=None, description="Next.js public Supabase anon key"
    )

    # Additional Calendly fields
    CALENDLY_ACCESS_TOKEN: Optional[str] = Field(
        default=None, description="Calendly access token"
    )

    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = Field(
        default=None, description="Google OAuth client ID"
    )
    GOOGLE_CLIENT_SECRET: Optional[str] = Field(
        default=None, description="Google OAuth client secret"
    )
    GOOGLE_REDIRECT_URI: Optional[str] = Field(
        default=None, description="Google OAuth redirect URI"
    )
    GOOGLE_SCOPES: Optional[str] = Field(
        default=None, description="Google OAuth scopes"
    )
    GOOGLE_SERVICE_ACCOUNT_FILE: Optional[str] = Field(
        default=None, description="Google service account file"
    )

    # Pipedream
    PIPEDREAM_CLIENT_ID: Optional[str] = Field(
        default=None, description="Pipedream client ID"
    )
    PIPEDREAM_CLIENT_SECRET: Optional[str] = Field(
        default=None, description="Pipedream client secret"
    )
    PIPEDREAM_PROJECT_ID: Optional[str] = Field(
        default=None, description="Pipedream project ID"
    )
    PIPEDREAM_ENVIRONMENT: Optional[str] = Field(
        default=None, description="Pipedream environment"
    )

    # MCP (Model Context Protocol) Configuration
    MCP_TIMEOUT_SECONDS: int = Field(
        default=30, description="Default timeout for MCP operations in seconds"
    )
    MCP_CONNECTION_TIMEOUT: int = Field(
        default=10, description="Connection timeout for MCP servers in seconds"
    )
    MCP_READ_TIMEOUT: int = Field(
        default=60, description="Read timeout for MCP operations in seconds"
    )
    MCP_MAX_CONNECTIONS: int = Field(
        default=20, description="Maximum number of concurrent MCP connections"
    )
    MCP_CONNECTION_POOL_SIZE: int = Field(
        default=10, description="MCP connection pool size per service"
    )
    MCP_MAX_RETRIES: int = Field(
        default=3, description="Maximum number of retry attempts for MCP operations"
    )
    MCP_RETRY_BACKOFF_FACTOR: float = Field(
        default=2.0, description="Exponential backoff factor for MCP retries"
    )
    MCP_RETRY_MAX_DELAY: int = Field(
        default=60, description="Maximum delay between MCP retries in seconds"
    )
    MCP_CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = Field(
        default=5, description="Number of failures before opening circuit breaker"
    )
    MCP_CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = Field(
        default=60,
        description="Time in seconds before attempting circuit breaker recovery",
    )
    MCP_HEALTH_CHECK_INTERVAL: int = Field(
        default=300, description="MCP health check interval in seconds (5 minutes)"
    )
    MCP_RATE_LIMIT_PER_MINUTE: int = Field(
        default=60, description="Rate limit for MCP operations per minute per service"
    )
    MCP_ENABLE_LOGGING: bool = Field(
        default=True, description="Enable detailed logging for MCP operations"
    )
    MCP_LOG_LEVEL: str = Field(
        default="INFO",
        description="Log level for MCP operations (DEBUG, INFO, WARNING, ERROR)",
    )
    MCP_ENABLE_METRICS: bool = Field(
        default=True, description="Enable metrics collection for MCP operations"
    )
    MCP_FALLBACK_TO_DEMO: bool = Field(
        default=True, description="Enable fallback to demo mode when MCP services fail"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Allow extra fields from environment
    )

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

    def get_mcp_timeout_config(self) -> dict:
        """Get MCP timeout configuration"""
        return {
            "default_timeout": self.MCP_TIMEOUT_SECONDS,
            "connection_timeout": self.MCP_CONNECTION_TIMEOUT,
            "read_timeout": self.MCP_READ_TIMEOUT,
        }

    def get_mcp_retry_config(self) -> dict:
        """Get MCP retry configuration"""
        return {
            "max_retries": self.MCP_MAX_RETRIES,
            "backoff_factor": self.MCP_RETRY_BACKOFF_FACTOR,
            "max_delay": self.MCP_RETRY_MAX_DELAY,
        }

    def get_mcp_connection_config(self) -> dict:
        """Get MCP connection configuration"""
        return {
            "max_connections": self.MCP_MAX_CONNECTIONS,
            "pool_size": self.MCP_CONNECTION_POOL_SIZE,
            "rate_limit_per_minute": self.MCP_RATE_LIMIT_PER_MINUTE,
        }

    def get_mcp_circuit_breaker_config(self) -> dict:
        """Get MCP circuit breaker configuration"""
        return {
            "failure_threshold": self.MCP_CIRCUIT_BREAKER_FAILURE_THRESHOLD,
            "recovery_timeout": self.MCP_CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
        }

    def is_mcp_logging_enabled(self) -> bool:
        """Check if MCP logging is enabled"""
        return self.MCP_ENABLE_LOGGING

    def is_mcp_metrics_enabled(self) -> bool:
        """Check if MCP metrics collection is enabled"""
        return self.MCP_ENABLE_METRICS

    def should_fallback_to_demo(self) -> bool:
        """Check if MCP should fallback to demo mode on failures"""
        return self.MCP_FALLBACK_TO_DEMO


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
            "storage_mb": self.get_limit("storage_mb", 100),
        }


def get_tenant_config(
    tenant_id: str, features: List[str], limits: dict
) -> TenantConfig:
    """
    Create tenant configuration
    """
    return TenantConfig(tenant_id, features, limits)


# Environment-specific configurations
class DevelopmentConfig(Settings):
    """Development-specific configuration"""

    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"

    model_config = SettingsConfigDict(env_file=".env.development")


class ProductionConfig(Settings):
    """Production-specific configuration"""

    DEBUG: bool = False
    LOG_LEVEL: str = "WARNING"

    model_config = SettingsConfigDict(env_file=".env.production")


class TestingConfig(Settings):
    """Testing-specific configuration"""

    TESTING: bool = True
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite:///./test.db"

    model_config = SettingsConfigDict(env_file=".env.testing")


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


class DatabaseConfig(BaseSettings):
    """Database configuration"""

    database_url: str = Field(
        default="sqlite:///./pipewise.db", description="Database connection URL"
    )
    database_echo: bool = Field(False, description="Enable SQL query logging")
    database_pool_size: int = Field(10, description="Database connection pool size")
    database_max_overflow: int = Field(
        20, description="Database connection pool max overflow"
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


class RedisConfig(BaseSettings):
    """Redis configuration"""

    redis_url: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )
    redis_max_connections: int = Field(20, description="Maximum Redis connections")
    redis_retry_on_timeout: bool = Field(
        True, description="Retry Redis operations on timeout"
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


class SupabaseConfig(BaseSettings):
    """Supabase configuration"""

    supabase_url: str = Field(default="", description="Supabase project URL")
    supabase_key: str = Field(default="", description="Supabase anon/service key")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


class SecurityConfig(BaseSettings):
    """Security configuration"""

    secret_key: str = Field(
        default="dev-secret-key", description="Secret key for JWT signing"
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30, description="Access token expiration time"
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


class MCPConfig(BaseSettings):
    """MCP (Model Context Protocol) configuration"""

    # Connection and Timeout Settings
    mcp_timeout_seconds: int = Field(
        default=30, description="Default timeout for MCP operations in seconds"
    )
    mcp_connection_timeout: int = Field(
        default=10, description="Connection timeout for MCP servers in seconds"
    )
    mcp_read_timeout: int = Field(
        default=60, description="Read timeout for MCP operations in seconds"
    )
    mcp_max_connections: int = Field(
        default=20, description="Maximum number of concurrent MCP connections"
    )
    mcp_connection_pool_size: int = Field(
        default=10, description="MCP connection pool size per service"
    )

    # Retry and Error Handling Settings
    mcp_max_retries: int = Field(
        default=3, description="Maximum number of retry attempts for MCP operations"
    )
    mcp_retry_backoff_factor: float = Field(
        default=2.0, description="Exponential backoff factor for MCP retries"
    )
    mcp_retry_max_delay: int = Field(
        default=60, description="Maximum delay between MCP retries in seconds"
    )
    mcp_retry_jitter: bool = Field(
        default=True, description="Add random jitter to retry delays"
    )

    # Circuit Breaker Settings
    mcp_circuit_breaker_failure_threshold: int = Field(
        default=5, description="Number of failures before opening circuit breaker"
    )
    mcp_circuit_breaker_recovery_timeout: int = Field(
        default=60,
        description="Time in seconds before attempting circuit breaker recovery",
    )
    mcp_circuit_breaker_half_open_max_calls: int = Field(
        default=3, description="Maximum calls in half-open state"
    )

    # Health Monitoring Settings
    mcp_health_check_interval: int = Field(
        default=300, description="MCP health check interval in seconds (5 minutes)"
    )
    mcp_health_check_timeout: int = Field(
        default=10, description="Health check timeout in seconds"
    )
    mcp_unhealthy_threshold: int = Field(
        default=3, description="Number of failed health checks before marking unhealthy"
    )

    # Rate Limiting Settings
    mcp_rate_limit_per_minute: int = Field(
        default=60, description="Rate limit for MCP operations per minute per service"
    )
    mcp_burst_limit: int = Field(
        default=10, description="Burst limit for MCP operations"
    )

    # Logging and Monitoring Settings
    mcp_enable_logging: bool = Field(
        default=True, description="Enable detailed logging for MCP operations"
    )
    mcp_log_level: str = Field(
        default="INFO",
        description="Log level for MCP operations (DEBUG, INFO, WARNING, ERROR)",
    )
    mcp_enable_metrics: bool = Field(
        default=True, description="Enable metrics collection for MCP operations"
    )
    mcp_metrics_namespace: str = Field(
        default="pipewise_mcp", description="Metrics namespace for MCP operations"
    )

    # Fallback and Demo Mode Settings
    mcp_fallback_to_demo: bool = Field(
        default=True, description="Enable fallback to demo mode when MCP services fail"
    )
    mcp_demo_mode_timeout: int = Field(
        default=5, description="Timeout for demo mode responses in seconds"
    )

    # Agent-Specific Settings
    mcp_coordinator_services: List[str] = Field(
        default=["sendgrid", "twitter"],
        description="MCP services for Coordinator Agent",
    )
    mcp_meeting_scheduler_services: List[str] = Field(
        default=["calendly_v2", "google_calendar"],
        description="MCP services for Meeting Scheduler Agent",
    )
    mcp_lead_administrator_services: List[str] = Field(
        default=["pipedrive", "salesforce_rest_api", "zoho_crm"],
        description="MCP services for Lead Administrator Agent",
    )

    # OAuth Integration Settings
    mcp_oauth_token_refresh_threshold: int = Field(
        default=300,
        description="Refresh OAuth tokens when expiring within this many seconds",
    )
    mcp_oauth_max_refresh_attempts: int = Field(
        default=3, description="Maximum attempts to refresh OAuth tokens"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Allow extra fields from environment
    )

    def get_service_config(self, service_name: str) -> dict:
        """Get service-specific configuration"""
        return {
            "timeout": self.mcp_timeout_seconds,
            "connection_timeout": self.mcp_connection_timeout,
            "read_timeout": self.mcp_read_timeout,
            "max_retries": self.mcp_max_retries,
            "backoff_factor": self.mcp_retry_backoff_factor,
            "max_delay": self.mcp_retry_max_delay,
            "rate_limit": self.mcp_rate_limit_per_minute,
        }

    def get_circuit_breaker_config(self) -> dict:
        """Get circuit breaker configuration"""
        return {
            "failure_threshold": self.mcp_circuit_breaker_failure_threshold,
            "recovery_timeout": self.mcp_circuit_breaker_recovery_timeout,
            "half_open_max_calls": self.mcp_circuit_breaker_half_open_max_calls,
        }

    def get_health_check_config(self) -> dict:
        """Get health check configuration"""
        return {
            "interval": self.mcp_health_check_interval,
            "timeout": self.mcp_health_check_timeout,
            "unhealthy_threshold": self.mcp_unhealthy_threshold,
        }

    def get_agent_services(self, agent_type: str) -> List[str]:
        """Get MCP services for a specific agent type"""
        agent_services = {
            "coordinator": self.mcp_coordinator_services,
            "meeting_scheduler": self.mcp_meeting_scheduler_services,
            "lead_administrator": self.mcp_lead_administrator_services,
        }
        return agent_services.get(agent_type, [])

    def is_logging_enabled(self, level: str = "INFO") -> bool:
        """Check if logging is enabled for a specific level"""
        if not self.mcp_enable_logging:
            return False

        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        current_level_index = log_levels.index(self.mcp_log_level)
        check_level_index = log_levels.index(level)

        return check_level_index >= current_level_index


def get_mcp_config() -> MCPConfig:
    """
    Get MCP configuration instance
    """
    return MCPConfig()


def get_all_configs() -> dict:
    """
    Get all configuration instances for easy access
    """
    return {
        "main": get_settings(),
        "mcp": get_mcp_config(),
    }
