"""
Integration tests for MCP monitoring system.

This module tests the complete MCP monitoring infrastructure including:
- Health monitoring with periodic checks
- Alert management with notification channels
- Performance monitoring and metrics collection
- Integration with FastAPI and PipeWise infrastructure
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
import asyncio

from app.ai_agents.mcp.health_monitor import MCPHealthMonitor, ServiceStatus
from app.ai_agents.mcp.alert_manager import (
    MCPAlertManager,
    AlertSeverity,
    AlertStatus,
)
from app.ai_agents.mcp.performance_metrics import MCPPerformanceMonitor
from app.ai_agents.mcp.config import MCPConfigManager
from app.ai_agents.mcp.structured_logger import OperationType
from fastapi.testclient import TestClient


class TestMCPHealthMonitorIntegration:
    """Test health monitoring integration."""

    @pytest.fixture
    def mock_health_monitor(self):
        """Create a mock health monitor for testing."""
        monitor = MCPHealthMonitor(check_interval=1, timeout=5)
        monitor.logger = MagicMock()
        return monitor

    @pytest.fixture
    def sample_service_config(self):
        """Sample service configuration for testing."""
        return {
            "sendgrid": {
                "api_key": "test_api_key",
                "base_url": "https://api.sendgrid.com/v3",
                "from_email": "test@example.com",
            },
            "twitter": {
                "bearer_token": "test_bearer_token",
                "api_key": "test_api_key",
                "base_url": "https://api.twitter.com/2",
            },
        }

    @pytest.mark.asyncio
    async def test_health_monitor_service_registration(
        self, mock_health_monitor, sample_service_config
    ):
        """Test service registration in health monitor."""
        # Register services
        for service_name, config in sample_service_config.items():
            mock_health_monitor.register_service(service_name, config)

        # Verify services are registered
        assert "sendgrid" in mock_health_monitor.services
        assert "twitter" in mock_health_monitor.services
        assert len(mock_health_monitor.services) == 2

    @pytest.mark.asyncio
    async def test_health_check_execution(self, mock_health_monitor):
        """Test health check execution for registered services."""
        # Register a test service
        mock_health_monitor.register_service(
            "test_service", {"base_url": "https://httpbin.org/status/200"}
        )

        # Mock the HTTP client to return success
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "ok"}
            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            # Execute health check
            result = await mock_health_monitor.check_service_health("test_service")

            # Verify result
            assert result.status == ServiceStatus.HEALTHY
            assert result.service_name == "test_service"
            assert result.response_time_ms > 0

    @pytest.mark.asyncio
    async def test_health_monitor_failure_detection(self, mock_health_monitor):
        """Test health monitor failure detection and recording."""
        # Register a test service
        mock_health_monitor.register_service(
            "failing_service", {"base_url": "https://httpbin.org/status/500"}
        )

        # Mock the HTTP client to return failure
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.json.return_value = {"error": "Internal Server Error"}
            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            # Execute health check
            result = await mock_health_monitor.check_service_health("failing_service")

            # Verify failure is detected
            assert result.status == ServiceStatus.UNHEALTHY
            assert result.service_name == "failing_service"
            assert result.error_message is not None

    @pytest.mark.asyncio
    async def test_health_monitor_timeout_handling(self, mock_health_monitor):
        """Test health monitor timeout handling."""
        # Register a test service
        mock_health_monitor.register_service(
            "timeout_service", {"base_url": "https://httpbin.org/delay/10"}
        )

        # Mock the HTTP client to raise timeout
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = (
                asyncio.TimeoutError("Request timeout")
            )

            # Execute health check
            result = await mock_health_monitor.check_service_health("timeout_service")

            # Verify timeout is handled
            assert result.status == ServiceStatus.UNHEALTHY
            assert "timeout" in (result.error_message or "").lower()


class TestMCPAlertManagerIntegration:
    """Test alert management integration."""

    @pytest.fixture
    def mock_alert_manager(self):
        """Create a mock alert manager for testing."""
        manager = MCPAlertManager(max_active_alerts=100, alert_check_interval=1)
        manager.logger = MagicMock()
        return manager

    @pytest.fixture
    def sample_alert_config(self):
        """Sample alert configuration for testing."""
        return {
            "email": {
                "enabled": True,
                "smtp_server": "smtp.test.com",
                "smtp_port": 587,
                "smtp_username": "test@example.com",
                "smtp_password": "test_password",
                "from_email": "alerts@example.com",
                "to_emails": ["admin@example.com"],
                "use_tls": True,
            },
            "webhook": {
                "enabled": True,
                "url": "https://example.com/webhook",
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
            },
        }

    @pytest.mark.asyncio
    async def test_alert_creation_and_management(self, mock_alert_manager):
        """Test alert creation and basic management."""
        await mock_alert_manager.check_service_unavailability(
            "test_service", ServiceStatus.UNHEALTHY
        )
        assert len(mock_alert_manager.active_alerts) > 0
        alert = list(mock_alert_manager.active_alerts.values())[0]
        assert alert.service_name == "test_service"
        assert alert.severity == AlertSeverity.WARNING  # default
        assert alert.status == AlertStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_alert_notification_sending(
        self, mock_alert_manager, sample_alert_config
    ):
        """Test alert notification sending."""
        # Configure notification settings
        mock_alert_manager.notification_config = sample_alert_config

        # Create test alert
        alert_data = {
            "service_name": "test_service",
            "severity": AlertSeverity.CRITICAL,
            "message": "Service is down",
        }

        alert = await mock_alert_manager.create_alert(**alert_data)

        # Mock notification sending
        with patch.object(mock_alert_manager, "_send_email_notification") as mock_email:
            with patch.object(
                mock_alert_manager, "_send_webhook_notification"
            ) as mock_webhook:
                mock_email.return_value = True
                mock_webhook.return_value = True

                # Send notifications
                await mock_alert_manager.send_alert_notifications(alert)

                # Verify notifications were sent
                mock_email.assert_called_once()
                mock_webhook.assert_called_once()

    @pytest.mark.asyncio
    async def test_alert_escalation_and_resolution(self, mock_alert_manager):
        """Test alert escalation and resolution."""
        # Create test alert
        alert_data = {
            "service_name": "test_service",
            "severity": AlertSeverity.WARNING,
            "message": "Service performance degraded",
        }

        alert = await mock_alert_manager.create_alert(**alert_data)

        # Test escalation
        await mock_alert_manager.escalate_alert(alert.id, AlertSeverity.CRITICAL)
        updated_alert = mock_alert_manager.alerts[alert.id]
        assert updated_alert.severity == AlertSeverity.CRITICAL

        # Test resolution
        await mock_alert_manager.resolve_alert(alert.id, "Service restored")
        resolved_alert = mock_alert_manager.alerts[alert.id]
        assert resolved_alert.resolved_at is not None
        assert resolved_alert.resolution_notes == "Service restored"

    @pytest.mark.asyncio
    async def test_alert_duplicate_detection(self, mock_alert_manager):
        """Test duplicate alert detection and handling."""
        # Create initial alert
        alert_data = {
            "service_name": "test_service",
            "severity": AlertSeverity.WARNING,
            "message": "Service slow response",
        }

        alert1 = await mock_alert_manager.create_alert(**alert_data)

        # Try to create duplicate alert
        alert2 = await mock_alert_manager.create_alert(**alert_data)

        # Should either be the same alert or increment occurrence count
        if alert1.id == alert2.id:
            assert alert1.occurrence_count > 1
        else:
            # Verify both alerts exist but are properly managed
            assert len(mock_alert_manager.alerts) == 2


class TestMCPPerformanceMonitorIntegration:
    """Test performance monitoring integration."""

    @pytest.fixture
    def mock_performance_monitor(self):
        """Create a mock performance monitor for testing."""
        monitor = MCPPerformanceMonitor()
        monitor.mcp_logger = MagicMock()
        return monitor

    @pytest.mark.asyncio
    async def test_performance_metric_recording(self, mock_performance_monitor):
        """Test performance metric recording."""
        correlation_id = mock_performance_monitor.start_operation(
            operation_id="test_op_id",
            service_name="test_service",
            operation="api_call",
        )
        mock_performance_monitor.end_operation(correlation_id, success=True)
        metrics = mock_performance_monitor.get_metrics()
        assert len(metrics) > 0
        assert "test_service" in mock_performance_monitor.service_metrics

    @pytest.mark.asyncio
    async def test_performance_metrics_aggregation(self, mock_performance_monitor):
        """Test performance metrics aggregation."""
        # Record multiple metrics
        service_name = "test_service"
        for i in range(10):
            mock_performance_monitor.record_operation(
                service_name=service_name,
                operation="api_call",
                response_time_ms=0.1 * (i + 1),
                success=i % 2 == 0,
            )

        # Get aggregated metrics
        aggregated = mock_performance_monitor.get_aggregated_metrics(service_name)

        # Verify aggregation
        assert aggregated["total_operations"] == 10
        assert aggregated["success_rate"] == 0.5  # 50% success rate
        assert aggregated["avg_response_time"] > 0

    @pytest.mark.asyncio
    async def test_performance_alert_triggers(self, mock_performance_monitor):
        """Test performance-based alert triggers."""
        # Record slow response times
        service_name = "slow_service"
        for i in range(5):
            correlation_id = mock_performance_monitor.start_operation(
                OperationType.AGENT_WORKFLOW,
                tags={"service": "slow_service", "operation": "slow_operation"},
            )
            mock_performance_monitor.end_operation(
                correlation_id, success=True, response_time_ms=2.0
            )

        # Check if performance triggers alert conditions
        performance_issues = mock_performance_monitor.check_performance_thresholds(
            service_name
        )

        # Verify performance issues are detected
        assert len(performance_issues) > 0
        assert any("slow" in issue.lower() for issue in performance_issues)


class TestMCPConfigManagerIntegration:
    """Test configuration management integration."""

    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock configuration manager for testing."""
        with patch.dict(
            "os.environ",
            {
                "MCP_HEALTH_CHECK_INTERVAL": "300",
                "SENDGRID_API_KEY": "test_sendgrid_key",
                "TWITTER_BEARER_TOKEN": "test_twitter_token",
                "PIPEDRIVE_API_TOKEN": "test_pipedrive_token",
            },
        ):
            manager = MCPConfigManager()
            return manager

    def test_config_loading_from_environment(self, mock_config_manager):
        """Test configuration loading from environment variables."""
        # Verify settings are loaded from environment
        assert mock_config_manager.settings.health_check_interval == 300

        # Verify service configs are loaded
        sendgrid_config = mock_config_manager.get_service_config("sendgrid")
        assert sendgrid_config is not None
        assert sendgrid_config.get("api_key") == "test_sendgrid_key"

    def test_config_validation(self, mock_config_manager):
        """Test configuration validation."""
        # Run validation
        errors = mock_config_manager.validate_configurations()

        # Verify validation results
        # Should have minimal errors since we provided test keys
        assert isinstance(errors, dict)

        # Services with missing required configs should have errors
        if "google_calendar" in errors:
            assert "GOOGLE_CLIENT_ID" in str(errors["google_calendar"])

    def test_enabled_services_filtering(self, mock_config_manager):
        """Test filtering of enabled services."""
        # Get enabled services
        enabled = mock_config_manager.get_enabled_services()

        # Verify enabled services are returned
        assert isinstance(enabled, dict)
        assert len(enabled) > 0

        # All returned services should be enabled
        for service_config in enabled.values():
            assert service_config.enabled is True


class TestMCPHealthRouterIntegration:
    """Test health router integration with FastAPI."""

    @pytest.fixture
    def test_client(self):
        """Create test client for FastAPI application."""
        from app.api.main import app

        return TestClient(app)

    def test_health_endpoint_availability(self, test_client):
        """Test health endpoint is available."""
        response = test_client.get("/health/mcp")

        # Should return 200 OK
        assert response.status_code == 200

        # Should return JSON with health status
        data = response.json()
        assert "status" in data
        assert "services" in data
        assert "timestamp" in data

    def test_health_endpoint_service_details(self, test_client):
        """Test health endpoint returns service details."""
        response = test_client.get("/health/mcp")
        data = response.json()

        # Should have service details
        assert isinstance(data["services"], dict)

        # Each service should have required fields
        for service_name, service_data in data["services"].items():
            assert "status" in service_data
            assert "last_check" in service_data

    def test_health_endpoint_performance_metrics(self, test_client):
        """Test health endpoint includes performance metrics."""
        response = test_client.get("/health/mcp")
        data = response.json()

        # Should have performance metrics
        assert "performance" in data
        assert isinstance(data["performance"], dict)

    def test_health_endpoint_error_handling(self, test_client):
        """Test health endpoint error handling."""
        # Mock health monitor to raise exception
        with patch("app.api.health_router.get_health_monitor") as mock_monitor:
            mock_monitor.return_value.get_system_health.side_effect = Exception(
                "Health check failed"
            )

            response = test_client.get("/health/mcp")

            # Should still return 200 but with error status
            assert response.status_code == 200
            data = response.json()
            assert "error" in data or data.get("status") == "error"


# Performance and load testing
class TestMCPPerformanceIntegration:
    """Test MCP system performance under load."""

    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self):
        """Test concurrent health checks performance."""
        health_monitor = MCPHealthMonitor(check_interval=1, timeout=5)
        health_monitor.logger = MagicMock()

        # Register multiple services
        services = [f"service_{i}" for i in range(10)]
        for service in services:
            health_monitor.register_service(
                service, {"base_url": f"https://httpbin.org/status/200"}
            )

        # Mock successful responses
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "ok"}
            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            # Execute concurrent health checks
            start_time = datetime.now()
            tasks = [
                health_monitor.check_service_health(service) for service in services
            ]
            results = await asyncio.gather(*tasks)
            end_time = datetime.now()

            # Verify all checks completed successfully
            assert len(results) == 10
            for result in results:
                assert result.status == ServiceStatus.HEALTHY

            # Verify reasonable performance (should complete within 10 seconds)
            duration = (end_time - start_time).total_seconds()
            assert duration < 10.0

    @pytest.mark.asyncio
    async def test_high_volume_metric_recording(self):
        """Test high volume metric recording performance."""
        performance_monitor = MCPPerformanceMonitor(
            max_data_points=10000, aggregation_interval=60
        )
        performance_monitor.mcp_logger = MagicMock()

        # Record large number of metrics
        start_time = datetime.now()
        for i in range(1000):
            correlation_id = performance_monitor.start_operation(
                operation_id=f"op_{i}",
                service_name="test_service",
                operation=f"api_call_{i}",
            )
            performance_monitor.end_operation(
                correlation_id, success=True, response_time_ms=0.5 + i * 0.001
            )
        end_time = datetime.now()

        # Verify metrics were recorded
        metrics = performance_monitor.get_service_metrics("test_service")
        assert len(metrics) == 1000

        # Verify reasonable performance (should complete within 5 seconds)
        duration = (end_time - start_time).total_seconds()
        assert duration < 5.0

    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self):
        """Test memory usage under sustained load."""
        import psutil  # type: ignore
        import os

        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create monitoring components
        alert_manager = MCPAlertManager(max_active_alerts=1000, alert_check_interval=1)
        performance_monitor = MCPPerformanceMonitor(
            max_data_points=10000, aggregation_interval=60
        )

        # Simulate sustained load
        for i in range(100):
            # Record metrics
            performance_monitor.record_operation(
                service_name=f"service_{i % 10}",
                operation="api_call",
                response_time_ms=0.001,
                success=True,
            )

            # Create some alerts
            if i % 20 == 0:
                await alert_manager.check_service_unavailability(
                    f"service_{i % 5}", ServiceStatus.UNHEALTHY
                )

        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 50MB for this test)
        assert memory_increase < 50.0
