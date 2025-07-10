"""
Configuration management for MCP services.

This module handles loading configuration from environment variables
and provides default values for all MCP service integrations.
"""

import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class MCPSettings:
    """MCP system configuration loaded from environment variables."""

    # Health Monitor Settings
    health_check_interval: int = 300  # Health check interval in seconds
    health_check_timeout: int = 30  # Health check timeout in seconds
    health_alert_threshold: int = 3  # Consecutive failures before alerting

    # Alert Manager Settings
    alert_check_interval: int = 60  # Alert check interval in seconds
    max_active_alerts: int = 1000  # Maximum active alerts to maintain

    # Performance Monitor Settings
    max_data_points: int = 100000  # Maximum performance data points to keep
    aggregation_interval: int = 60  # Metrics aggregation interval in seconds
    retention_days: int = 7  # How many days to retain metrics

    # Logging Settings
    log_level: str = "INFO"  # Logging level
    enable_structured_logging: bool = True  # Enable structured JSON logging
    metrics_retention_hours: int = 24  # How long to retain in-memory metrics

    def __post_init__(self):
        """Load settings from environment variables after initialization."""
        self.health_check_interval = int(
            os.getenv("MCP_HEALTH_CHECK_INTERVAL", self.health_check_interval)
        )
        self.health_check_timeout = int(
            os.getenv("MCP_HEALTH_CHECK_TIMEOUT", self.health_check_timeout)
        )
        self.health_alert_threshold = int(
            os.getenv("MCP_HEALTH_ALERT_THRESHOLD", self.health_alert_threshold)
        )

        self.alert_check_interval = int(
            os.getenv("MCP_ALERT_CHECK_INTERVAL", self.alert_check_interval)
        )
        self.max_active_alerts = int(
            os.getenv("MCP_MAX_ACTIVE_ALERTS", self.max_active_alerts)
        )

        self.max_data_points = int(
            os.getenv("MCP_MAX_DATA_POINTS", self.max_data_points)
        )
        self.aggregation_interval = int(
            os.getenv("MCP_AGGREGATION_INTERVAL", self.aggregation_interval)
        )
        self.retention_days = int(os.getenv("MCP_RETENTION_DAYS", self.retention_days))

        self.log_level = os.getenv("MCP_LOG_LEVEL", self.log_level)
        self.enable_structured_logging = self._get_env_bool(
            "MCP_ENABLE_STRUCTURED_LOGGING", self.enable_structured_logging
        )
        self.metrics_retention_hours = int(
            os.getenv("MCP_METRICS_RETENTION_HOURS", self.metrics_retention_hours)
        )

    def _get_env_bool(self, key: str, default: bool) -> bool:
        """Get boolean value from environment variable."""
        value = os.getenv(key, "").lower()
        if value in ("true", "1", "yes", "on"):
            return True
        elif value in ("false", "0", "no", "off"):
            return False
        else:
            return default

    def dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "health_check_interval": self.health_check_interval,
            "health_check_timeout": self.health_check_timeout,
            "health_alert_threshold": self.health_alert_threshold,
            "alert_check_interval": self.alert_check_interval,
            "max_active_alerts": self.max_active_alerts,
            "max_data_points": self.max_data_points,
            "aggregation_interval": self.aggregation_interval,
            "retention_days": self.retention_days,
            "log_level": self.log_level,
            "enable_structured_logging": self.enable_structured_logging,
            "metrics_retention_hours": self.metrics_retention_hours,
        }


@dataclass
class ServiceConfig:
    """Configuration for a single MCP service."""

    name: str
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    health_check_enabled: bool = True

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with fallback to default."""
        return self.config.get(key, default)

    def update(self, **kwargs) -> None:
        """Update configuration values."""
        self.config.update(kwargs)


class MCPConfigManager:
    """Manager for all MCP service configurations."""

    def __init__(self):
        """Initialize the configuration manager."""
        self.settings = MCPSettings()
        self.services: Dict[str, ServiceConfig] = {}
        self._load_service_configurations()

    def _load_service_configurations(self) -> None:
        """Load service configurations from environment variables."""

        # SendGrid Configuration
        sendgrid_config = ServiceConfig(
            name="sendgrid",
            enabled=self._get_env_bool("SENDGRID_ENABLED", True),
            config={
                "api_key": os.getenv("SENDGRID_API_KEY", ""),
                "base_url": os.getenv(
                    "SENDGRID_BASE_URL", "https://api.sendgrid.com/v3"
                ),
                "from_email": os.getenv("SENDGRID_FROM_EMAIL", "noreply@pipewise.com"),
            },
        )
        self.services["sendgrid"] = sendgrid_config

        # Twitter Configuration
        twitter_config = ServiceConfig(
            name="twitter",
            enabled=self._get_env_bool("TWITTER_ENABLED", True),
            config={
                "bearer_token": os.getenv("TWITTER_BEARER_TOKEN", ""),
                "api_key": os.getenv("TWITTER_API_KEY", ""),
                "api_secret": os.getenv("TWITTER_API_SECRET", ""),
                "access_token": os.getenv("TWITTER_ACCESS_TOKEN", ""),
                "access_token_secret": os.getenv("TWITTER_ACCESS_TOKEN_SECRET", ""),
                "base_url": os.getenv("TWITTER_BASE_URL", "https://api.twitter.com/2"),
            },
        )
        self.services["twitter"] = twitter_config

        # Calendly Configuration
        calendly_config = ServiceConfig(
            name="calendly",
            enabled=self._get_env_bool("CALENDLY_ENABLED", True),
            config={
                "access_token": os.getenv("CALENDLY_ACCESS_TOKEN", ""),
                "base_url": os.getenv("CALENDLY_BASE_URL", "https://api.calendly.com"),
                "webhook_signing_key": os.getenv("CALENDLY_WEBHOOK_SIGNING_KEY", ""),
            },
        )
        self.services["calendly"] = calendly_config

        # Google Calendar Configuration
        google_calendar_config = ServiceConfig(
            name="google_calendar",
            enabled=self._get_env_bool("GOOGLE_CALENDAR_ENABLED", True),
            config={
                "access_token": os.getenv("GOOGLE_ACCESS_TOKEN", ""),
                "refresh_token": os.getenv("GOOGLE_REFRESH_TOKEN", ""),
                "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
                "base_url": os.getenv(
                    "GOOGLE_CALENDAR_BASE_URL", "https://www.googleapis.com/calendar/v3"
                ),
            },
        )
        self.services["google_calendar"] = google_calendar_config

        # Pipedrive Configuration
        pipedrive_config = ServiceConfig(
            name="pipedrive",
            enabled=self._get_env_bool("PIPEDRIVE_ENABLED", True),
            config={
                "api_token": os.getenv("PIPEDRIVE_API_TOKEN", ""),
                "base_url": os.getenv(
                    "PIPEDRIVE_BASE_URL", "https://api.pipedrive.com/v1"
                ),
                "company_domain": os.getenv("PIPEDRIVE_COMPANY_DOMAIN", ""),
            },
        )
        self.services["pipedrive"] = pipedrive_config

        # Salesforce Configuration
        salesforce_config = ServiceConfig(
            name="salesforce",
            enabled=self._get_env_bool("SALESFORCE_ENABLED", True),
            config={
                "access_token": os.getenv("SALESFORCE_ACCESS_TOKEN", ""),
                "refresh_token": os.getenv("SALESFORCE_REFRESH_TOKEN", ""),
                "instance_url": os.getenv("SALESFORCE_INSTANCE_URL", ""),
                "client_id": os.getenv("SALESFORCE_CLIENT_ID", ""),
                "client_secret": os.getenv("SALESFORCE_CLIENT_SECRET", ""),
                "api_version": os.getenv("SALESFORCE_API_VERSION", "v54.0"),
            },
        )
        self.services["salesforce"] = salesforce_config

        # Zoho CRM Configuration
        zoho_config = ServiceConfig(
            name="zoho",
            enabled=self._get_env_bool("ZOHO_ENABLED", True),
            config={
                "access_token": os.getenv("ZOHO_ACCESS_TOKEN", ""),
                "refresh_token": os.getenv("ZOHO_REFRESH_TOKEN", ""),
                "api_domain": os.getenv("ZOHO_API_DOMAIN", "www.zohoapis.com"),
                "client_id": os.getenv("ZOHO_CLIENT_ID", ""),
                "client_secret": os.getenv("ZOHO_CLIENT_SECRET", ""),
                "org_id": os.getenv("ZOHO_ORG_ID", ""),
            },
        )
        self.services["zoho"] = zoho_config

        # Pipedream Configuration
        pipedream_config = ServiceConfig(
            name="pipedream",
            enabled=self._get_env_bool("PIPEDREAM_ENABLED", True),
            config={
                "api_key": os.getenv("PIPEDREAM_API_KEY", ""),
                "base_url": os.getenv(
                    "PIPEDREAM_BASE_URL", "https://api.pipedream.com/v1"
                ),
                "workspace_id": os.getenv("PIPEDREAM_WORKSPACE_ID", ""),
            },
        )
        self.services["pipedream"] = pipedream_config

        # PipeWise API Configuration (for self-monitoring)
        pipewise_config = ServiceConfig(
            name="pipewise_api",
            enabled=self._get_env_bool("PIPEWISE_API_MONITORING_ENABLED", True),
            config={
                "base_url": os.getenv("PIPEWISE_API_BASE_URL", "http://localhost:8000"),
                "api_key": os.getenv("PIPEWISE_API_KEY", ""),
                "health_endpoint": os.getenv("PIPEWISE_HEALTH_ENDPOINT", "/health"),
            },
        )
        self.services["pipewise_api"] = pipewise_config

    def _get_env_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean value from environment variable."""
        value = os.getenv(key, "").lower()
        if value in ("true", "1", "yes", "on"):
            return True
        elif value in ("false", "0", "no", "off"):
            return False
        else:
            return default

    def get_service_config(self, service_name: str) -> Optional[ServiceConfig]:
        """Get configuration for a specific service."""
        return self.services.get(service_name)

    def get_enabled_services(self) -> Dict[str, ServiceConfig]:
        """Get all enabled services."""
        return {
            name: config for name, config in self.services.items() if config.enabled
        }

    def is_service_enabled(self, service_name: str) -> bool:
        """Check if a service is enabled."""
        service = self.services.get(service_name)
        return service.enabled if service else False

    def update_service_config(self, service_name: str, **kwargs) -> bool:
        """Update configuration for a service."""
        if service_name in self.services:
            self.services[service_name].update(**kwargs)
            return True
        return False

    def validate_configurations(self) -> Dict[str, List[str]]:
        """
        Validate all service configurations and return any issues.

        Returns:
            Dictionary mapping service names to lists of validation errors
        """
        validation_errors = {}

        for service_name, config in self.services.items():
            errors = []

            if not config.enabled:
                continue

            if service_name == "sendgrid":
                if not config.get("api_key"):
                    errors.append("SENDGRID_API_KEY is required")

            elif service_name == "twitter":
                if not config.get("bearer_token") and not config.get("api_key"):
                    errors.append(
                        "Either TWITTER_BEARER_TOKEN or TWITTER_API_KEY is required"
                    )

            elif service_name == "calendly":
                if not config.get("access_token"):
                    errors.append("CALENDLY_ACCESS_TOKEN is required")

            elif service_name == "google_calendar":
                if not config.get("client_id") or not config.get("client_secret"):
                    errors.append(
                        "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are required"
                    )

            elif service_name == "pipedrive":
                if not config.get("api_token"):
                    errors.append("PIPEDRIVE_API_TOKEN is required")

            elif service_name == "salesforce":
                if not config.get("client_id") or not config.get("client_secret"):
                    errors.append(
                        "SALESFORCE_CLIENT_ID and SALESFORCE_CLIENT_SECRET are required"
                    )

            elif service_name == "zoho":
                if not config.get("client_id") or not config.get("client_secret"):
                    errors.append("ZOHO_CLIENT_ID and ZOHO_CLIENT_SECRET are required")

            elif service_name == "pipedream":
                if not config.get("api_key"):
                    errors.append("PIPEDREAM_API_KEY is required")

            if errors:
                validation_errors[service_name] = errors

        return validation_errors

    def get_notification_config(self) -> Dict[str, Any]:
        """Get notification configuration for alerts."""
        return {
            "email": {
                "enabled": self._get_env_bool("ALERT_EMAIL_ENABLED", True),
                "smtp_server": os.getenv("ALERT_SMTP_SERVER", "smtp.gmail.com"),
                "smtp_port": int(os.getenv("ALERT_SMTP_PORT", "587")),
                "smtp_username": os.getenv("ALERT_SMTP_USERNAME", ""),
                "smtp_password": os.getenv("ALERT_SMTP_PASSWORD", ""),
                "from_email": os.getenv("ALERT_FROM_EMAIL", "alerts@pipewise.com"),
                "to_emails": os.getenv("ALERT_TO_EMAILS", "admin@pipewise.com").split(
                    ","
                ),
                "use_tls": self._get_env_bool("ALERT_SMTP_TLS", True),
            },
            "slack": {
                "enabled": self._get_env_bool("ALERT_SLACK_ENABLED", False),
                "webhook_url": os.getenv("ALERT_SLACK_WEBHOOK_URL", ""),
                "channel": os.getenv("ALERT_SLACK_CHANNEL", "#alerts"),
                "username": os.getenv("ALERT_SLACK_USERNAME", "PipeWise Alert Bot"),
            },
            "webhook": {
                "enabled": self._get_env_bool("ALERT_WEBHOOK_ENABLED", False),
                "url": os.getenv("ALERT_WEBHOOK_URL", ""),
                "method": os.getenv("ALERT_WEBHOOK_METHOD", "POST"),
                "headers": {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {os.getenv('ALERT_WEBHOOK_TOKEN', '')}",
                },
            },
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "settings": self.settings.dict(),
            "services": {
                name: {
                    "name": config.name,
                    "enabled": config.enabled,
                    "config": config.config,
                    "health_check_enabled": config.health_check_enabled,
                }
                for name, config in self.services.items()
            },
            "notification": self.get_notification_config(),
        }


# Global configuration manager instance
config_manager = MCPConfigManager()


def get_config_manager() -> MCPConfigManager:
    """Get the global configuration manager instance."""
    return config_manager


def get_mcp_settings() -> MCPSettings:
    """Get MCP system settings."""
    return config_manager.settings


def get_service_config(service_name: str) -> Optional[ServiceConfig]:
    """Get configuration for a specific service."""
    return config_manager.get_service_config(service_name)


def get_enabled_services() -> Dict[str, ServiceConfig]:
    """Get all enabled services."""
    return config_manager.get_enabled_services()


def validate_mcp_config() -> Dict[str, List[str]]:
    """Validate MCP configuration and return any errors."""
    return config_manager.validate_configurations()
