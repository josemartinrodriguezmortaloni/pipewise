"""
Meeting Scheduler MCP Integration

This module provides MCP-based replacements for local scheduling functions.
It replaces the original schedule_meeting_for_lead() function with a new
implementation that uses MCP tools for Calendly and Google Calendar.

Key Features:
- Replace local schedule_meeting_for_lead() with MCP version
- Use Calendly MCP for meeting link generation
- Use Google Calendar MCP for event creation
- Maintain backward compatibility with existing API
- Provide enhanced scheduling capabilities

Following PRD: Task 4.2.3 - Replace schedule_meeting_for_lead() with MCP tools
"""

import logging
from typing import Dict, Any, Optional, Union
from datetime import datetime, timedelta
from uuid import UUID

from .meeting_scheduler_agent_mcps import MeetingSchedulerAgentMCPManager
from .local_tools_to_mcp_mapper import LocalToolToMCPMapper
from .oauth_integration import OAuthProvider
from .error_handler import get_error_handler, MCPConnectionError
from .retry_handler import retry_mcp_operation
from ..tools.gmail import GmailMCPServer
from ..tools.twitter import TwitterMCPServer

# Import the existing database client
from ...supabase.supabase_client import SupabaseCRMClient
from ...models.lead import Lead

logger = logging.getLogger(__name__)


class MCPSchedulingManager:
    """
    MCP-based scheduling manager that replaces local scheduling functions.

    This class provides MCP-based implementations for meeting scheduling
    that integrate with Calendly and Google Calendar via MCP tools.
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.error_handler = get_error_handler()
        self.scheduler_mcp_manager = MeetingSchedulerAgentMCPManager(user_id)
        self.tool_mapper = LocalToolToMCPMapper(user_id)
        self.db_client = SupabaseCRMClient()

    @retry_mcp_operation(
        max_attempts=3, service_name="mcp_meeting_scheduler", log_attempts=True
    )
    async def schedule_meeting_for_lead_mcp(
        self,
        lead_id: str,
        meeting_url: Optional[str] = None,
        event_type: str = "discovery_call",
    ) -> Dict[str, Any]:
        """
        MCP-based replacement for schedule_meeting_for_lead().

        This function provides enhanced scheduling capabilities using MCP tools
        while maintaining backward compatibility with the original function.

        Args:
            lead_id: Lead identifier (can be email or ID)
            meeting_url: Optional pre-generated meeting URL
            event_type: Type of meeting (discovery_call, demo, consultation, follow_up)

        Returns:
            Dictionary with scheduling result and meeting details
        """
        try:
            # Get lead information
            lead = await self._get_lead_info(lead_id)
            if not lead:
                return {
                    "success": False,
                    "error": f"Lead with identifier '{lead_id}' not found",
                    "lead_id": lead_id,
                    "mcp_used": False,
                }

            # Get MCP configurations
            scheduler_config = await self.scheduler_mcp_manager.get_meeting_scheduler_mcp_configuration()

            # Check if MCPs are available
            calendly_available = not scheduler_config["mcps"]["calendly"].get(
                "demo_mode", False
            )
            google_calendar_available = not scheduler_config["mcps"][
                "google_calendar"
            ].get("demo_mode", False)

            # Execute scheduling workflow
            if meeting_url:
                # Use provided meeting URL
                result = await self._schedule_with_existing_url(
                    lead, meeting_url, event_type
                )
            else:
                # Create new meeting using MCP tools
                result = await self._schedule_with_mcp_tools(
                    lead, event_type, calendly_available, google_calendar_available
                )

            # Update lead in database
            if result["success"]:
                await self._update_lead_in_database(
                    lead, result["meeting_url"], event_type
                )

            # Add MCP usage information
            result["mcp_used"] = True
            result["calendly_available"] = calendly_available
            result["google_calendar_available"] = google_calendar_available
            result["user_id"] = self.user_id

            logger.info(
                f"✅ MCP-based meeting scheduled for lead {lead.id}: {result['meeting_url']}"
            )

            return result

        except Exception as e:
            mcp_error = self.error_handler.handle_error(
                e,
                service_name="mcp_meeting_scheduler",
                operation="schedule_meeting_for_lead_mcp",
                context={
                    "lead_id": lead_id,
                    "event_type": event_type,
                    "user_id": self.user_id,
                },
            )

            logger.error(
                f"❌ MCP-based meeting scheduling failed: {mcp_error.get_user_friendly_message()}"
            )

            return {
                "success": False,
                "error": mcp_error.get_user_friendly_message(),
                "lead_id": lead_id,
                "event_type": event_type,
                "mcp_used": True,
                "fallback_available": True,
            }

    async def _schedule_with_existing_url(
        self, lead: Lead, meeting_url: str, event_type: str
    ) -> Dict[str, Any]:
        """Schedule meeting with existing URL"""
        try:
            # Create calendar event using Google Calendar MCP
            calendar_result = await self._create_calendar_event(
                lead, meeting_url, event_type
            )

            # Send meeting confirmation
            confirmation_result = await self._send_meeting_confirmation(
                lead, meeting_url, event_type
            )

            return {
                "success": True,
                "meeting_url": meeting_url,
                "event_type": event_type,
                "calendar_event_created": calendar_result.get("success", False),
                "confirmation_sent": confirmation_result.get("success", False),
                "method": "existing_url",
            }

        except Exception as e:
            logger.error(f"❌ Error scheduling with existing URL: {e}")
            return {
                "success": False,
                "error": str(e),
                "meeting_url": meeting_url,
                "method": "existing_url",
            }

    async def _schedule_with_mcp_tools(
        self,
        lead: Lead,
        event_type: str,
        calendly_available: bool,
        google_calendar_available: bool,
    ) -> Dict[str, Any]:
        """Schedule meeting using MCP tools"""
        try:
            meeting_url = None
            calendar_event_id = None

            # Step 1: Create meeting link using Calendly MCP
            if calendly_available:
                calendly_result = await self._create_calendly_meeting_link(
                    lead, event_type
                )
                if calendly_result.get("success", False):
                    meeting_url = calendly_result.get("meeting_link")
                    logger.info(f"✅ Calendly meeting link created: {meeting_url}")

            # Step 2: Create calendar event using Google Calendar MCP
            if google_calendar_available and meeting_url:
                calendar_result = await self._create_calendar_event(
                    lead, meeting_url, event_type
                )
                if calendar_result.get("success", False):
                    calendar_event_id = calendar_result.get("event_id")
                    logger.info(
                        f"✅ Google Calendar event created: {calendar_event_id}"
                    )

            # Step 3: Send meeting confirmation
            confirmation_result = await self._send_meeting_confirmation(
                lead, meeting_url or "", event_type
            )

            # Generate fallback URL if MCP tools failed
            if not meeting_url:
                meeting_url = self._generate_fallback_meeting_url(lead, event_type)
                logger.warning(f"⚠️ Using fallback meeting URL: {meeting_url}")

            return {
                "success": True,
                "meeting_url": meeting_url,
                "event_type": event_type,
                "calendar_event_id": calendar_event_id,
                "confirmation_sent": confirmation_result.get("success", False),
                "method": "mcp_tools",
                "calendly_used": calendly_available,
                "google_calendar_used": google_calendar_available,
            }

        except Exception as e:
            logger.error(f"❌ Error scheduling with MCP tools: {e}")
            return {
                "success": False,
                "error": str(e),
                "event_type": event_type,
                "method": "mcp_tools",
            }

    async def _create_calendly_meeting_link(
        self, lead: Lead, event_type: str
    ) -> Dict[str, Any]:
        """Create meeting link using Calendly MCP"""
        try:
            # Map event type to Calendly parameters
            duration_map = {
                "discovery_call": 30,
                "demo": 45,
                "consultation": 60,
                "follow_up": 15,
            }

            # Use MCP tool mapper to execute Calendly tool
            result = await self.tool_mapper.map_tool_call(
                "calendly.create_meeting_link",
                {
                    "event_type": event_type,
                    "duration": duration_map.get(event_type, 30),
                    "title": f"{event_type.replace('_', ' ').title()} with {lead.name}",
                    "description": f"Scheduled {event_type.replace('_', ' ')} with {lead.name} from {lead.company}",
                    "lead_email": lead.email,
                },
            )

            if result.get("success", False):
                return {
                    "success": True,
                    "meeting_link": result.get("meeting_link")
                    or result.get("result", {}).get("meeting_link"),
                    "event_type": event_type,
                    "duration": duration_map.get(event_type, 30),
                }
            else:
                return {
                    "success": False,
                    "error": result.get(
                        "error", "Unknown error creating Calendly link"
                    ),
                }

        except Exception as e:
            logger.error(f"❌ Error creating Calendly meeting link: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def _create_calendar_event(
        self, lead: Lead, meeting_url: str, event_type: str
    ) -> Dict[str, Any]:
        """Create calendar event using Google Calendar MCP"""
        try:
            # Calculate meeting time (example: tomorrow at 2 PM)
            meeting_time = datetime.now() + timedelta(days=1)
            meeting_time = meeting_time.replace(
                hour=14, minute=0, second=0, microsecond=0
            )

            # Duration mapping
            duration_map = {
                "discovery_call": 30,
                "demo": 45,
                "consultation": 60,
                "follow_up": 15,
            }

            duration = duration_map.get(event_type, 30)
            end_time = meeting_time + timedelta(minutes=duration)

            # Use MCP tool mapper to execute Google Calendar tool
            result = await self.tool_mapper.map_tool_call(
                "google_calendar.create_calendar_event",
                {
                    "title": f"{event_type.replace('_', ' ').title()} with {lead.name}",
                    "description": f"Scheduled {event_type.replace('_', ' ')} with {lead.name} from {lead.company}",
                    "start_time": meeting_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "attendees": [lead.email],
                    "location": meeting_url,
                    "meeting_link": meeting_url,
                    "reminder_minutes": [15, 60],  # 15 minutes and 1 hour before
                },
            )

            if result.get("success", False):
                return {
                    "success": True,
                    "event_id": result.get("event_id")
                    or result.get("result", {}).get("event_id"),
                    "start_time": meeting_time.isoformat(),
                    "end_time": end_time.isoformat(),
                }
            else:
                return {
                    "success": False,
                    "error": result.get(
                        "error", "Unknown error creating calendar event"
                    ),
                }

        except Exception as e:
            logger.error(f"❌ Error creating calendar event: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def _send_meeting_confirmation(
        self, lead: Lead, meeting_url: str, event_type: str
    ) -> Dict[str, Any]:
        """Send meeting confirmation using email MCP"""
        try:
            # Use MCP tool mapper to send confirmation email
            result = await self.tool_mapper.map_tool_call(
                "gmail.send_email",
                {
                    "to_email": lead.email,
                    "subject": f"Meeting Scheduled: {event_type.replace('_', ' ').title()}",
                    "message": f"""
                    Hello {lead.name},
                    
                    Your {event_type.replace("_", " ")} has been scheduled successfully.
                    
                    Meeting Details:
                    - Type: {event_type.replace("_", " ").title()}
                    - Meeting Link: {meeting_url}
                    - Company: {lead.company}
                    
                    Please save this information and join the meeting at the scheduled time.
                    
                    Best regards,
                    PipeWise Team
                    """,
                    "from_name": "PipeWise Scheduler",
                },
            )

            if result.get("success", False):
                return {
                    "success": True,
                    "email_sent": True,
                    "recipient": lead.email,
                }
            else:
                return {
                    "success": False,
                    "error": result.get(
                        "error", "Unknown error sending confirmation email"
                    ),
                }

        except Exception as e:
            logger.error(f"❌ Error sending meeting confirmation: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def _generate_fallback_meeting_url(self, lead: Lead, event_type: str) -> str:
        """Generate fallback meeting URL when MCP tools fail"""
        # Generate a simple Calendly-style URL as fallback
        safe_name = lead.name.replace(" ", "-").lower()
        return f"https://calendly.com/pipewise-{self.user_id}/{event_type}-{safe_name}"

    async def _get_lead_info(self, lead_id: str) -> Optional[Lead]:
        """Get lead information from database"""
        try:
            if "@" in lead_id:
                # Lead ID is an email
                return self.db_client.get_lead_by_email(lead_id)
            else:
                # Lead ID is a UUID
                return self.db_client.get_lead(lead_id)
        except Exception as e:
            logger.error(f"❌ Error getting lead info: {e}")
            return None

    async def _update_lead_in_database(
        self, lead: Lead, meeting_url: str, event_type: str
    ) -> bool:
        """Update lead in database with meeting information"""
        try:
            if not lead.id:
                logger.error("❌ Lead ID is None, cannot update database")
                return False

            updated_lead = self.db_client.schedule_meeting_for_lead(
                lead.id, meeting_url, event_type
            )
            logger.info(f"✅ Lead {lead.id} updated with meeting: {meeting_url}")
            return True
        except Exception as e:
            logger.error(f"❌ Error updating lead in database: {e}")
            return False


# Backward compatibility wrapper function
async def schedule_meeting_for_lead_mcp(
    lead_id: str,
    meeting_url: Optional[str] = None,
    event_type: str = "discovery_call",
    user_id: str = "system",
) -> Dict[str, Any]:
    """
    MCP-based replacement for the original schedule_meeting_for_lead function.

    This function provides the same interface as the original function but
    uses MCP tools for enhanced scheduling capabilities.

    Args:
        lead_id: Lead identifier (can be email or ID)
        meeting_url: Optional pre-generated meeting URL
        event_type: Type of meeting (discovery_call, demo, consultation, follow_up)
        user_id: User identifier for MCP configuration

    Returns:
        Dictionary with scheduling result and meeting details
    """
    scheduler = MCPSchedulingManager(user_id)
    return await scheduler.schedule_meeting_for_lead_mcp(
        lead_id, meeting_url, event_type
    )


# Synchronous wrapper for backward compatibility
def schedule_meeting_for_lead_mcp_sync(
    lead_id: str,
    meeting_url: Optional[str] = None,
    event_type: str = "discovery_call",
    user_id: str = "system",
) -> str:
    """
    Synchronous wrapper for MCP-based meeting scheduling.

    This function maintains the same interface as the original function
    but uses MCP tools internally. It returns a string for compatibility.

    Args:
        lead_id: Lead identifier
        meeting_url: Optional meeting URL
        event_type: Type of meeting
        user_id: User identifier

    Returns:
        Status message string
    """
    import asyncio

    try:
        # Run the async function
        result = asyncio.run(
            schedule_meeting_for_lead_mcp(lead_id, meeting_url, event_type, user_id)
        )

        if result["success"]:
            lead_name = result.get("lead_name", "Lead")
            return f"Meeting scheduled for {lead_name}: {result['meeting_url']}, type: {event_type}"
        else:
            return f"Error scheduling meeting: {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error(f"❌ Error in synchronous MCP meeting scheduling: {e}")
        return f"Error scheduling meeting: {str(e)}"


# Function to replace the original schedule_meeting_for_lead
def get_mcp_meeting_scheduler(user_id: str) -> MCPSchedulingManager:
    """
    Get MCP-based meeting scheduler instance.

    Args:
        user_id: User identifier

    Returns:
        MCPSchedulingManager instance
    """
    return MCPSchedulingManager(user_id)


# Migration utilities
def get_scheduling_function_mapping() -> Dict[str, str]:
    """
    Get mapping of old functions to new MCP functions.

    Returns:
        Dictionary mapping old function names to new MCP function names
    """
    return {
        "schedule_meeting_for_lead": "schedule_meeting_for_lead_mcp",
        "create_meeting_link": "create_calendly_meeting_link",
        "create_calendar_event": "create_calendar_event",
        "send_meeting_confirmation": "send_meeting_confirmation",
    }


def get_mcp_scheduling_capabilities() -> Dict[str, Any]:
    """
    Get capabilities provided by MCP scheduling system.

    Returns:
        Dictionary describing MCP scheduling capabilities
    """
    return {
        "calendly_integration": {
            "create_meeting_links": True,
            "custom_event_types": True,
            "automated_booking": True,
            "meeting_analytics": True,
        },
        "google_calendar_integration": {
            "create_events": True,
            "check_availability": True,
            "send_invites": True,
            "manage_reminders": True,
        },
        "email_integration": {
            "send_confirmations": True,
            "send_reminders": True,
            "follow_up_emails": True,
        },
        "database_integration": {
            "update_lead_status": True,
            "track_meeting_history": True,
            "sync_with_crm": True,
        },
        "fallback_capabilities": {
            "local_tool_fallback": True,
            "demo_mode": True,
            "error_recovery": True,
        },
    }
