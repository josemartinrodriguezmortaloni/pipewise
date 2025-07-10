"""
Configuration module for MCP integration tests.

This module manages environment variables and test settings for integration tests
with real MCP services. It provides configuration for all external service integrations
and test environment setup.
"""

import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MCPServiceConfig:
    """Configuration for an individual MCP service."""

    service_name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    sandbox_mode: bool = True
    timeout: int = 30
    max_retries: int = 3
    additional_config: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        """Initialize additional configuration if not provided."""
        if self.additional_config is None:
            self.additional_config = {}


@dataclass
class IntegrationTestConfig:
    """Main configuration class for integration tests."""

    # Test environment settings
    run_integration_tests: bool = False
    test_user_id: str = "integration-test-user"
    test_lead_email: str = "test.lead@example.com"
    test_lead_name: str = "John Doe"
    test_company_name: str = "TechCorp Solutions"

    # MCP environment settings
    mcp_environment: str = "test"
    use_sandbox_apis: bool = True
    mcp_timeout: int = 30
    mcp_max_retries: int = 3

    # Database settings
    test_database_url: Optional[str] = None
    supabase_test_url: Optional[str] = None
    supabase_test_anon_key: Optional[str] = None
    redis_test_url: Optional[str] = None

    # Logging and monitoring
    log_level: str = "DEBUG"
    test_log_file: str = "tests/logs/integration_tests.log"
    enable_performance_logging: bool = True
    enable_metrics: bool = True

    # Rate limiting and security
    rate_limit_test_mode: bool = True
    rate_limit_requests_per_minute: int = 10
    jwt_test_secret: Optional[str] = None

    # Cleanup and maintenance
    auto_cleanup_test_data: bool = True
    cleanup_after_hours: int = 24

    # Concurrent testing
    max_concurrent_requests: int = 5
    concurrent_agent_limit: int = 3

    # Service configurations
    sendgrid: Optional[MCPServiceConfig] = None
    twitter: Optional[MCPServiceConfig] = None
    calendly: Optional[MCPServiceConfig] = None
    google_calendar: Optional[MCPServiceConfig] = None
    pipedrive: Optional[MCPServiceConfig] = None
    salesforce: Optional[MCPServiceConfig] = None
    zoho: Optional[MCPServiceConfig] = None
    pipedream: Optional[MCPServiceConfig] = None

    def __post_init__(self) -> None:
        """Initialize service configurations from environment variables."""
        self._load_from_environment()
        self._initialize_service_configs()

    def _load_from_environment(self) -> None:
        """Load configuration values from environment variables."""
        # Test environment settings
        self.run_integration_tests = os.getenv("RUN_INTEGRATION_TESTS", "0") == "1"
        self.test_user_id = os.getenv("TEST_USER_ID", self.test_user_id)
        self.test_lead_email = os.getenv("TEST_LEAD_EMAIL", self.test_lead_email)
        self.test_lead_name = os.getenv("TEST_LEAD_NAME", self.test_lead_name)
        self.test_company_name = os.getenv("TEST_COMPANY_NAME", self.test_company_name)

        # MCP settings
        self.mcp_environment = os.getenv("MCP_ENVIRONMENT", self.mcp_environment)
        self.use_sandbox_apis = os.getenv("USE_SANDBOX_APIS", "true").lower() == "true"
        self.mcp_timeout = int(os.getenv("MCP_TIMEOUT", str(self.mcp_timeout)))
        self.mcp_max_retries = int(
            os.getenv("MCP_MAX_RETRIES", str(self.mcp_max_retries))
        )

        # Database settings
        self.test_database_url = os.getenv("TEST_DATABASE_URL")
        self.supabase_test_url = os.getenv("SUPABASE_TEST_URL")
        self.supabase_test_anon_key = os.getenv("SUPABASE_TEST_ANON_KEY")
        self.redis_test_url = os.getenv("REDIS_TEST_URL")

        # Logging and monitoring
        self.log_level = os.getenv("LOG_LEVEL", self.log_level)
        self.test_log_file = os.getenv("TEST_LOG_FILE", self.test_log_file)
        self.enable_performance_logging = (
            os.getenv("ENABLE_PERFORMANCE_LOGGING", "true").lower() == "true"
        )
        self.enable_metrics = os.getenv("ENABLE_METRICS", "true").lower() == "true"

        # Rate limiting and security
        self.rate_limit_test_mode = (
            os.getenv("RATE_LIMIT_TEST_MODE", "true").lower() == "true"
        )
        self.rate_limit_requests_per_minute = int(
            os.getenv(
                "RATE_LIMIT_REQUESTS_PER_MINUTE",
                str(self.rate_limit_requests_per_minute),
            )
        )
        self.jwt_test_secret = os.getenv("JWT_TEST_SECRET")

        # Cleanup and maintenance
        self.auto_cleanup_test_data = (
            os.getenv("AUTO_CLEANUP_TEST_DATA", "true").lower() == "true"
        )
        self.cleanup_after_hours = int(
            os.getenv("CLEANUP_AFTER_HOURS", str(self.cleanup_after_hours))
        )

        # Concurrent testing
        self.max_concurrent_requests = int(
            os.getenv("MAX_CONCURRENT_REQUESTS", str(self.max_concurrent_requests))
        )
        self.concurrent_agent_limit = int(
            os.getenv("CONCURRENT_AGENT_LIMIT", str(self.concurrent_agent_limit))
        )

    def _initialize_service_configs(self) -> None:
        """Initialize service-specific configurations."""
        # SendGrid configuration
        self.sendgrid = MCPServiceConfig(
            service_name="sendgrid",
            api_key=os.getenv("SENDGRID_TEST_API_KEY"),
            base_url="https://api.sendgrid.com/v3",
            sandbox_mode=os.getenv("SENDGRID_SANDBOX_MODE", "true").lower() == "true",
            additional_config={
                "from_email": os.getenv(
                    "SENDGRID_TEST_FROM_EMAIL", "noreply@pipewise.test"
                )
            },
        )

        # Twitter configuration
        self.twitter = MCPServiceConfig(
            service_name="twitter",
            api_key=os.getenv("TWITTER_TEST_BEARER_TOKEN"),
            base_url="https://api.twitter.com/2",
            sandbox_mode=os.getenv("TWITTER_SANDBOX_MODE", "true").lower() == "true",
            additional_config={
                "api_key": os.getenv("TWITTER_TEST_API_KEY"),
                "api_secret": os.getenv("TWITTER_TEST_API_SECRET"),
            },
        )

        # Calendly configuration
        self.calendly = MCPServiceConfig(
            service_name="calendly",
            api_key=os.getenv("CALENDLY_TEST_TOKEN"),
            base_url=os.getenv("CALENDLY_SANDBOX_URL", "https://api.calendly.com"),
            additional_config={
                "event_type": os.getenv(
                    "CALENDLY_TEST_EVENT_TYPE", "discovery-call-test"
                )
            },
        )

        # Google Calendar configuration
        self.google_calendar = MCPServiceConfig(
            service_name="google_calendar",
            base_url="https://www.googleapis.com/calendar/v3",
            sandbox_mode=os.getenv("GOOGLE_CALENDAR_SANDBOX_MODE", "true").lower()
            == "true",
            additional_config={
                "credentials_file": os.getenv("GOOGLE_CALENDAR_TEST_CREDENTIALS"),
                "calendar_id": os.getenv("GOOGLE_CALENDAR_TEST_CALENDAR_ID"),
            },
        )

        # Pipedrive configuration
        self.pipedrive = MCPServiceConfig(
            service_name="pipedrive",
            api_key=os.getenv("PIPEDRIVE_TEST_TOKEN"),
            base_url=f"https://{os.getenv('PIPEDRIVE_SANDBOX_DOMAIN', 'sandbox.pipedrive.com')}/api/v1",
            additional_config={
                "pipeline_id": os.getenv("PIPEDRIVE_TEST_PIPELINE_ID", "1")
            },
        )

        # Salesforce configuration
        self.salesforce = MCPServiceConfig(
            service_name="salesforce",
            base_url=os.getenv("SALESFORCE_SANDBOX_URL", "https://test.salesforce.com"),
            additional_config={
                "client_id": os.getenv("SALESFORCE_TEST_CLIENT_ID"),
                "client_secret": os.getenv("SALESFORCE_TEST_CLIENT_SECRET"),
                "username": os.getenv("SALESFORCE_TEST_USERNAME"),
                "password": os.getenv("SALESFORCE_TEST_PASSWORD"),
                "security_token": os.getenv("SALESFORCE_TEST_SECURITY_TOKEN"),
            },
        )

        # Zoho CRM configuration
        self.zoho = MCPServiceConfig(
            service_name="zoho",
            base_url=f"https://{os.getenv('ZOHO_SANDBOX_DOMAIN', 'crmsandbox.zoho.com')}/crm/v2",
            additional_config={
                "client_id": os.getenv("ZOHO_TEST_CLIENT_ID"),
                "client_secret": os.getenv("ZOHO_TEST_CLIENT_SECRET"),
                "refresh_token": os.getenv("ZOHO_TEST_REFRESH_TOKEN"),
            },
        )

        # Pipedream configuration
        self.pipedream = MCPServiceConfig(
            service_name="pipedream",
            api_key=os.getenv("PIPEDREAM_TEST_API_KEY"),
            base_url=os.getenv("PIPEDREAM_SANDBOX_URL", "https://api.pipedream.com/v1"),
        )

    def get_service_config(self, service_name: str) -> Optional[MCPServiceConfig]:
        """Get configuration for a specific service."""
        return getattr(self, service_name, None)

    def is_service_configured(self, service_name: str) -> bool:
        """Check if a service is properly configured for testing."""
        config = self.get_service_config(service_name)
        if not config:
            return False

        # Check if required credentials are available
        if service_name in [
            "sendgrid",
            "twitter",
            "calendly",
            "pipedrive",
            "pipedream",
        ]:
            return config.api_key is not None
        elif service_name == "google_calendar":
            return (
                config.additional_config is not None
                and config.additional_config.get("credentials_file") is not None
            )
        elif service_name in ["salesforce", "zoho"]:
            required_fields = ["client_id", "client_secret"]
            return config.additional_config is not None and all(
                config.additional_config.get(field) for field in required_fields
            )

        return True

    def get_configured_services(self) -> List[str]:
        """Get list of properly configured services."""
        services = [
            "sendgrid",
            "twitter",
            "calendly",
            "google_calendar",
            "pipedrive",
            "salesforce",
            "zoho",
            "pipedream",
        ]
        return [service for service in services if self.is_service_configured(service)]

    def get_test_credentials(self) -> Dict[str, Any]:
        """Get test credentials in the format expected by MCP factory."""
        credentials = {"user_id": self.test_user_id}

        configured_services = self.get_configured_services()

        for service in configured_services:
            config = self.get_service_config(service)
            if config and config.api_key:
                credentials[f"{service}_token"] = config.api_key
            elif service == "google_calendar":
                credentials["google_token"] = "google_calendar_token"  # Placeholder
            elif service in ["salesforce", "zoho"]:
                credentials[f"{service}_token"] = (
                    f"{service}_oauth_token"  # Placeholder
                )

        return credentials

    def create_log_directory(self) -> None:
        """Create log directory if it doesn't exist."""
        log_path = Path(self.test_log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

    def validate_configuration(self) -> Dict[str, Any]:
        """Validate the test configuration and return status."""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "configured_services": self.get_configured_services(),
        }

        # Check if integration tests should run
        if not self.run_integration_tests:
            validation_result["warnings"].append(
                "Integration tests disabled. Set RUN_INTEGRATION_TESTS=1 to enable."
            )

        # Check if any services are configured
        if not validation_result["configured_services"]:
            validation_result["valid"] = False
            validation_result["errors"].append(
                "No MCP services are properly configured for testing."
            )

        # Check database configuration
        if not self.test_database_url and not self.supabase_test_url:
            validation_result["warnings"].append(
                "No test database configured. Some tests may fail."
            )

        # Check essential services
        essential_services = ["sendgrid", "twitter"]
        missing_essential = [
            s
            for s in essential_services
            if s not in validation_result["configured_services"]
        ]
        if missing_essential:
            validation_result["warnings"].append(
                f"Essential services not configured: {', '.join(missing_essential)}"
            )

        return validation_result

    def print_configuration_status(self) -> None:
        """Print the current configuration status."""
        validation = self.validate_configuration()

        print("=" * 60)
        print("MCP Integration Test Configuration Status")
        print("=" * 60)

        print(f"Integration Tests Enabled: {self.run_integration_tests}")
        print(f"Environment: {self.mcp_environment}")
        print(f"Sandbox Mode: {self.use_sandbox_apis}")
        print(f"Test User ID: {self.test_user_id}")

        print(f"\nConfigured Services ({len(validation['configured_services'])}):")
        for service in validation["configured_services"]:
            config = self.get_service_config(service)
            status = (
                "✓" if config and (config.api_key or config.additional_config) else "?"
            )
            print(f"  {status} {service.title()}")

        if validation["errors"]:
            print("\n⚠️  Errors:")
            for error in validation["errors"]:
                print(f"  - {error}")

        if validation["warnings"]:
            print("\n⚠️  Warnings:")
            for warning in validation["warnings"]:
                print(f"  - {warning}")

        print("\n" + "=" * 60)


# Global configuration instance
config = IntegrationTestConfig()


def get_integration_config() -> IntegrationTestConfig:
    """Get the global integration test configuration."""
    return config


def is_integration_testing_enabled() -> bool:
    """Check if integration testing is enabled."""
    return config.run_integration_tests


def get_test_credentials() -> Dict[str, Any]:
    """Get test credentials for MCP services."""
    return config.get_test_credentials()


def validate_test_environment() -> bool:
    """Validate that the test environment is properly configured."""
    validation = config.validate_configuration()
    return validation["valid"]


# Example usage and environment setup instructions
if __name__ == "__main__":
    print(__doc__)
    print("\nTo configure integration tests, set these environment variables:")
    print("\n# Essential Configuration")
    print("export RUN_INTEGRATION_TESTS=1")
    print("export TEST_USER_ID=your-test-user-id")
    print("\n# Service API Keys")
    print("export SENDGRID_TEST_API_KEY=your_sendgrid_test_key")
    print("export TWITTER_TEST_BEARER_TOKEN=your_twitter_test_token")
    print("export CALENDLY_TEST_TOKEN=your_calendly_test_token")
    print("export PIPEDRIVE_TEST_TOKEN=your_pipedrive_test_token")
    print("\n# Database Configuration")
    print("export TEST_DATABASE_URL=postgresql://user:pass@localhost:5432/test_db")
    print("export SUPABASE_TEST_URL=https://your-project.supabase.co")
    print("export SUPABASE_TEST_ANON_KEY=your_test_anon_key")

    print("\nCurrent Configuration:")
    config.print_configuration_status()
