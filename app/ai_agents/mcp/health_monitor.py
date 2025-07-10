"""
Health monitoring system for MCP services.

This module provides comprehensive health monitoring for all MCP services including:
- Periodic health checks (every 5 minutes)
- Performance metrics collection
- Automated alerting for service failures
- Service availability tracking
- Response time monitoring
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, Callable, Set, Union, Awaitable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
from collections import defaultdict, deque
import statistics
import httpx

from app.ai_agents.mcp.error_handler import (
    MCPConnectionError,
    MCPOperationError,
    MCPTimeoutError,
    MCPAuthenticationError,
)


class ServiceStatus(Enum):
    """Possible service status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class HealthCheckResult:
    """Result of a health check operation."""

    service_name: str
    status: ServiceStatus
    response_time_ms: float
    timestamp: datetime
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "service_name": self.service_name,
            "status": self.status.value,
            "response_time_ms": self.response_time_ms,
            "timestamp": self.timestamp.isoformat(),
            "error_message": self.error_message,
            "details": self.details,
        }


@dataclass
class ServiceMetrics:
    """Performance metrics for a service."""

    service_name: str
    total_checks: int = 0
    successful_checks: int = 0
    failed_checks: int = 0
    avg_response_time: float = 0.0
    min_response_time: float = float("inf")
    max_response_time: float = 0.0
    last_check_time: Optional[datetime] = None
    last_successful_check: Optional[datetime] = None
    current_status: ServiceStatus = ServiceStatus.UNKNOWN
    consecutive_failures: int = 0
    uptime_percentage: float = 100.0

    # Response time history (last 100 checks)
    response_times: deque = field(default_factory=lambda: deque(maxlen=100))

    def update_metrics(self, result: HealthCheckResult) -> None:
        """Update metrics with a new health check result."""
        self.total_checks += 1
        self.last_check_time = result.timestamp
        self.current_status = result.status

        if result.status == ServiceStatus.HEALTHY:
            self.successful_checks += 1
            self.last_successful_check = result.timestamp
            self.consecutive_failures = 0
        else:
            self.failed_checks += 1
            self.consecutive_failures += 1

        # Update response time metrics
        response_time = result.response_time_ms
        self.response_times.append(response_time)

        if response_time < self.min_response_time:
            self.min_response_time = response_time
        if response_time > self.max_response_time:
            self.max_response_time = response_time

        # Calculate average response time
        if self.response_times:
            self.avg_response_time = statistics.mean(self.response_times)

        # Calculate uptime percentage
        if self.total_checks > 0:
            self.uptime_percentage = (self.successful_checks / self.total_checks) * 100

    def get_percentile_response_time(self, percentile: float) -> float:
        """Get response time at specific percentile."""
        if not self.response_times:
            return 0.0

        sorted_times = sorted(self.response_times)
        index = int(len(sorted_times) * percentile / 100)
        return sorted_times[min(index, len(sorted_times) - 1)]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "service_name": self.service_name,
            "total_checks": self.total_checks,
            "successful_checks": self.successful_checks,
            "failed_checks": self.failed_checks,
            "avg_response_time": round(self.avg_response_time, 2),
            "min_response_time": round(self.min_response_time, 2),
            "max_response_time": round(self.max_response_time, 2),
            "last_check_time": self.last_check_time.isoformat()
            if self.last_check_time
            else None,
            "last_successful_check": self.last_successful_check.isoformat()
            if self.last_successful_check
            else None,
            "current_status": self.current_status.value,
            "consecutive_failures": self.consecutive_failures,
            "uptime_percentage": round(self.uptime_percentage, 2),
            "p95_response_time": round(self.get_percentile_response_time(95), 2),
            "p99_response_time": round(self.get_percentile_response_time(99), 2),
        }


@dataclass
class Alert:
    """Represents a system alert."""

    id: str
    service_name: str
    severity: AlertSeverity
    message: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "service_name": self.service_name,
            "severity": self.severity.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "details": self.details,
        }


class MCPHealthMonitor:
    """Main health monitoring system for MCP services."""

    def __init__(
        self,
        check_interval: int = 300,  # 5 minutes
        alert_threshold: int = 3,  # Alert after 3 consecutive failures
        timeout: int = 30,  # 30 second timeout for health checks
        enable_auto_alerts: bool = True,
    ):
        """
        Initialize the health monitor.

        Args:
            check_interval: Time between health checks in seconds
            alert_threshold: Number of consecutive failures before alerting
            timeout: Timeout for individual health checks in seconds
            enable_auto_alerts: Whether to automatically generate alerts
        """
        self.check_interval = check_interval
        self.alert_threshold = alert_threshold
        self.timeout = timeout
        self.enable_auto_alerts = enable_auto_alerts

        # Service monitoring data
        self.metrics: Dict[str, ServiceMetrics] = {}
        self.service_configs: Dict[str, Dict[str, Any]] = {}
        self.health_checkers: Dict[str, Callable] = {}

        # Alert management
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.alert_callbacks: List[
            Union[Callable[[Alert], None], Callable[[Alert], Awaitable[None]]]
        ] = []

        # Monitoring state
        self.is_running = False
        self.monitor_task: Optional[asyncio.Task] = None

        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.setup_structured_logging()

        # Register default health checkers
        self.register_default_health_checkers()

    def setup_structured_logging(self) -> None:
        """Setup structured logging for health monitoring."""
        # Create custom formatter for structured logs
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - "
            "service=%(service_name)s - %(message)s"
        )

        # Configure logger
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def register_service(
        self,
        service_name: str,
        config: Dict[str, Any],
        health_checker: Optional[Callable] = None,
    ) -> None:
        """
        Register a service for monitoring.

        Args:
            service_name: Name of the service
            config: Service configuration including endpoints and credentials
            health_checker: Custom health check function for the service
        """
        self.service_configs[service_name] = config
        self.metrics[service_name] = ServiceMetrics(service_name=service_name)

        if health_checker:
            self.health_checkers[service_name] = health_checker

        self.logger.info(
            f"Registered service for monitoring", extra={"service_name": service_name}
        )

    def register_default_health_checkers(self) -> None:
        """Register default health checkers for known services."""
        self.health_checkers.update(
            {
                "sendgrid": self._check_sendgrid_health,
                "twitter": self._check_twitter_health,
                "calendly": self._check_calendly_health,
                "google_calendar": self._check_google_calendar_health,
                "pipedrive": self._check_pipedrive_health,
                "salesforce": self._check_salesforce_health,
                "zoho": self._check_zoho_health,
                "pipedream": self._check_pipedream_health,
            }
        )

    async def _check_sendgrid_health(self, config: Dict[str, Any]) -> HealthCheckResult:
        """Health check for SendGrid service."""
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {"Authorization": f"Bearer {config.get('api_key')}"}
                response = await client.get(
                    "https://api.sendgrid.com/v3/user/profile", headers=headers
                )

                response_time = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    return HealthCheckResult(
                        service_name="sendgrid",
                        status=ServiceStatus.HEALTHY,
                        response_time_ms=response_time,
                        timestamp=datetime.now(),
                        details={"status_code": response.status_code},
                    )
                else:
                    return HealthCheckResult(
                        service_name="sendgrid",
                        status=ServiceStatus.DEGRADED,
                        response_time_ms=response_time,
                        timestamp=datetime.now(),
                        error_message=f"HTTP {response.status_code}",
                        details={"status_code": response.status_code},
                    )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service_name="sendgrid",
                status=ServiceStatus.UNHEALTHY,
                response_time_ms=response_time,
                timestamp=datetime.now(),
                error_message=str(e),
            )

    async def _check_twitter_health(self, config: Dict[str, Any]) -> HealthCheckResult:
        """Health check for Twitter service."""
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {"Authorization": f"Bearer {config.get('bearer_token')}"}
                response = await client.get(
                    "https://api.twitter.com/2/users/me", headers=headers
                )

                response_time = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    return HealthCheckResult(
                        service_name="twitter",
                        status=ServiceStatus.HEALTHY,
                        response_time_ms=response_time,
                        timestamp=datetime.now(),
                        details={"status_code": response.status_code},
                    )
                else:
                    return HealthCheckResult(
                        service_name="twitter",
                        status=ServiceStatus.DEGRADED,
                        response_time_ms=response_time,
                        timestamp=datetime.now(),
                        error_message=f"HTTP {response.status_code}",
                        details={"status_code": response.status_code},
                    )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service_name="twitter",
                status=ServiceStatus.UNHEALTHY,
                response_time_ms=response_time,
                timestamp=datetime.now(),
                error_message=str(e),
            )

    async def _check_calendly_health(self, config: Dict[str, Any]) -> HealthCheckResult:
        """Health check for Calendly service."""
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {"Authorization": f"Bearer {config.get('access_token')}"}
                response = await client.get(
                    "https://api.calendly.com/users/me", headers=headers
                )

                response_time = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    return HealthCheckResult(
                        service_name="calendly",
                        status=ServiceStatus.HEALTHY,
                        response_time_ms=response_time,
                        timestamp=datetime.now(),
                        details={"status_code": response.status_code},
                    )
                else:
                    return HealthCheckResult(
                        service_name="calendly",
                        status=ServiceStatus.DEGRADED,
                        response_time_ms=response_time,
                        timestamp=datetime.now(),
                        error_message=f"HTTP {response.status_code}",
                        details={"status_code": response.status_code},
                    )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service_name="calendly",
                status=ServiceStatus.UNHEALTHY,
                response_time_ms=response_time,
                timestamp=datetime.now(),
                error_message=str(e),
            )

    async def _check_google_calendar_health(
        self, config: Dict[str, Any]
    ) -> HealthCheckResult:
        """Health check for Google Calendar service."""
        start_time = time.time()

        try:
            # For Google Calendar, we'll check the calendar list endpoint
            # This would require proper OAuth token handling
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {"Authorization": f"Bearer {config.get('access_token')}"}
                response = await client.get(
                    "https://www.googleapis.com/calendar/v3/users/me/calendarList",
                    headers=headers,
                )

                response_time = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    return HealthCheckResult(
                        service_name="google_calendar",
                        status=ServiceStatus.HEALTHY,
                        response_time_ms=response_time,
                        timestamp=datetime.now(),
                        details={"status_code": response.status_code},
                    )
                else:
                    return HealthCheckResult(
                        service_name="google_calendar",
                        status=ServiceStatus.DEGRADED,
                        response_time_ms=response_time,
                        timestamp=datetime.now(),
                        error_message=f"HTTP {response.status_code}",
                        details={"status_code": response.status_code},
                    )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service_name="google_calendar",
                status=ServiceStatus.UNHEALTHY,
                response_time_ms=response_time,
                timestamp=datetime.now(),
                error_message=str(e),
            )

    async def _check_pipedrive_health(
        self, config: Dict[str, Any]
    ) -> HealthCheckResult:
        """Health check for Pipedrive service."""
        start_time = time.time()

        try:
            base_url = config.get("base_url", "https://api.pipedrive.com/v1")
            api_token = config.get("api_token")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{base_url}/users/me", params={"api_token": api_token}
                )

                response_time = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    return HealthCheckResult(
                        service_name="pipedrive",
                        status=ServiceStatus.HEALTHY,
                        response_time_ms=response_time,
                        timestamp=datetime.now(),
                        details={"status_code": response.status_code},
                    )
                else:
                    return HealthCheckResult(
                        service_name="pipedrive",
                        status=ServiceStatus.DEGRADED,
                        response_time_ms=response_time,
                        timestamp=datetime.now(),
                        error_message=f"HTTP {response.status_code}",
                        details={"status_code": response.status_code},
                    )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service_name="pipedrive",
                status=ServiceStatus.UNHEALTHY,
                response_time_ms=response_time,
                timestamp=datetime.now(),
                error_message=str(e),
            )

    async def _check_salesforce_health(
        self, config: Dict[str, Any]
    ) -> HealthCheckResult:
        """Health check for Salesforce service."""
        start_time = time.time()

        try:
            # Salesforce health check would use the identity endpoint
            instance_url = config.get("instance_url")
            access_token = config.get("access_token")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {"Authorization": f"Bearer {access_token}"}
                response = await client.get(
                    f"{instance_url}/services/data/v54.0/sobjects/", headers=headers
                )

                response_time = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    return HealthCheckResult(
                        service_name="salesforce",
                        status=ServiceStatus.HEALTHY,
                        response_time_ms=response_time,
                        timestamp=datetime.now(),
                        details={"status_code": response.status_code},
                    )
                else:
                    return HealthCheckResult(
                        service_name="salesforce",
                        status=ServiceStatus.DEGRADED,
                        response_time_ms=response_time,
                        timestamp=datetime.now(),
                        error_message=f"HTTP {response.status_code}",
                        details={"status_code": response.status_code},
                    )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service_name="salesforce",
                status=ServiceStatus.UNHEALTHY,
                response_time_ms=response_time,
                timestamp=datetime.now(),
                error_message=str(e),
            )

    async def _check_zoho_health(self, config: Dict[str, Any]) -> HealthCheckResult:
        """Health check for Zoho CRM service."""
        start_time = time.time()

        try:
            api_domain = config.get("api_domain", "www.zohoapis.com")
            access_token = config.get("access_token")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
                response = await client.get(
                    f"https://{api_domain}/crm/v2/org", headers=headers
                )

                response_time = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    return HealthCheckResult(
                        service_name="zoho",
                        status=ServiceStatus.HEALTHY,
                        response_time_ms=response_time,
                        timestamp=datetime.now(),
                        details={"status_code": response.status_code},
                    )
                else:
                    return HealthCheckResult(
                        service_name="zoho",
                        status=ServiceStatus.DEGRADED,
                        response_time_ms=response_time,
                        timestamp=datetime.now(),
                        error_message=f"HTTP {response.status_code}",
                        details={"status_code": response.status_code},
                    )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service_name="zoho",
                status=ServiceStatus.UNHEALTHY,
                response_time_ms=response_time,
                timestamp=datetime.now(),
                error_message=str(e),
            )

    async def _check_pipedream_health(
        self, config: Dict[str, Any]
    ) -> HealthCheckResult:
        """Health check for Pipedream service."""
        start_time = time.time()

        try:
            base_url = config.get("base_url", "https://api.pipedream.com/v1")
            api_key = config.get("api_key")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {"Authorization": f"Bearer {api_key}"}
                response = await client.get(f"{base_url}/users/me", headers=headers)

                response_time = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    return HealthCheckResult(
                        service_name="pipedream",
                        status=ServiceStatus.HEALTHY,
                        response_time_ms=response_time,
                        timestamp=datetime.now(),
                        details={"status_code": response.status_code},
                    )
                else:
                    return HealthCheckResult(
                        service_name="pipedream",
                        status=ServiceStatus.DEGRADED,
                        response_time_ms=response_time,
                        timestamp=datetime.now(),
                        error_message=f"HTTP {response.status_code}",
                        details={"status_code": response.status_code},
                    )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service_name="pipedream",
                status=ServiceStatus.UNHEALTHY,
                response_time_ms=response_time,
                timestamp=datetime.now(),
                error_message=str(e),
            )

    async def check_service_health(self, service_name: str) -> HealthCheckResult:
        """
        Perform health check for a specific service.

        Args:
            service_name: Name of the service to check

        Returns:
            HealthCheckResult with the check results
        """
        if service_name not in self.service_configs:
            return HealthCheckResult(
                service_name=service_name,
                status=ServiceStatus.UNKNOWN,
                response_time_ms=0,
                timestamp=datetime.now(),
                error_message="Service not configured",
            )

        config = self.service_configs[service_name]
        health_checker = self.health_checkers.get(service_name)

        if not health_checker:
            return HealthCheckResult(
                service_name=service_name,
                status=ServiceStatus.UNKNOWN,
                response_time_ms=0,
                timestamp=datetime.now(),
                error_message="No health checker available",
            )

        try:
            result = await health_checker(config)

            # Update metrics
            if service_name in self.metrics:
                self.metrics[service_name].update_metrics(result)

            # Log the result
            self.logger.info(
                f"Health check completed - status: {result.status.value}, "
                f"response_time: {result.response_time_ms:.2f}ms",
                extra={
                    "service_name": service_name,
                    "status": result.status.value,
                    "response_time_ms": result.response_time_ms,
                },
            )

            # Check if we need to generate alerts
            if self.enable_auto_alerts:
                await self._check_alert_conditions(service_name, result)

            return result

        except Exception as e:
            self.logger.error(
                f"Health check failed with exception: {str(e)}",
                extra={"service_name": service_name},
            )

            return HealthCheckResult(
                service_name=service_name,
                status=ServiceStatus.UNHEALTHY,
                response_time_ms=0,
                timestamp=datetime.now(),
                error_message=f"Health check exception: {str(e)}",
            )

    async def check_all_services(self) -> Dict[str, HealthCheckResult]:
        """
        Perform health checks for all registered services.

        Returns:
            Dictionary mapping service names to their health check results
        """
        results = {}
        tasks = []

        for service_name in self.service_configs.keys():
            task = asyncio.create_task(
                self.check_service_health(service_name),
                name=f"health_check_{service_name}",
            )
            tasks.append((service_name, task))

        # Wait for all health checks to complete
        for service_name, task in tasks:
            try:
                result = await task
                results[service_name] = result
            except Exception as e:
                self.logger.error(
                    f"Failed to complete health check: {str(e)}",
                    extra={"service_name": service_name},
                )
                results[service_name] = HealthCheckResult(
                    service_name=service_name,
                    status=ServiceStatus.UNHEALTHY,
                    response_time_ms=0,
                    timestamp=datetime.now(),
                    error_message=str(e),
                )

        return results

    async def _check_alert_conditions(
        self, service_name: str, result: HealthCheckResult
    ) -> None:
        """Check if alert conditions are met and generate alerts if needed."""
        metrics = self.metrics.get(service_name)
        if not metrics:
            return

        # Check for consecutive failures
        if metrics.consecutive_failures >= self.alert_threshold:
            alert_id = f"consecutive_failures_{service_name}"

            if alert_id not in self.active_alerts:
                alert = Alert(
                    id=alert_id,
                    service_name=service_name,
                    severity=AlertSeverity.ERROR,
                    message=f"Service {service_name} has failed {metrics.consecutive_failures} consecutive health checks",
                    timestamp=datetime.now(),
                    details={
                        "consecutive_failures": metrics.consecutive_failures,
                        "last_error": result.error_message,
                        "current_status": result.status.value,
                    },
                )
                await self._generate_alert(alert)

        # Check for extended downtime (> 2 minutes)
        if (
            metrics.last_successful_check
            and datetime.now() - metrics.last_successful_check > timedelta(minutes=2)
        ):
            alert_id = f"extended_downtime_{service_name}"

            if alert_id not in self.active_alerts:
                downtime_minutes = (
                    datetime.now() - metrics.last_successful_check
                ).total_seconds() / 60
                alert = Alert(
                    id=alert_id,
                    service_name=service_name,
                    severity=AlertSeverity.CRITICAL,
                    message=f"Service {service_name} has been unavailable for {downtime_minutes:.1f} minutes",
                    timestamp=datetime.now(),
                    details={
                        "downtime_minutes": downtime_minutes,
                        "last_successful_check": metrics.last_successful_check.isoformat(),
                    },
                )
                await self._generate_alert(alert)

        # Check for high response times
        if result.response_time_ms > 5000:  # 5 seconds
            alert_id = f"high_response_time_{service_name}"

            # Only alert if this is a pattern, not a one-off
            if metrics.avg_response_time > 3000 and alert_id not in self.active_alerts:
                alert = Alert(
                    id=alert_id,
                    service_name=service_name,
                    severity=AlertSeverity.WARNING,
                    message=f"Service {service_name} has high response times (avg: {metrics.avg_response_time:.0f}ms)",
                    timestamp=datetime.now(),
                    details={
                        "current_response_time": result.response_time_ms,
                        "avg_response_time": metrics.avg_response_time,
                        "p95_response_time": metrics.get_percentile_response_time(95),
                    },
                )
                await self._generate_alert(alert)

        # Check if service has recovered and resolve alerts
        if result.status == ServiceStatus.HEALTHY:
            await self._resolve_service_alerts(service_name)

    async def _generate_alert(self, alert: Alert) -> None:
        """Generate and process a new alert."""
        self.active_alerts[alert.id] = alert
        self.alert_history.append(alert)

        self.logger.warning(
            f"ALERT GENERATED: {alert.message}",
            extra={
                "service_name": alert.service_name,
                "alert_id": alert.id,
                "severity": alert.severity.value,
            },
        )

        # Notify alert callbacks
        for callback in self.alert_callbacks:
            try:
                # Check if callback is awaitable
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                self.logger.error(f"Alert callback failed: {str(e)}")

    async def _resolve_service_alerts(self, service_name: str) -> None:
        """Resolve all active alerts for a service."""
        resolved_alerts = []

        for alert_id, alert in self.active_alerts.items():
            if alert.service_name == service_name and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = datetime.now()
                resolved_alerts.append(alert_id)

                self.logger.info(
                    f"ALERT RESOLVED: {alert.message}",
                    extra={"service_name": service_name, "alert_id": alert_id},
                )

        # Remove resolved alerts from active alerts
        for alert_id in resolved_alerts:
            del self.active_alerts[alert_id]

    def add_alert_callback(
        self,
        callback: Union[Callable[[Alert], None], Callable[[Alert], Awaitable[None]]],
    ) -> None:
        """Add a callback function to be called when alerts are generated."""
        self.alert_callbacks.append(callback)

    async def start_monitoring(self) -> None:
        """Start the periodic health monitoring."""
        if self.is_running:
            self.logger.warning("Health monitoring is already running")
            return

        self.is_running = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())

        self.logger.info(
            f"Started health monitoring with {self.check_interval}s interval",
            extra={"service_count": len(self.service_configs)},
        )

    async def stop_monitoring(self) -> None:
        """Stop the periodic health monitoring."""
        if not self.is_running:
            return

        self.is_running = False

        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

        self.logger.info("Stopped health monitoring")

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop that runs periodic health checks."""
        self.logger.info("Health monitoring loop started")

        while self.is_running:
            try:
                start_time = time.time()

                # Perform health checks for all services
                results = await self.check_all_services()

                check_duration = time.time() - start_time

                self.logger.info(
                    f"Completed health check cycle in {check_duration:.2f}s",
                    extra={
                        "services_checked": len(results),
                        "cycle_duration": check_duration,
                    },
                )

                # Wait for next check interval
                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                self.logger.info("Health monitoring loop cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {str(e)}")
                # Continue monitoring even if there's an error
                await asyncio.sleep(self.check_interval)

    def get_service_metrics(self, service_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance metrics for services.

        Args:
            service_name: Specific service name, or None for all services

        Returns:
            Dictionary containing metrics data
        """
        if service_name:
            if service_name in self.metrics:
                return {service_name: self.metrics[service_name].to_dict()}
            else:
                return {}
        else:
            return {name: metrics.to_dict() for name, metrics in self.metrics.items()}

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts."""
        return [alert.to_dict() for alert in self.active_alerts.values()]

    def get_alert_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get alert history, optionally limited to recent alerts."""
        alerts = sorted(self.alert_history, key=lambda x: x.timestamp, reverse=True)
        if limit:
            alerts = alerts[:limit]
        return [alert.to_dict() for alert in alerts]

    def get_system_health_summary(self) -> Dict[str, Any]:
        """Get a summary of overall system health."""
        total_services = len(self.metrics)
        healthy_services = sum(
            1
            for m in self.metrics.values()
            if m.current_status == ServiceStatus.HEALTHY
        )
        degraded_services = sum(
            1
            for m in self.metrics.values()
            if m.current_status == ServiceStatus.DEGRADED
        )
        unhealthy_services = sum(
            1
            for m in self.metrics.values()
            if m.current_status == ServiceStatus.UNHEALTHY
        )

        # Calculate overall system health percentage
        if total_services > 0:
            health_percentage = (healthy_services / total_services) * 100
        else:
            health_percentage = 100

        # Determine overall status
        if unhealthy_services > 0:
            overall_status = ServiceStatus.UNHEALTHY
        elif degraded_services > 0:
            overall_status = ServiceStatus.DEGRADED
        else:
            overall_status = ServiceStatus.HEALTHY

        return {
            "overall_status": overall_status.value,
            "health_percentage": round(health_percentage, 1),
            "total_services": total_services,
            "healthy_services": healthy_services,
            "degraded_services": degraded_services,
            "unhealthy_services": unhealthy_services,
            "active_alerts": len(self.active_alerts),
            "monitoring_active": self.is_running,
            "last_check_time": max(
                (m.last_check_time for m in self.metrics.values() if m.last_check_time),
                default=None,
            ),
        }


# Global health monitor instance
health_monitor = MCPHealthMonitor()


def get_health_monitor() -> MCPHealthMonitor:
    """Get the global health monitor instance."""
    return health_monitor
