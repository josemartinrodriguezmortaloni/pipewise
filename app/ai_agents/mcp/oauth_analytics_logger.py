"""
OAuth Analytics Logger

This module handles logging of OAuth integration usage for analytics purposes.
It tracks usage patterns, success/failure rates, and performance metrics for
OAuth integrations across different services.

Key Features:
- Usage tracking for all OAuth operations
- Success/failure rate monitoring
- Performance metrics logging
- Structured logging for analytics
- Supabase integration for data storage
- Real-time analytics dashboard data

Following PRD: Task 3.0 - Integrar MCP con Sistema OAuth Existente
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum

from .error_handler import get_error_handler
from .oauth_integration import OAuthProvider

logger = logging.getLogger(__name__)


class OAuthEventType(Enum):
    """Types of OAuth events to track"""

    TOKEN_VALIDATION = "token_validation"
    TOKEN_REFRESH = "token_refresh"
    MCP_CREATION = "mcp_creation"
    SERVICE_ACCESS = "service_access"
    AUTHENTICATION_FAILURE = "authentication_failure"
    RATE_LIMIT_HIT = "rate_limit_hit"
    DEMO_MODE_FALLBACK = "demo_mode_fallback"


class OAuthEventStatus(Enum):
    """Status of OAuth events"""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL_SUCCESS = "partial_success"
    RETRY = "retry"


@dataclass
class OAuthAnalyticsEvent:
    """OAuth analytics event data structure"""

    event_id: str
    event_type: OAuthEventType
    status: OAuthEventStatus
    user_id: str
    service_name: str
    oauth_provider: Optional[OAuthProvider]
    timestamp: datetime
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "status": self.status.value,
            "user_id": self.user_id,
            "service_name": self.service_name,
            "oauth_provider": self.oauth_provider.value
            if self.oauth_provider
            else None,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "context": self.context or {},
            "metadata": self.metadata or {},
        }


class OAuthAnalyticsLogger:
    """
    Analytics logger for OAuth integrations.

    Tracks usage patterns, performance metrics, and errors for OAuth
    integrations to provide insights for optimization and troubleshooting.
    """

    def __init__(self):
        self.error_handler = get_error_handler()
        self._event_buffer = []  # Buffer events for batch processing
        self._buffer_size = 100  # Flush buffer when it reaches this size
        self._last_flush = datetime.now()
        self._flush_interval = timedelta(minutes=5)  # Flush every 5 minutes

    def log_oauth_event(
        self,
        event_type: OAuthEventType,
        status: OAuthEventStatus,
        user_id: str,
        service_name: str,
        oauth_provider: Optional[OAuthProvider] = None,
        duration_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log an OAuth analytics event.

        Args:
            event_type: Type of OAuth event
            status: Status of the event
            user_id: User identifier
            service_name: Name of the service
            oauth_provider: OAuth provider (optional)
            duration_ms: Duration in milliseconds (optional)
            error_message: Error message if failed (optional)
            context: Additional context data (optional)
            metadata: Additional metadata (optional)
        """
        try:
            import uuid

            # Create analytics event
            event = OAuthAnalyticsEvent(
                event_id=str(uuid.uuid4()),
                event_type=event_type,
                status=status,
                user_id=user_id,
                service_name=service_name,
                oauth_provider=oauth_provider,
                timestamp=datetime.now(),
                duration_ms=duration_ms,
                error_message=error_message,
                context=context,
                metadata=metadata,
            )

            # Add to buffer
            self._event_buffer.append(event)

            # Log to standard logger for immediate visibility
            self._log_to_standard_logger(event)

            # Check if we need to flush
            self._check_and_flush_buffer()

        except Exception as e:
            logger.error(f"❌ Error logging OAuth analytics event: {e}")

    def _log_to_standard_logger(self, event: OAuthAnalyticsEvent) -> None:
        """Log event to standard logger for immediate visibility"""
        status_icon = {
            OAuthEventStatus.SUCCESS: "✅",
            OAuthEventStatus.FAILURE: "❌",
            OAuthEventStatus.PARTIAL_SUCCESS: "⚠️",
            OAuthEventStatus.RETRY: "🔄",
        }.get(event.status, "ℹ️")

        log_message = (
            f"{status_icon} OAuth Analytics | "
            f"{event.event_type.value.upper()} | "
            f"User: {event.user_id} | "
            f"Service: {event.service_name} | "
            f"Provider: {event.oauth_provider.value if event.oauth_provider else 'Unknown'}"
        )

        if event.duration_ms:
            log_message += f" | Duration: {event.duration_ms}ms"

        if event.error_message:
            log_message += f" | Error: {event.error_message}"

        if event.status == OAuthEventStatus.SUCCESS:
            logger.info(log_message)
        elif event.status == OAuthEventStatus.FAILURE:
            logger.error(log_message)
        else:
            logger.warning(log_message)

    def _check_and_flush_buffer(self) -> None:
        """Check if buffer needs to be flushed and flush if necessary"""
        should_flush = (
            len(self._event_buffer) >= self._buffer_size
            or datetime.now() - self._last_flush >= self._flush_interval
        )

        if should_flush:
            self._flush_buffer()

    def _flush_buffer(self) -> None:
        """Flush event buffer to storage"""
        if not self._event_buffer:
            return

        try:
            # Store events in Supabase
            self._store_events_in_supabase(self._event_buffer)

            # Clear buffer
            events_count = len(self._event_buffer)
            self._event_buffer.clear()
            self._last_flush = datetime.now()

            logger.info(f"📊 Flushed {events_count} OAuth analytics events to storage")

        except Exception as e:
            logger.error(f"❌ Error flushing OAuth analytics buffer: {e}")

    def _store_events_in_supabase(self, events: List[OAuthAnalyticsEvent]) -> None:
        """Store events in Supabase analytics table"""
        try:
            from app.supabase.supabase_client import get_supabase_client

            supabase = get_supabase_client()

            # Convert events to dictionaries for storage
            event_data = [event.to_dict() for event in events]

            # Insert into oauth_analytics table
            supabase.table("oauth_analytics").insert(event_data).execute()

            logger.debug(f"📊 Stored {len(events)} OAuth analytics events in Supabase")

        except Exception as e:
            logger.error(f"❌ Error storing OAuth analytics events in Supabase: {e}")
            # Continue without failing - analytics should not break main functionality

    def log_token_validation(
        self,
        user_id: str,
        service_name: str,
        oauth_provider: Optional[OAuthProvider],
        success: bool,
        duration_ms: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Log token validation event"""
        self.log_oauth_event(
            event_type=OAuthEventType.TOKEN_VALIDATION,
            status=OAuthEventStatus.SUCCESS if success else OAuthEventStatus.FAILURE,
            user_id=user_id,
            service_name=service_name,
            oauth_provider=oauth_provider,
            duration_ms=duration_ms,
            error_message=error_message,
        )

    def log_token_refresh(
        self,
        user_id: str,
        service_name: str,
        oauth_provider: Optional[OAuthProvider],
        success: bool,
        duration_ms: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Log token refresh event"""
        self.log_oauth_event(
            event_type=OAuthEventType.TOKEN_REFRESH,
            status=OAuthEventStatus.SUCCESS if success else OAuthEventStatus.FAILURE,
            user_id=user_id,
            service_name=service_name,
            oauth_provider=oauth_provider,
            duration_ms=duration_ms,
            error_message=error_message,
        )

    def log_mcp_creation(
        self,
        user_id: str,
        service_name: str,
        oauth_provider: Optional[OAuthProvider],
        success: bool,
        duration_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log MCP creation event"""
        self.log_oauth_event(
            event_type=OAuthEventType.MCP_CREATION,
            status=OAuthEventStatus.SUCCESS if success else OAuthEventStatus.FAILURE,
            user_id=user_id,
            service_name=service_name,
            oauth_provider=oauth_provider,
            duration_ms=duration_ms,
            error_message=error_message,
            context=context,
        )

    def log_service_access(
        self,
        user_id: str,
        service_name: str,
        oauth_provider: Optional[OAuthProvider],
        success: bool,
        duration_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log service access event"""
        self.log_oauth_event(
            event_type=OAuthEventType.SERVICE_ACCESS,
            status=OAuthEventStatus.SUCCESS if success else OAuthEventStatus.FAILURE,
            user_id=user_id,
            service_name=service_name,
            oauth_provider=oauth_provider,
            duration_ms=duration_ms,
            error_message=error_message,
            context=context,
        )

    def log_authentication_failure(
        self,
        user_id: str,
        service_name: str,
        oauth_provider: Optional[OAuthProvider],
        error_message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log authentication failure event"""
        self.log_oauth_event(
            event_type=OAuthEventType.AUTHENTICATION_FAILURE,
            status=OAuthEventStatus.FAILURE,
            user_id=user_id,
            service_name=service_name,
            oauth_provider=oauth_provider,
            error_message=error_message,
            context=context,
        )

    def log_rate_limit_hit(
        self,
        user_id: str,
        service_name: str,
        oauth_provider: Optional[OAuthProvider],
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log rate limit hit event"""
        self.log_oauth_event(
            event_type=OAuthEventType.RATE_LIMIT_HIT,
            status=OAuthEventStatus.FAILURE,
            user_id=user_id,
            service_name=service_name,
            oauth_provider=oauth_provider,
            error_message="Rate limit exceeded",
            context=context,
        )

    def log_demo_mode_fallback(
        self,
        user_id: str,
        service_name: str,
        reason: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log demo mode fallback event"""
        self.log_oauth_event(
            event_type=OAuthEventType.DEMO_MODE_FALLBACK,
            status=OAuthEventStatus.PARTIAL_SUCCESS,
            user_id=user_id,
            service_name=service_name,
            oauth_provider=None,
            error_message=reason,
            context=context,
        )

    def force_flush(self) -> None:
        """Force flush of event buffer"""
        self._flush_buffer()

    def get_analytics_summary(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """
        Get analytics summary for a user.

        Args:
            user_id: User identifier
            days: Number of days to look back

        Returns:
            Dictionary with analytics summary
        """
        try:
            from app.supabase.supabase_client import get_supabase_client

            supabase = get_supabase_client()

            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # Query analytics data
            response = (
                supabase.table("oauth_analytics")
                .select("*")
                .eq("user_id", user_id)
                .gte("timestamp", start_date.isoformat())
                .lte("timestamp", end_date.isoformat())
                .execute()
            )

            if not response.data:
                return {
                    "total_events": 0,
                    "success_rate": 0.0,
                    "services_used": [],
                    "event_types": {},
                    "providers": {},
                    "daily_usage": {},
                }

            events = response.data

            # Calculate metrics
            total_events = len(events)
            success_events = len([e for e in events if e["status"] == "success"])
            success_rate = (
                (success_events / total_events) * 100 if total_events > 0 else 0
            )

            # Services used
            services_used = list(set(e["service_name"] for e in events))

            # Event types breakdown
            event_types = {}
            for event in events:
                event_type = event["event_type"]
                event_types[event_type] = event_types.get(event_type, 0) + 1

            # OAuth providers breakdown
            providers = {}
            for event in events:
                provider = event["oauth_provider"]
                if provider:
                    providers[provider] = providers.get(provider, 0) + 1

            # Daily usage
            daily_usage = {}
            for event in events:
                event_date = (
                    datetime.fromisoformat(event["timestamp"]).date().isoformat()
                )
                daily_usage[event_date] = daily_usage.get(event_date, 0) + 1

            return {
                "total_events": total_events,
                "success_rate": round(success_rate, 2),
                "services_used": services_used,
                "event_types": event_types,
                "providers": providers,
                "daily_usage": daily_usage,
            }

        except Exception as e:
            logger.error(f"❌ Error getting analytics summary: {e}")
            return {
                "total_events": 0,
                "success_rate": 0.0,
                "services_used": [],
                "event_types": {},
                "providers": {},
                "daily_usage": {},
                "error": str(e),
            }

    def get_system_analytics(self, days: int = 7) -> Dict[str, Any]:
        """
        Get system-wide analytics summary.

        Args:
            days: Number of days to look back

        Returns:
            Dictionary with system analytics
        """
        try:
            from app.supabase.supabase_client import get_supabase_client

            supabase = get_supabase_client()

            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # Query analytics data
            response = (
                supabase.table("oauth_analytics")
                .select("*")
                .gte("timestamp", start_date.isoformat())
                .lte("timestamp", end_date.isoformat())
                .execute()
            )

            if not response.data:
                return {
                    "total_events": 0,
                    "unique_users": 0,
                    "success_rate": 0.0,
                    "top_services": [],
                    "top_providers": [],
                    "error_rate_by_service": {},
                }

            events = response.data

            # Calculate metrics
            total_events = len(events)
            unique_users = len(set(e["user_id"] for e in events))
            success_events = len([e for e in events if e["status"] == "success"])
            success_rate = (
                (success_events / total_events) * 100 if total_events > 0 else 0
            )

            # Top services
            service_counts = {}
            for event in events:
                service = event["service_name"]
                service_counts[service] = service_counts.get(service, 0) + 1

            top_services = sorted(
                service_counts.items(), key=lambda x: x[1], reverse=True
            )[:5]

            # Top providers
            provider_counts = {}
            for event in events:
                provider = event["oauth_provider"]
                if provider:
                    provider_counts[provider] = provider_counts.get(provider, 0) + 1

            top_providers = sorted(
                provider_counts.items(), key=lambda x: x[1], reverse=True
            )[:5]

            # Error rate by service
            error_rate_by_service = {}
            for service in service_counts:
                service_events = [e for e in events if e["service_name"] == service]
                service_failures = [
                    e for e in service_events if e["status"] == "failure"
                ]
                error_rate = (len(service_failures) / len(service_events)) * 100
                error_rate_by_service[service] = round(error_rate, 2)

            return {
                "total_events": total_events,
                "unique_users": unique_users,
                "success_rate": round(success_rate, 2),
                "top_services": top_services,
                "top_providers": top_providers,
                "error_rate_by_service": error_rate_by_service,
            }

        except Exception as e:
            logger.error(f"❌ Error getting system analytics: {e}")
            return {
                "total_events": 0,
                "unique_users": 0,
                "success_rate": 0.0,
                "top_services": [],
                "top_providers": [],
                "error_rate_by_service": {},
                "error": str(e),
            }


# Global analytics logger instance
_oauth_analytics_logger = OAuthAnalyticsLogger()


def get_oauth_analytics_logger() -> OAuthAnalyticsLogger:
    """
    Get the global OAuth analytics logger instance.

    Returns:
        OAuthAnalyticsLogger instance
    """
    return _oauth_analytics_logger


def log_oauth_event(
    event_type: OAuthEventType,
    status: OAuthEventStatus,
    user_id: str,
    service_name: str,
    oauth_provider: Optional[OAuthProvider] = None,
    duration_ms: Optional[int] = None,
    error_message: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Convenience function to log OAuth analytics event.

    Args:
        event_type: Type of OAuth event
        status: Status of the event
        user_id: User identifier
        service_name: Name of the service
        oauth_provider: OAuth provider (optional)
        duration_ms: Duration in milliseconds (optional)
        error_message: Error message if failed (optional)
        context: Additional context data (optional)
    """
    logger_instance = get_oauth_analytics_logger()
    logger_instance.log_oauth_event(
        event_type=event_type,
        status=status,
        user_id=user_id,
        service_name=service_name,
        oauth_provider=oauth_provider,
        duration_ms=duration_ms,
        error_message=error_message,
        context=context,
    )
