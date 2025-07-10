"""
Meeting Scheduler Agent MCP Configurations

This module provides MCP configurations specifically for the Meeting Scheduler Agent.
The Meeting Scheduler Agent handles:
- Calendly MCP for scheduling links and automated booking
- Google Calendar MCP for calendar management and availability

Key Features:
- Automated meeting scheduling via Calendly
- Calendar availability checking
- Meeting link generation
- Google Calendar integration
- Event creation and management
- Reminder and notification systems
- Integration with OAuth system

Following PRD: Task 4.0 - Implementar MCPs Específicos por Agente
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum

from .oauth_integration import (
    OAuthTokens,
    MCPCredentials,
    OAuthProvider,
    get_mcp_credentials_for_service,
)
from .oauth_analytics_logger import (
    get_oauth_analytics_logger,
    OAuthEventType,
    OAuthEventStatus,
)
from .error_handler import (
    MCPConnectionError,
    MCPConfigurationError,
    MCPAuthenticationError,
    get_error_handler,
)
from .retry_handler import retry_mcp_operation

logger = logging.getLogger(__name__)


class SchedulerMCPType(Enum):
    """Types of MCPs used by Meeting Scheduler Agent"""

    CALENDLY = "calendly"
    GOOGLE_CALENDAR = "google_calendar"


class MeetingType(Enum):
    """Types of meetings supported by Calendly MCP"""

    DISCOVERY_CALL = "discovery_call"
    DEMO = "demo"
    CONSULTATION = "consultation"
    FOLLOW_UP = "follow_up"
    ONBOARDING = "onboarding"


class CalendarAction(Enum):
    """Types of calendar actions supported by Google Calendar MCP"""

    CREATE_EVENT = "create_event"
    UPDATE_EVENT = "update_event"
    DELETE_EVENT = "delete_event"
    GET_AVAILABILITY = "get_availability"
    LIST_EVENTS = "list_events"
    SEND_REMINDER = "send_reminder"


class MeetingSchedulerAgentMCPManager:
    """
    MCP Manager for Meeting Scheduler Agent.

    Manages Calendly and Google Calendar MCP configurations and operations
    specifically for the Meeting Scheduler Agent's scheduling workflows.
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.error_handler = get_error_handler()
        self.analytics_logger = get_oauth_analytics_logger()
        self._mcp_cache = {}

    @retry_mcp_operation(
        max_attempts=3, service_name="scheduler_calendly", log_attempts=True
    )
    async def configure_calendly_mcp(self) -> Dict[str, Any]:
        """
        Configure Calendly MCP for scheduling links and automated booking.

        Returns:
            Calendly MCP configuration with tools and credentials

        Raises:
            MCPConfigurationError: If configuration fails
            MCPAuthenticationError: If OAuth authentication fails
        """
        try:
            # Get OAuth tokens for Calendly
            calendly_tokens = await self._get_oauth_tokens("calendly")

            if not calendly_tokens:
                logger.warning(
                    f"⚠️ No Calendly OAuth tokens for user {self.user_id}, using demo mode"
                )
                return self._get_demo_calendly_config()

            # Get MCP credentials
            mcp_credentials = get_mcp_credentials_for_service(
                calendly_tokens, "calendly", self.user_id
            )

            # Configure Calendly MCP with specific tools
            calendly_config = {
                "service_name": "calendly",
                "service_type": "scheduling",
                "credentials": mcp_credentials.to_dict(),
                "tools": [
                    {
                        "name": "create_meeting_link",
                        "description": "Create personalized meeting links for leads",
                        "parameters": {
                            "event_type": {
                                "type": "string",
                                "enum": [
                                    "discovery_call",
                                    "demo",
                                    "consultation",
                                    "follow_up",
                                ],
                            },
                            "duration": {
                                "type": "integer",
                                "minimum": 15,
                                "maximum": 120,
                            },
                            "title": {"type": "string"},
                            "description": {"type": "string", "required": False},
                            "location": {"type": "string", "required": False},
                            "lead_email": {"type": "string", "required": False},
                            "custom_questions": {
                                "type": "array",
                                "items": {"type": "object"},
                                "required": False,
                            },
                        },
                        "pipedream_action": "calendly_create_meeting_link",
                    },
                    {
                        "name": "get_scheduled_events",
                        "description": "Get list of scheduled events for a date range",
                        "parameters": {
                            "start_date": {"type": "string", "format": "date"},
                            "end_date": {"type": "string", "format": "date"},
                            "status": {
                                "type": "string",
                                "enum": ["scheduled", "cancelled"],
                                "required": False,
                            },
                            "event_type": {"type": "string", "required": False},
                        },
                        "pipedream_action": "calendly_get_scheduled_events",
                    },
                    {
                        "name": "cancel_meeting",
                        "description": "Cancel a scheduled meeting",
                        "parameters": {
                            "event_uuid": {"type": "string"},
                            "reason": {"type": "string", "required": False},
                            "send_notification": {"type": "boolean", "default": True},
                        },
                        "pipedream_action": "calendly_cancel_meeting",
                    },
                    {
                        "name": "reschedule_meeting",
                        "description": "Reschedule an existing meeting",
                        "parameters": {
                            "event_uuid": {"type": "string"},
                            "new_start_time": {"type": "string", "format": "date-time"},
                            "send_notification": {"type": "boolean", "default": True},
                        },
                        "pipedream_action": "calendly_reschedule_meeting",
                    },
                    {
                        "name": "get_availability",
                        "description": "Check availability for scheduling meetings",
                        "parameters": {
                            "start_date": {"type": "string", "format": "date"},
                            "end_date": {"type": "string", "format": "date"},
                            "timezone": {"type": "string", "default": "UTC"},
                        },
                        "pipedream_action": "calendly_get_availability",
                    },
                    {
                        "name": "create_event_type",
                        "description": "Create new event type for different meeting purposes",
                        "parameters": {
                            "name": {"type": "string"},
                            "duration": {"type": "integer"},
                            "description": {"type": "string", "required": False},
                            "location": {"type": "string", "required": False},
                            "color": {"type": "string", "required": False},
                            "custom_questions": {
                                "type": "array",
                                "items": {"type": "object"},
                                "required": False,
                            },
                        },
                        "pipedream_action": "calendly_create_event_type",
                    },
                    {
                        "name": "get_meeting_analytics",
                        "description": "Get analytics for scheduled meetings",
                        "parameters": {
                            "start_date": {"type": "string", "format": "date"},
                            "end_date": {"type": "string", "format": "date"},
                            "metrics": {
                                "type": "array",
                                "items": {"type": "string"},
                                "required": False,
                            },
                        },
                        "pipedream_action": "calendly_get_analytics",
                    },
                    {
                        "name": "send_meeting_reminder",
                        "description": "Send reminder for upcoming meetings",
                        "parameters": {
                            "event_uuid": {"type": "string"},
                            "reminder_time": {
                                "type": "integer",
                                "description": "Minutes before meeting",
                            },
                            "custom_message": {"type": "string", "required": False},
                        },
                        "pipedream_action": "calendly_send_reminder",
                    },
                ],
                "configuration": {
                    "webhook_enabled": True,
                    "auto_confirmations": True,
                    "reminder_enabled": True,
                    "default_timezone": "UTC",
                    "booking_window": 30,  # days
                    "buffer_time": 15,  # minutes
                    "max_events_per_day": 10,
                    "api_version": "2022-08-01",
                },
                "rate_limits": {
                    "api_calls_per_minute": 100,
                    "meetings_per_hour": 50,
                    "events_per_day": 100,
                },
                "meeting_types": {
                    "discovery_call": {
                        "duration": 30,
                        "description": "Initial discovery call with potential leads",
                        "color": "#007bff",
                    },
                    "demo": {
                        "duration": 45,
                        "description": "Product demonstration session",
                        "color": "#28a745",
                    },
                    "consultation": {
                        "duration": 60,
                        "description": "Detailed consultation session",
                        "color": "#ffc107",
                    },
                    "follow_up": {
                        "duration": 15,
                        "description": "Follow-up meeting",
                        "color": "#6c757d",
                    },
                },
            }

            # Cache configuration
            self._mcp_cache["calendly"] = calendly_config

            # Log successful configuration
            self.analytics_logger.log_mcp_creation(
                user_id=self.user_id,
                service_name="calendly",
                oauth_provider=OAuthProvider.CALENDLY,
                success=True,
                context={
                    "agent_type": "meeting_scheduler",
                    "tools_count": len(calendly_config["tools"]),
                },
            )

            logger.info(
                f"✅ Calendly MCP configured for Meeting Scheduler Agent (user: {self.user_id})"
            )

            return calendly_config

        except Exception as e:
            mcp_error = self.error_handler.handle_error(
                e,
                service_name="calendly",
                operation="configure_calendly_mcp",
                context={"user_id": self.user_id, "agent_type": "meeting_scheduler"},
            )

            # Log failed configuration
            self.analytics_logger.log_mcp_creation(
                user_id=self.user_id,
                service_name="calendly",
                oauth_provider=OAuthProvider.CALENDLY,
                success=False,
                error_message=mcp_error.get_user_friendly_message(),
                context={"agent_type": "meeting_scheduler"},
            )

            logger.error(
                f"❌ Failed to configure Calendly MCP: {mcp_error.get_user_friendly_message()}"
            )
            raise mcp_error

    @retry_mcp_operation(
        max_attempts=3, service_name="scheduler_google_calendar", log_attempts=True
    )
    async def configure_google_calendar_mcp(self) -> Dict[str, Any]:
        """
        Configure Google Calendar MCP for calendar management and availability.

        Returns:
            Google Calendar MCP configuration with tools and credentials

        Raises:
            MCPConfigurationError: If configuration fails
            MCPAuthenticationError: If OAuth authentication fails
        """
        try:
            # Get OAuth tokens for Google Calendar
            google_tokens = await self._get_oauth_tokens("google_calendar")

            if not google_tokens:
                logger.warning(
                    f"⚠️ No Google Calendar OAuth tokens for user {self.user_id}, using demo mode"
                )
                return self._get_demo_google_calendar_config()

            # Get MCP credentials
            mcp_credentials = get_mcp_credentials_for_service(
                google_tokens, "google_calendar", self.user_id
            )

            # Configure Google Calendar MCP with specific tools
            google_calendar_config = {
                "service_name": "google_calendar",
                "service_type": "calendar",
                "credentials": mcp_credentials.to_dict(),
                "tools": [
                    {
                        "name": "create_calendar_event",
                        "description": "Create calendar events for scheduled meetings",
                        "parameters": {
                            "title": {"type": "string"},
                            "description": {"type": "string", "required": False},
                            "start_time": {"type": "string", "format": "date-time"},
                            "end_time": {"type": "string", "format": "date-time"},
                            "timezone": {"type": "string", "default": "UTC"},
                            "attendees": {
                                "type": "array",
                                "items": {"type": "string"},
                                "required": False,
                            },
                            "location": {"type": "string", "required": False},
                            "meeting_link": {"type": "string", "required": False},
                            "reminder_minutes": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "required": False,
                            },
                        },
                        "pipedream_action": "google_calendar_create_event",
                    },
                    {
                        "name": "get_calendar_events",
                        "description": "Get calendar events for a specific date range",
                        "parameters": {
                            "start_date": {"type": "string", "format": "date"},
                            "end_date": {"type": "string", "format": "date"},
                            "calendar_id": {"type": "string", "default": "primary"},
                            "timezone": {"type": "string", "default": "UTC"},
                        },
                        "pipedream_action": "google_calendar_get_events",
                    },
                    {
                        "name": "update_calendar_event",
                        "description": "Update existing calendar event",
                        "parameters": {
                            "event_id": {"type": "string"},
                            "title": {"type": "string", "required": False},
                            "description": {"type": "string", "required": False},
                            "start_time": {
                                "type": "string",
                                "format": "date-time",
                                "required": False,
                            },
                            "end_time": {
                                "type": "string",
                                "format": "date-time",
                                "required": False,
                            },
                            "attendees": {
                                "type": "array",
                                "items": {"type": "string"},
                                "required": False,
                            },
                            "location": {"type": "string", "required": False},
                        },
                        "pipedream_action": "google_calendar_update_event",
                    },
                    {
                        "name": "delete_calendar_event",
                        "description": "Delete calendar event",
                        "parameters": {
                            "event_id": {"type": "string"},
                            "calendar_id": {"type": "string", "default": "primary"},
                            "send_updates": {
                                "type": "string",
                                "enum": ["all", "externalOnly", "none"],
                                "default": "all",
                            },
                        },
                        "pipedream_action": "google_calendar_delete_event",
                    },
                    {
                        "name": "check_availability",
                        "description": "Check calendar availability for scheduling",
                        "parameters": {
                            "start_time": {"type": "string", "format": "date-time"},
                            "end_time": {"type": "string", "format": "date-time"},
                            "calendar_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "default": ["primary"],
                            },
                            "timezone": {"type": "string", "default": "UTC"},
                        },
                        "pipedream_action": "google_calendar_check_availability",
                    },
                    {
                        "name": "find_meeting_time",
                        "description": "Find available meeting time for attendees",
                        "parameters": {
                            "duration_minutes": {"type": "integer"},
                            "attendee_emails": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "preferred_times": {
                                "type": "array",
                                "items": {"type": "object"},
                                "required": False,
                            },
                            "start_date": {"type": "string", "format": "date"},
                            "end_date": {"type": "string", "format": "date"},
                            "timezone": {"type": "string", "default": "UTC"},
                        },
                        "pipedream_action": "google_calendar_find_meeting_time",
                    },
                    {
                        "name": "create_meeting_room",
                        "description": "Create or book meeting room resource",
                        "parameters": {
                            "room_email": {"type": "string"},
                            "event_id": {"type": "string"},
                            "start_time": {"type": "string", "format": "date-time"},
                            "end_time": {"type": "string", "format": "date-time"},
                        },
                        "pipedream_action": "google_calendar_book_room",
                    },
                    {
                        "name": "send_calendar_invite",
                        "description": "Send calendar invitation to attendees",
                        "parameters": {
                            "event_id": {"type": "string"},
                            "attendee_emails": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "custom_message": {"type": "string", "required": False},
                        },
                        "pipedream_action": "google_calendar_send_invite",
                    },
                ],
                "configuration": {
                    "api_version": "v3",
                    "default_calendar": "primary",
                    "default_timezone": "UTC",
                    "send_notifications": True,
                    "use_default_reminders": True,
                    "guest_can_modify": False,
                    "guest_can_invite_others": False,
                    "guest_can_see_other_guests": True,
                },
                "rate_limits": {
                    "api_calls_per_minute": 1000,
                    "events_per_hour": 300,
                    "batch_requests_per_minute": 100,
                },
                "scopes": [
                    "https://www.googleapis.com/auth/calendar",
                    "https://www.googleapis.com/auth/calendar.events",
                    "https://www.googleapis.com/auth/calendar.readonly",
                ],
            }

            # Cache configuration
            self._mcp_cache["google_calendar"] = google_calendar_config

            # Log successful configuration
            self.analytics_logger.log_mcp_creation(
                user_id=self.user_id,
                service_name="google_calendar",
                oauth_provider=OAuthProvider.GOOGLE,
                success=True,
                context={
                    "agent_type": "meeting_scheduler",
                    "tools_count": len(google_calendar_config["tools"]),
                },
            )

            logger.info(
                f"✅ Google Calendar MCP configured for Meeting Scheduler Agent (user: {self.user_id})"
            )

            return google_calendar_config

        except Exception as e:
            mcp_error = self.error_handler.handle_error(
                e,
                service_name="google_calendar",
                operation="configure_google_calendar_mcp",
                context={"user_id": self.user_id, "agent_type": "meeting_scheduler"},
            )

            # Log failed configuration
            self.analytics_logger.log_mcp_creation(
                user_id=self.user_id,
                service_name="google_calendar",
                oauth_provider=OAuthProvider.GOOGLE,
                success=False,
                error_message=mcp_error.get_user_friendly_message(),
                context={"agent_type": "meeting_scheduler"},
            )

            logger.error(
                f"❌ Failed to configure Google Calendar MCP: {mcp_error.get_user_friendly_message()}"
            )
            raise mcp_error

    async def get_meeting_scheduler_mcp_configuration(self) -> Dict[str, Any]:
        """
        Get complete MCP configuration for Meeting Scheduler Agent.

        Returns:
            Dictionary with Calendly and Google Calendar MCP configurations
        """
        try:
            # Configure both MCPs
            calendly_config = await self.configure_calendly_mcp()
            google_calendar_config = await self.configure_google_calendar_mcp()

            scheduler_config = {
                "agent_type": "meeting_scheduler",
                "agent_name": "PipeWise Meeting Scheduler",
                "description": "Handles meeting scheduling and calendar management",
                "user_id": self.user_id,
                "mcps": {
                    "calendly": calendly_config,
                    "google_calendar": google_calendar_config,
                },
                "capabilities": [
                    "meeting_scheduling",
                    "calendar_management",
                    "availability_checking",
                    "event_creation",
                    "reminder_management",
                    "meeting_analytics",
                    "room_booking",
                    "invite_management",
                ],
                "workflows": {
                    "schedule_discovery_call": {
                        "steps": [
                            {"tool": "get_availability", "service": "calendly"},
                            {
                                "tool": "create_meeting_link",
                                "service": "calendly",
                                "type": "discovery_call",
                            },
                            {
                                "tool": "create_calendar_event",
                                "service": "google_calendar",
                            },
                            {"tool": "send_meeting_reminder", "service": "calendly"},
                        ],
                    },
                    "schedule_demo": {
                        "steps": [
                            {"tool": "find_meeting_time", "service": "google_calendar"},
                            {
                                "tool": "create_meeting_link",
                                "service": "calendly",
                                "type": "demo",
                            },
                            {
                                "tool": "create_calendar_event",
                                "service": "google_calendar",
                            },
                            {
                                "tool": "send_calendar_invite",
                                "service": "google_calendar",
                            },
                        ],
                    },
                    "reschedule_meeting": {
                        "steps": [
                            {
                                "tool": "check_availability",
                                "service": "google_calendar",
                            },
                            {"tool": "reschedule_meeting", "service": "calendly"},
                            {
                                "tool": "update_calendar_event",
                                "service": "google_calendar",
                            },
                            {
                                "tool": "send_calendar_invite",
                                "service": "google_calendar",
                            },
                        ],
                    },
                    "cancel_meeting": {
                        "steps": [
                            {"tool": "cancel_meeting", "service": "calendly"},
                            {
                                "tool": "delete_calendar_event",
                                "service": "google_calendar",
                            },
                        ],
                    },
                },
                "configuration": {
                    "scheduling_channels": ["calendly", "google_calendar"],
                    "automation_enabled": True,
                    "sync_enabled": True,
                    "reminder_enabled": True,
                    "analytics_tracking": True,
                },
                "created_at": datetime.now().isoformat(),
            }

            logger.info(
                f"✅ Complete Meeting Scheduler MCP configuration ready for user {self.user_id}"
            )

            return scheduler_config

        except Exception as e:
            logger.error(
                f"❌ Failed to get complete Meeting Scheduler MCP configuration: {e}"
            )
            raise

    async def _get_oauth_tokens(self, service_name: str) -> Optional[OAuthTokens]:
        """Get OAuth tokens for a service"""
        try:
            from .mcp_server_manager import get_mcp_credentials_for_user

            mcp_credentials = await get_mcp_credentials_for_user(
                self.user_id, service_name
            )

            if not mcp_credentials:
                return None

            # Extract tokens from credentials (simplified)
            provider_map = {
                "calendly": OAuthProvider.CALENDLY,
                "google_calendar": OAuthProvider.GOOGLE,
            }

            return OAuthTokens(
                access_token=f"scheduler_demo_token_{service_name}",
                provider=provider_map.get(service_name, OAuthProvider.GOOGLE),
                user_id=self.user_id,
            )

        except Exception as e:
            logger.debug(f"⚪ Could not get OAuth tokens for {service_name}: {e}")
            return None

    def _get_demo_calendly_config(self) -> Dict[str, Any]:
        """Get demo Calendly configuration for development"""
        return {
            "service_name": "calendly",
            "service_type": "scheduling",
            "demo_mode": True,
            "credentials": {
                "service_name": "calendly",
                "headers": {
                    "Authorization": f"Bearer demo_calendly_token_{self.user_id}",
                    "Content-Type": "application/json",
                },
                "auth_type": "demo",
            },
            "tools": [
                {
                    "name": "create_meeting_link",
                    "description": "Create personalized meeting links for leads (DEMO MODE)",
                    "demo_response": {
                        "meeting_link": f"https://calendly.com/demo-user-{self.user_id}/discovery-call",
                        "event_type": "discovery_call",
                        "duration": 30,
                    },
                },
                {
                    "name": "get_scheduled_events",
                    "description": "Get scheduled events (DEMO MODE)",
                    "demo_response": {
                        "events": [
                            {
                                "uuid": "demo_event_123",
                                "title": "Discovery Call",
                                "start_time": "2025-01-08T10:00:00Z",
                                "status": "scheduled",
                            }
                        ],
                    },
                },
            ],
            "configuration": {
                "demo_mode": True,
                "webhook_enabled": False,
                "auto_confirmations": False,
            },
        }

    def _get_demo_google_calendar_config(self) -> Dict[str, Any]:
        """Get demo Google Calendar configuration for development"""
        return {
            "service_name": "google_calendar",
            "service_type": "calendar",
            "demo_mode": True,
            "credentials": {
                "service_name": "google_calendar",
                "headers": {
                    "Authorization": f"Bearer demo_google_calendar_token_{self.user_id}",
                    "Content-Type": "application/json",
                },
                "auth_type": "demo",
            },
            "tools": [
                {
                    "name": "create_calendar_event",
                    "description": "Create calendar events (DEMO MODE)",
                    "demo_response": {
                        "event_id": "demo_event_456",
                        "title": "Demo Meeting",
                        "start_time": "2025-01-08T14:00:00Z",
                        "status": "confirmed",
                    },
                },
                {
                    "name": "check_availability",
                    "description": "Check calendar availability (DEMO MODE)",
                    "demo_response": {
                        "available": True,
                        "next_available_slot": "2025-01-08T15:00:00Z",
                    },
                },
            ],
            "configuration": {
                "demo_mode": True,
                "api_version": "v3",
                "default_calendar": "primary",
            },
        }

    def clear_cache(self) -> None:
        """Clear MCP configuration cache"""
        self._mcp_cache.clear()
        logger.info("🧹 Cleared Meeting Scheduler MCP cache")


# Helper functions
async def get_meeting_scheduler_mcp_configuration(user_id: str) -> Dict[str, Any]:
    """
    Get MCP configuration for Meeting Scheduler Agent.

    Args:
        user_id: User identifier

    Returns:
        Complete MCP configuration for Meeting Scheduler Agent
    """
    manager = MeetingSchedulerAgentMCPManager(user_id)
    return await manager.get_meeting_scheduler_mcp_configuration()


async def configure_scheduler_calendly(user_id: str) -> Dict[str, Any]:
    """
    Configure Calendly MCP for Meeting Scheduler Agent.

    Args:
        user_id: User identifier

    Returns:
        Calendly MCP configuration
    """
    manager = MeetingSchedulerAgentMCPManager(user_id)
    return await manager.configure_calendly_mcp()


async def configure_scheduler_google_calendar(user_id: str) -> Dict[str, Any]:
    """
    Configure Google Calendar MCP for Meeting Scheduler Agent.

    Args:
        user_id: User identifier

    Returns:
        Google Calendar MCP configuration
    """
    manager = MeetingSchedulerAgentMCPManager(user_id)
    return await manager.configure_google_calendar_mcp()


def get_scheduler_supported_tools() -> List[str]:
    """
    Get list of tools supported by Meeting Scheduler Agent MCPs.

    Returns:
        List of supported tool names
    """
    return [
        # Calendly tools
        "create_meeting_link",
        "get_scheduled_events",
        "cancel_meeting",
        "reschedule_meeting",
        "get_availability",
        "create_event_type",
        "get_meeting_analytics",
        "send_meeting_reminder",
        # Google Calendar tools
        "create_calendar_event",
        "get_calendar_events",
        "update_calendar_event",
        "delete_calendar_event",
        "check_availability",
        "find_meeting_time",
        "create_meeting_room",
        "send_calendar_invite",
    ]


def get_scheduler_workflow_templates() -> Dict[str, Dict[str, Any]]:
    """
    Get workflow templates for Meeting Scheduler Agent.

    Returns:
        Dictionary of workflow templates
    """
    return {
        "schedule_discovery_call": {
            "name": "Schedule Discovery Call",
            "description": "Complete workflow for scheduling discovery calls with leads",
            "steps": [
                {
                    "step": 1,
                    "tool": "get_availability",
                    "service": "calendly",
                    "description": "Check available time slots",
                },
                {
                    "step": 2,
                    "tool": "create_meeting_link",
                    "service": "calendly",
                    "description": "Create personalized meeting link",
                },
                {
                    "step": 3,
                    "tool": "create_calendar_event",
                    "service": "google_calendar",
                    "description": "Add event to calendar",
                },
                {
                    "step": 4,
                    "tool": "send_meeting_reminder",
                    "service": "calendly",
                    "description": "Send reminder to attendees",
                },
            ],
        },
        "schedule_demo": {
            "name": "Schedule Product Demo",
            "description": "Workflow for scheduling product demonstration sessions",
            "steps": [
                {
                    "step": 1,
                    "tool": "find_meeting_time",
                    "service": "google_calendar",
                    "description": "Find optimal meeting time",
                },
                {
                    "step": 2,
                    "tool": "create_meeting_link",
                    "service": "calendly",
                    "description": "Create demo meeting link",
                },
                {
                    "step": 3,
                    "tool": "create_calendar_event",
                    "service": "google_calendar",
                    "description": "Create calendar event",
                },
                {
                    "step": 4,
                    "tool": "send_calendar_invite",
                    "service": "google_calendar",
                    "description": "Send calendar invitation",
                },
            ],
        },
        "reschedule_meeting": {
            "name": "Reschedule Meeting",
            "description": "Workflow for rescheduling existing meetings",
            "steps": [
                {
                    "step": 1,
                    "tool": "check_availability",
                    "service": "google_calendar",
                    "description": "Check new time availability",
                },
                {
                    "step": 2,
                    "tool": "reschedule_meeting",
                    "service": "calendly",
                    "description": "Reschedule in Calendly",
                },
                {
                    "step": 3,
                    "tool": "update_calendar_event",
                    "service": "google_calendar",
                    "description": "Update calendar event",
                },
                {
                    "step": 4,
                    "tool": "send_calendar_invite",
                    "service": "google_calendar",
                    "description": "Send updated invitation",
                },
            ],
        },
    }
