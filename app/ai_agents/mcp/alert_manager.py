"""
Alert management system for MCP services.

This module provides comprehensive automated alerting for MCP services including:
- Service unavailability alerts (> 2 minutes)
- Rate limiting alerts for external APIs
- Critical OAuth authentication failure alerts
- Alert escalation and notification routing
- Alert suppression and grouping
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Callable, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict, deque
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import httpx
import logging

from app.ai_agents.mcp.structured_logger import get_mcp_logger, OperationType
from app.ai_agents.mcp.health_monitor import (
    ServiceStatus,
    Alert as HealthAlert,
    AlertSeverity,
)


class AlertType(Enum):
    """Types of alerts that can be generated."""

    SERVICE_UNAVAILABLE = "service_unavailable"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    AUTHENTICATION_FAILURE = "authentication_failure"
    HIGH_ERROR_RATE = "high_error_rate"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    CONFIGURATION_ERROR = "configuration_error"
    SYSTEM_OVERLOAD = "system_overload"


class AlertChannel(Enum):
    """Available alert notification channels."""

    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    DISCORD = "discord"
    TEAMS = "teams"


class AlertStatus(Enum):
    """Status of an alert."""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class AlertRule:
    """Definition of an alert rule."""

    id: str
    name: str
    alert_type: AlertType
    description: str
    enabled: bool = True

    # Conditions
    service_names: Optional[List[str]] = None  # None means all services
    threshold_value: Optional[float] = None
    threshold_duration_minutes: Optional[int] = None
    error_rate_threshold: Optional[float] = None

    # Alert configuration
    severity: AlertSeverity = AlertSeverity.WARNING
    channels: List[AlertChannel] = field(default_factory=list)
    escalation_delay_minutes: int = 30
    auto_resolve: bool = True
    suppression_duration_minutes: int = 60

    # Notification settings
    notification_template: Optional[str] = None
    include_metrics: bool = True
    include_logs: bool = False

    def matches_service(self, service_name: str) -> bool:
        """Check if this rule applies to a service."""
        return self.service_names is None or service_name in self.service_names

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        result["alert_type"] = self.alert_type.value
        result["severity"] = self.severity.value
        result["channels"] = [c.value for c in self.channels]
        return result


@dataclass
class AlertEvent:
    """Represents an alert event in the system."""

    id: str
    rule_id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    service_name: str
    timestamp: datetime
    status: AlertStatus = AlertStatus.ACTIVE

    # Context and metadata
    triggered_by: Optional[str] = None
    context_data: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)

    # Lifecycle tracking
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    last_updated: Optional[datetime] = None

    # Notification tracking
    notifications_sent: List[Dict[str, Any]] = field(default_factory=list)
    escalation_level: int = 0
    next_escalation_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        result["alert_type"] = self.alert_type.value
        result["severity"] = self.severity.value
        result["status"] = self.status.value
        result["timestamp"] = self.timestamp.isoformat()

        if self.acknowledged_at:
            result["acknowledged_at"] = self.acknowledged_at.isoformat()
        if self.resolved_at:
            result["resolved_at"] = self.resolved_at.isoformat()
        if self.last_updated:
            result["last_updated"] = self.last_updated.isoformat()
        if self.next_escalation_at:
            result["next_escalation_at"] = self.next_escalation_at.isoformat()

        return result

    def update_status(
        self, status: AlertStatus, updated_by: Optional[str] = None
    ) -> None:
        """Update alert status with timestamp."""
        self.status = status
        self.last_updated = datetime.now()

        if status == AlertStatus.ACKNOWLEDGED:
            self.acknowledged_at = self.last_updated
            self.acknowledged_by = updated_by
        elif status == AlertStatus.RESOLVED:
            self.resolved_at = self.last_updated
            self.resolved_by = updated_by


@dataclass
class NotificationChannel:
    """Configuration for a notification channel."""

    channel_type: AlertChannel
    name: str
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)

    # Rate limiting
    max_notifications_per_hour: int = 60
    notification_count: int = 0
    last_reset_time: datetime = field(default_factory=datetime.now)

    def can_send_notification(self) -> bool:
        """Check if channel can send a notification (rate limiting)."""
        now = datetime.now()

        # Reset counter if an hour has passed
        if now - self.last_reset_time >= timedelta(hours=1):
            self.notification_count = 0
            self.last_reset_time = now

        return (
            self.enabled and self.notification_count < self.max_notifications_per_hour
        )

    def record_notification(self) -> None:
        """Record that a notification was sent."""
        self.notification_count += 1


class MCPAlertManager:
    """Main alert management system for MCP services."""

    def __init__(
        self,
        enable_auto_alerts: bool = True,
        alert_check_interval: int = 60,  # Check every minute
        max_active_alerts: int = 1000,
    ):
        """
        Initialize the alert manager.

        Args:
            enable_auto_alerts: Whether to automatically generate alerts
            alert_check_interval: How often to check for alert conditions (seconds)
            max_active_alerts: Maximum number of active alerts to maintain
        """
        self.enable_auto_alerts = enable_auto_alerts
        self.alert_check_interval = alert_check_interval
        self.max_active_alerts = max_active_alerts

        # Alert storage
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, AlertEvent] = {}
        self.alert_history: deque = deque(maxlen=10000)

        # Notification channels
        self.notification_channels: Dict[str, NotificationChannel] = {}

        # Suppression tracking
        self.suppressed_alerts: Dict[str, datetime] = {}

        # State tracking for alert conditions
        self.service_downtime: Dict[str, datetime] = {}
        self.rate_limit_incidents: Dict[str, List[datetime]] = defaultdict(list)
        self.auth_failure_incidents: Dict[str, List[datetime]] = defaultdict(list)

        # Background tasks
        self.monitor_task: Optional[asyncio.Task] = None
        self.is_running = False

        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.mcp_logger = get_mcp_logger()

        # Register default alert rules
        self.register_default_alert_rules()

        # Register default notification channels
        self.register_default_notification_channels()

    def register_default_alert_rules(self) -> None:
        """Register default alert rules for common scenarios."""
        # Service unavailability alert (> 2 minutes)
        self.add_alert_rule(
            AlertRule(
                id="service_unavailable_2min",
                name="Service Unavailable > 2 Minutes",
                alert_type=AlertType.SERVICE_UNAVAILABLE,
                description="Alert when a service is unavailable for more than 2 minutes",
                threshold_duration_minutes=2,
                severity=AlertSeverity.CRITICAL,
                channels=[AlertChannel.EMAIL, AlertChannel.SLACK],
                escalation_delay_minutes=15,
            )
        )

        # Rate limiting alert
        self.add_alert_rule(
            AlertRule(
                id="rate_limit_exceeded",
                name="API Rate Limit Exceeded",
                alert_type=AlertType.RATE_LIMIT_EXCEEDED,
                description="Alert when API rate limits are exceeded",
                threshold_value=5,  # 5 rate limit hits in window
                threshold_duration_minutes=5,
                severity=AlertSeverity.WARNING,
                channels=[AlertChannel.EMAIL],
                escalation_delay_minutes=30,
            )
        )

        # Authentication failure alert
        self.add_alert_rule(
            AlertRule(
                id="auth_failure_critical",
                name="Critical OAuth Authentication Failures",
                alert_type=AlertType.AUTHENTICATION_FAILURE,
                description="Alert on critical OAuth authentication failures",
                threshold_value=3,  # 3 failures in window
                threshold_duration_minutes=10,
                severity=AlertSeverity.ERROR,
                channels=[AlertChannel.EMAIL, AlertChannel.SLACK],
                escalation_delay_minutes=20,
            )
        )

        # High error rate alert
        self.add_alert_rule(
            AlertRule(
                id="high_error_rate",
                name="High Error Rate",
                alert_type=AlertType.HIGH_ERROR_RATE,
                description="Alert when error rate exceeds threshold",
                error_rate_threshold=25.0,  # 25% error rate
                threshold_duration_minutes=5,
                severity=AlertSeverity.WARNING,
                channels=[AlertChannel.EMAIL],
                escalation_delay_minutes=45,
            )
        )

        # Performance degradation alert
        self.add_alert_rule(
            AlertRule(
                id="performance_degradation",
                name="Performance Degradation",
                alert_type=AlertType.PERFORMANCE_DEGRADATION,
                description="Alert when response times are consistently high",
                threshold_value=5000,  # 5 second response time
                threshold_duration_minutes=10,
                severity=AlertSeverity.WARNING,
                channels=[AlertChannel.EMAIL],
                escalation_delay_minutes=60,
            )
        )

    def register_default_notification_channels(self) -> None:
        """Register default notification channels."""
        # Email channel
        self.add_notification_channel(
            NotificationChannel(
                channel_type=AlertChannel.EMAIL,
                name="default_email",
                config={
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587,
                    "from_email": "alerts@pipewise.com",
                    "to_emails": ["admin@pipewise.com"],
                    "use_tls": True,
                },
            )
        )

        # Slack channel
        self.add_notification_channel(
            NotificationChannel(
                channel_type=AlertChannel.SLACK,
                name="default_slack",
                config={
                    "webhook_url": "",  # To be configured
                    "channel": "#alerts",
                    "username": "PipeWise Alert Bot",
                },
            )
        )

        # Webhook channel
        self.add_notification_channel(
            NotificationChannel(
                channel_type=AlertChannel.WEBHOOK,
                name="default_webhook",
                config={
                    "url": "",  # To be configured
                    "method": "POST",
                    "headers": {"Content-Type": "application/json"},
                },
            )
        )

    def add_alert_rule(self, rule: AlertRule) -> None:
        """Add or update an alert rule."""
        self.alert_rules[rule.id] = rule
        self.logger.info(f"Added alert rule: {rule.name} ({rule.id})")

    def remove_alert_rule(self, rule_id: str) -> bool:
        """Remove an alert rule."""
        if rule_id in self.alert_rules:
            del self.alert_rules[rule_id]
            self.logger.info(f"Removed alert rule: {rule_id}")
            return True
        return False

    def add_notification_channel(self, channel: NotificationChannel) -> None:
        """Add or update a notification channel."""
        self.notification_channels[channel.name] = channel
        self.logger.info(f"Added notification channel: {channel.name}")

    def remove_notification_channel(self, channel_name: str) -> bool:
        """Remove a notification channel."""
        if channel_name in self.notification_channels:
            del self.notification_channels[channel_name]
            self.logger.info(f"Removed notification channel: {channel_name}")
            return True
        return False

    async def check_service_unavailability(
        self, service_name: str, status: ServiceStatus
    ) -> None:
        """Check for service unavailability conditions."""
        now = datetime.now()

        if status in [ServiceStatus.UNHEALTHY, ServiceStatus.UNKNOWN]:
            # Service is down, track downtime
            if service_name not in self.service_downtime:
                self.service_downtime[service_name] = now

            # Check if downtime exceeds threshold
            downtime_duration = now - self.service_downtime[service_name]

            for rule in self.alert_rules.values():
                if (
                    rule.alert_type == AlertType.SERVICE_UNAVAILABLE
                    and rule.enabled
                    and rule.matches_service(service_name)
                ):
                    threshold_minutes = rule.threshold_duration_minutes or 2

                    if downtime_duration >= timedelta(minutes=threshold_minutes):
                        alert_id = f"service_unavailable_{service_name}_{rule.id}"

                        if alert_id not in self.active_alerts:
                            await self._create_alert(
                                alert_id=alert_id,
                                rule=rule,
                                service_name=service_name,
                                title=f"Service {service_name} Unavailable",
                                message=f"Service {service_name} has been unavailable for {downtime_duration.total_seconds() / 60:.1f} minutes",
                                context_data={
                                    "downtime_minutes": downtime_duration.total_seconds()
                                    / 60,
                                    "service_status": status.value,
                                    "threshold_minutes": threshold_minutes,
                                },
                            )
        else:
            # Service is healthy, clear downtime tracking and resolve alerts
            if service_name in self.service_downtime:
                del self.service_downtime[service_name]
                await self._resolve_service_alerts(
                    service_name, AlertType.SERVICE_UNAVAILABLE
                )

    async def check_rate_limiting(
        self, service_name: str, rate_limit_hit: bool
    ) -> None:
        """Check for rate limiting conditions."""
        if not rate_limit_hit:
            return

        now = datetime.now()
        incidents = self.rate_limit_incidents[service_name]

        # Add current incident
        incidents.append(now)

        # Clean up old incidents (older than 1 hour)
        cutoff_time = now - timedelta(hours=1)
        self.rate_limit_incidents[service_name] = [
            incident for incident in incidents if incident >= cutoff_time
        ]

        # Check alert rules
        for rule in self.alert_rules.values():
            if (
                rule.alert_type == AlertType.RATE_LIMIT_EXCEEDED
                and rule.enabled
                and rule.matches_service(service_name)
            ):
                threshold_value = rule.threshold_value or 5
                threshold_minutes = rule.threshold_duration_minutes or 5

                # Count incidents in the threshold window
                window_start = now - timedelta(minutes=threshold_minutes)
                recent_incidents = [
                    incident
                    for incident in self.rate_limit_incidents[service_name]
                    if incident >= window_start
                ]

                if len(recent_incidents) >= threshold_value:
                    alert_id = f"rate_limit_exceeded_{service_name}_{rule.id}"

                    if alert_id not in self.active_alerts:
                        await self._create_alert(
                            alert_id=alert_id,
                            rule=rule,
                            service_name=service_name,
                            title=f"Rate Limit Exceeded - {service_name}",
                            message=f"Service {service_name} has hit rate limits {len(recent_incidents)} times in the last {threshold_minutes} minutes",
                            context_data={
                                "incidents_count": len(recent_incidents),
                                "threshold_value": threshold_value,
                                "threshold_minutes": threshold_minutes,
                                "recent_incidents": [
                                    inc.isoformat() for inc in recent_incidents
                                ],
                            },
                        )

    async def check_authentication_failures(
        self,
        service_name: str,
        user_id: str,
        auth_failed: bool,
        error_code: Optional[str] = None,
    ) -> None:
        """Check for authentication failure conditions."""
        if not auth_failed:
            return

        now = datetime.now()
        key = f"{service_name}:{user_id}"
        incidents = self.auth_failure_incidents[key]

        # Add current failure
        incidents.append(now)

        # Clean up old incidents (older than 1 hour)
        cutoff_time = now - timedelta(hours=1)
        self.auth_failure_incidents[key] = [
            incident for incident in incidents if incident >= cutoff_time
        ]

        # Check alert rules
        for rule in self.alert_rules.values():
            if (
                rule.alert_type == AlertType.AUTHENTICATION_FAILURE
                and rule.enabled
                and rule.matches_service(service_name)
            ):
                threshold_value = rule.threshold_value or 3
                threshold_minutes = rule.threshold_duration_minutes or 10

                # Count failures in the threshold window
                window_start = now - timedelta(minutes=threshold_minutes)
                recent_failures = [
                    incident
                    for incident in self.auth_failure_incidents[key]
                    if incident >= window_start
                ]

                if len(recent_failures) >= threshold_value:
                    alert_id = f"auth_failure_{service_name}_{user_id}_{rule.id}"

                    if alert_id not in self.active_alerts:
                        await self._create_alert(
                            alert_id=alert_id,
                            rule=rule,
                            service_name=service_name,
                            title=f"Authentication Failures - {service_name}",
                            message=f"User {user_id} has failed authentication {len(recent_failures)} times for {service_name} in the last {threshold_minutes} minutes",
                            context_data={
                                "user_id": user_id,
                                "failures_count": len(recent_failures),
                                "threshold_value": threshold_value,
                                "threshold_minutes": threshold_minutes,
                                "error_code": error_code,
                                "recent_failures": [
                                    inc.isoformat() for inc in recent_failures
                                ],
                            },
                        )

    async def _create_alert(
        self,
        alert_id: str,
        rule: AlertRule,
        service_name: str,
        title: str,
        message: str,
        context_data: Dict[str, Any],
    ) -> Optional[AlertEvent]:
        """Create a new alert event."""
        # Check if alert is suppressed
        if self._is_alert_suppressed(alert_id, rule):
            return None

        # Create alert event
        alert = AlertEvent(
            id=alert_id,
            rule_id=rule.id,
            alert_type=rule.alert_type,
            severity=rule.severity,
            title=title,
            message=message,
            service_name=service_name,
            timestamp=datetime.now(),
            context_data=context_data,
            next_escalation_at=datetime.now()
            + timedelta(minutes=rule.escalation_delay_minutes),
        )

        # Store alert
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)

        # Log alert creation
        with self.mcp_logger.operation_context(
            OperationType.AGENT_WORKFLOW, service_name=service_name
        ):
            self.mcp_logger.log_error(
                Exception(f"Alert created: {title}"),
                service_name=service_name,
                operation="alert_creation",
                context_data=context_data,
            )

        self.logger.warning(f"Alert created: {title} ({alert_id})")

        # Send notifications
        await self._send_alert_notifications(alert, rule)

        # Clean up old alerts if we exceed the limit
        if len(self.active_alerts) > self.max_active_alerts:
            await self._cleanup_old_alerts()

        return alert

    def _is_alert_suppressed(self, alert_id: str, rule: AlertRule) -> bool:
        """Check if an alert is currently suppressed."""
        if alert_id in self.suppressed_alerts:
            suppression_end = self.suppressed_alerts[alert_id] + timedelta(
                minutes=rule.suppression_duration_minutes
            )
            if datetime.now() < suppression_end:
                return True
            else:
                # Suppression period ended
                del self.suppressed_alerts[alert_id]

        return False

    async def _send_alert_notifications(
        self, alert: AlertEvent, rule: AlertRule
    ) -> None:
        """Send notifications for an alert."""
        for channel_type in rule.channels:
            # Find matching notification channel
            channel = None
            for ch in self.notification_channels.values():
                if ch.channel_type == channel_type and ch.can_send_notification():
                    channel = ch
                    break

            if not channel:
                self.logger.warning(
                    f"No available {channel_type.value} channel for alert {alert.id}"
                )
                continue

            try:
                success = await self._send_notification(channel, alert, rule)

                if success:
                    channel.record_notification()
                    alert.notifications_sent.append(
                        {
                            "channel": channel.name,
                            "channel_type": channel_type.value,
                            "timestamp": datetime.now().isoformat(),
                            "success": True,
                        }
                    )
                else:
                    alert.notifications_sent.append(
                        {
                            "channel": channel.name,
                            "channel_type": channel_type.value,
                            "timestamp": datetime.now().isoformat(),
                            "success": False,
                            "error": "Notification failed",
                        }
                    )

            except Exception as e:
                self.logger.error(
                    f"Failed to send notification via {channel.name}: {str(e)}"
                )
                alert.notifications_sent.append(
                    {
                        "channel": channel.name,
                        "channel_type": channel_type.value,
                        "timestamp": datetime.now().isoformat(),
                        "success": False,
                        "error": str(e),
                    }
                )

    async def _send_notification(
        self, channel: NotificationChannel, alert: AlertEvent, rule: AlertRule
    ) -> bool:
        """Send a notification through a specific channel."""
        try:
            if channel.channel_type == AlertChannel.EMAIL:
                return await self._send_email_notification(channel, alert, rule)
            elif channel.channel_type == AlertChannel.SLACK:
                return await self._send_slack_notification(channel, alert, rule)
            elif channel.channel_type == AlertChannel.WEBHOOK:
                return await self._send_webhook_notification(channel, alert, rule)
            else:
                self.logger.warning(
                    f"Unsupported notification channel: {channel.channel_type}"
                )
                return False

        except Exception as e:
            self.logger.error(f"Notification send failed: {str(e)}")
            return False

    async def _send_email_notification(
        self, channel: NotificationChannel, alert: AlertEvent, rule: AlertRule
    ) -> bool:
        """Send email notification."""
        config = channel.config

        # Create email message
        msg = MIMEMultipart()
        msg["From"] = config.get("from_email", "alerts@pipewise.com")
        msg["To"] = ", ".join(config.get("to_emails", []))
        msg["Subject"] = f"[{alert.severity.value.upper()}] {alert.title}"

        # Email body
        body = self._format_alert_message(alert, rule, format_type="email")
        msg.attach(MIMEText(body, "html"))

        # Send email
        try:
            server = smtplib.SMTP(config["smtp_server"], config["smtp_port"])
            if config.get("use_tls", True):
                server.starttls()

            if config.get("username") and config.get("password"):
                server.login(config["username"], config["password"])

            server.send_message(msg)
            server.quit()
            return True

        except Exception as e:
            self.logger.error(f"Email send failed: {str(e)}")
            return False

    async def _send_slack_notification(
        self, channel: NotificationChannel, alert: AlertEvent, rule: AlertRule
    ) -> bool:
        """Send Slack notification."""
        config = channel.config
        webhook_url = config.get("webhook_url")

        if not webhook_url:
            self.logger.warning("Slack webhook URL not configured")
            return False

        # Create Slack message
        color = {
            AlertSeverity.INFO: "good",
            AlertSeverity.WARNING: "warning",
            AlertSeverity.ERROR: "danger",
            AlertSeverity.CRITICAL: "danger",
        }.get(alert.severity, "warning")

        message = {
            "channel": config.get("channel", "#alerts"),
            "username": config.get("username", "PipeWise Alert Bot"),
            "attachments": [
                {
                    "color": color,
                    "title": alert.title,
                    "text": alert.message,
                    "fields": [
                        {
                            "title": "Service",
                            "value": alert.service_name,
                            "short": True,
                        },
                        {
                            "title": "Severity",
                            "value": alert.severity.value.upper(),
                            "short": True,
                        },
                        {
                            "title": "Time",
                            "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                            "short": True,
                        },
                    ],
                    "footer": "PipeWise MCP Alert System",
                }
            ],
        }

        # Send to Slack
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=message)
                return response.status_code == 200

        except Exception as e:
            self.logger.error(f"Slack notification failed: {str(e)}")
            return False

    async def _send_webhook_notification(
        self, channel: NotificationChannel, alert: AlertEvent, rule: AlertRule
    ) -> bool:
        """Send webhook notification."""
        config = channel.config
        url = config.get("url")

        if not url:
            self.logger.warning("Webhook URL not configured")
            return False

        # Create webhook payload
        payload = {
            "alert": alert.to_dict(),
            "rule": rule.to_dict(),
            "timestamp": datetime.now().isoformat(),
        }

        # Send webhook
        try:
            headers = config.get("headers", {})
            method = config.get("method", "POST").upper()

            async with httpx.AsyncClient() as client:
                if method == "POST":
                    response = await client.post(url, json=payload, headers=headers)
                elif method == "PUT":
                    response = await client.put(url, json=payload, headers=headers)
                else:
                    self.logger.error(f"Unsupported webhook method: {method}")
                    return False

                return 200 <= response.status_code < 300

        except Exception as e:
            self.logger.error(f"Webhook notification failed: {str(e)}")
            return False

    def _format_alert_message(
        self, alert: AlertEvent, rule: AlertRule, format_type: str = "text"
    ) -> str:
        """Format alert message for different notification types."""
        if format_type == "email":
            return f"""
            <html>
            <body>
                <h2>{alert.title}</h2>
                <p><strong>Severity:</strong> {alert.severity.value.upper()}</p>
                <p><strong>Service:</strong> {alert.service_name}</p>
                <p><strong>Time:</strong> {alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")}</p>
                <p><strong>Message:</strong> {alert.message}</p>
                
                <h3>Alert Details</h3>
                <ul>
                    <li><strong>Rule:</strong> {rule.name}</li>
                    <li><strong>Type:</strong> {alert.alert_type.value}</li>
                    <li><strong>Alert ID:</strong> {alert.id}</li>
                </ul>
                
                <h3>Context Information</h3>
                <pre>{json.dumps(alert.context_data, indent=2)}</pre>
                
                <p><em>This alert was generated by PipeWise MCP Alert System.</em></p>
            </body>
            </html>
            """
        else:
            return f"""
Alert: {alert.title}
Severity: {alert.severity.value.upper()}
Service: {alert.service_name}
Time: {alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")}
Message: {alert.message}

Rule: {rule.name}
Type: {alert.alert_type.value}
Alert ID: {alert.id}

Context: {json.dumps(alert.context_data, indent=2)}
            """

    async def _resolve_service_alerts(
        self, service_name: str, alert_type: AlertType
    ) -> None:
        """Resolve all active alerts of a specific type for a service."""
        alerts_to_resolve = []

        for alert_id, alert in self.active_alerts.items():
            if (
                alert.service_name == service_name
                and alert.alert_type == alert_type
                and alert.status == AlertStatus.ACTIVE
            ):
                alerts_to_resolve.append(alert_id)

        for alert_id in alerts_to_resolve:
            await self.resolve_alert(alert_id, "system", "Service recovered")

    async def _cleanup_old_alerts(self) -> None:
        """Clean up old active alerts to maintain the limit."""
        if len(self.active_alerts) <= self.max_active_alerts:
            return

        # Sort alerts by timestamp (oldest first)
        sorted_alerts = sorted(self.active_alerts.items(), key=lambda x: x[1].timestamp)

        # Remove oldest alerts
        alerts_to_remove = (
            len(self.active_alerts) - self.max_active_alerts + 100
        )  # Remove extra for buffer

        for i in range(min(alerts_to_remove, len(sorted_alerts))):
            alert_id, alert = sorted_alerts[i]
            if alert.status == AlertStatus.ACTIVE:
                await self.resolve_alert(
                    alert_id, "system", "Auto-resolved due to alert limit"
                )
            else:
                del self.active_alerts[alert_id]

    async def acknowledge_alert(
        self, alert_id: str, acknowledged_by: str, notes: str = ""
    ) -> bool:
        """Acknowledge an alert."""
        if alert_id not in self.active_alerts:
            return False

        alert = self.active_alerts[alert_id]
        alert.update_status(AlertStatus.ACKNOWLEDGED, acknowledged_by)

        self.logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
        return True

    async def resolve_alert(
        self, alert_id: str, resolved_by: str, resolution_notes: str = ""
    ) -> bool:
        """Resolve an alert."""
        if alert_id not in self.active_alerts:
            return False

        alert = self.active_alerts[alert_id]
        alert.update_status(AlertStatus.RESOLVED, resolved_by)

        # Add resolution notes to context
        alert.context_data["resolution_notes"] = resolution_notes
        alert.context_data["resolved_by"] = resolved_by

        # Remove from active alerts
        del self.active_alerts[alert_id]

        self.logger.info(f"Alert resolved: {alert_id} by {resolved_by}")
        return True

    async def suppress_alert(
        self, alert_id: str, suppression_duration_minutes: int = 60
    ) -> bool:
        """Suppress an alert for a specified duration."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.update_status(AlertStatus.SUPPRESSED)
            del self.active_alerts[alert_id]

        # Track suppression
        self.suppressed_alerts[alert_id] = datetime.now()

        self.logger.info(
            f"Alert suppressed: {alert_id} for {suppression_duration_minutes} minutes"
        )
        return True

    async def start_monitoring(self) -> None:
        """Start the alert monitoring loop."""
        if self.is_running:
            self.logger.warning("Alert monitoring is already running")
            return

        self.is_running = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())

        self.logger.info("Started alert monitoring")

    async def stop_monitoring(self) -> None:
        """Stop the alert monitoring loop."""
        if not self.is_running:
            return

        self.is_running = False

        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

        self.logger.info("Stopped alert monitoring")

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop for alert conditions."""
        self.logger.info("Alert monitoring loop started")

        while self.is_running:
            try:
                # Check for escalations
                await self._check_escalations()

                # Clean up old incidents
                await self._cleanup_old_incidents()

                # Wait for next check
                await asyncio.sleep(self.alert_check_interval)

            except asyncio.CancelledError:
                self.logger.info("Alert monitoring loop cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in alert monitoring loop: {str(e)}")
                await asyncio.sleep(self.alert_check_interval)

    async def _check_escalations(self) -> None:
        """Check for alerts that need escalation."""
        now = datetime.now()

        for alert in list(self.active_alerts.values()):
            if (
                alert.status == AlertStatus.ACTIVE
                and alert.next_escalation_at
                and now >= alert.next_escalation_at
            ):
                # Escalate alert
                alert.escalation_level += 1
                rule = self.alert_rules.get(alert.rule_id)

                if rule:
                    alert.next_escalation_at = now + timedelta(
                        minutes=rule.escalation_delay_minutes
                    )

                    # Send escalation notification
                    alert.title = f"[ESCALATED {alert.escalation_level}x] {alert.title}"
                    await self._send_alert_notifications(alert, rule)

                    self.logger.warning(
                        f"Alert escalated: {alert.id} (level {alert.escalation_level})"
                    )

    async def _cleanup_old_incidents(self) -> None:
        """Clean up old incident tracking data."""
        cutoff_time = datetime.now() - timedelta(hours=24)

        # Clean rate limit incidents
        for service_name in list(self.rate_limit_incidents.keys()):
            incidents = self.rate_limit_incidents[service_name]
            self.rate_limit_incidents[service_name] = [
                incident for incident in incidents if incident >= cutoff_time
            ]

            if not self.rate_limit_incidents[service_name]:
                del self.rate_limit_incidents[service_name]

        # Clean auth failure incidents
        for key in list(self.auth_failure_incidents.keys()):
            incidents = self.auth_failure_incidents[key]
            self.auth_failure_incidents[key] = [
                incident for incident in incidents if incident >= cutoff_time
            ]

            if not self.auth_failure_incidents[key]:
                del self.auth_failure_incidents[key]

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts."""
        return [alert.to_dict() for alert in self.active_alerts.values()]

    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics."""
        total_active = len(self.active_alerts)
        by_severity = defaultdict(int)
        by_type = defaultdict(int)
        by_service = defaultdict(int)

        for alert in self.active_alerts.values():
            by_severity[alert.severity.value] += 1
            by_type[alert.alert_type.value] += 1
            by_service[alert.service_name] += 1

        return {
            "total_active_alerts": total_active,
            "by_severity": dict(by_severity),
            "by_type": dict(by_type),
            "by_service": dict(by_service),
            "total_rules": len(self.alert_rules),
            "enabled_rules": sum(
                1 for rule in self.alert_rules.values() if rule.enabled
            ),
            "notification_channels": len(self.notification_channels),
        }


# Global alert manager instance
alert_manager = MCPAlertManager()


def get_alert_manager() -> MCPAlertManager:
    """Get the global alert manager instance."""
    return alert_manager
