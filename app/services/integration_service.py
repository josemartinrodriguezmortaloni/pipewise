"""
Integration Service for PipeWise

This service provides a clean interface for agents to work with platform integrations.
It handles the coordination between different agents and their respective integrations.

Author: AI Assistant
Date: 2025-06-07
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class IntegrationService:
    """Service to manage integrations for agents"""

    def __init__(self):
        # Import here to avoid circular imports
        from app.api.integrations import get_user_integration, save_user_integration

        self._get_user_integration = get_user_integration
        self._save_user_integration = save_user_integration

    def get_calendly_config(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's Calendly configuration"""
        try:
            return self._get_user_integration(user_id, "calendly")
        except Exception as e:
            logger.error(f"Error getting Calendly config for user {user_id}: {e}")
            return None

    def is_calendly_configured(self, user_id: str) -> bool:
        """Check if user has Calendly configured"""
        config = self.get_calendly_config(user_id)
        return config is not None and config.get("status") == "connected"

    def create_meeting_scheduler(self, user_id: str, lead_data: Dict[str, Any] = None):
        """Create a meeting scheduler agent with user's Calendly configuration"""
        try:
            from app.agents.meeting_scheduler import MeetingSchedulerAgent

            config = self.get_calendly_config(user_id)

            if config and config.get("access_token"):
                logger.info(
                    f"Creating meeting scheduler with Calendly token for user {user_id}"
                )
                return MeetingSchedulerAgent(
                    calendly_token=config.get("access_token"), user_id=user_id
                )
            else:
                logger.info(
                    f"Creating meeting scheduler in fallback mode for user {user_id}"
                )
                return MeetingSchedulerAgent(calendly_token=None, user_id=user_id)

        except Exception as e:
            logger.error(f"Error creating meeting scheduler for user {user_id}: {e}")
            raise

    async def schedule_meeting(
        self, user_id: str, lead_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Schedule a meeting using the meeting scheduler agent"""
        try:
            # Create meeting scheduler with user's configuration
            scheduler = self.create_meeting_scheduler(user_id, lead_data)

            # Run the scheduler
            result = await scheduler.run(lead_data)

            # Update stats if successful
            if result.get("success"):
                config = self.get_calendly_config(user_id)
                if config:
                    config["meetings_scheduled"] = (
                        config.get("meetings_scheduled", 0) + 1
                    )
                    if "meeting_url" in result:
                        config["links_created"] = config.get("links_created", 0) + 1
                    config["last_meeting_scheduled"] = datetime.utcnow().isoformat()
                    self._save_user_integration(user_id, "calendly", config)

            return result

        except Exception as e:
            logger.error(f"Error scheduling meeting for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "meeting_url": "https://calendly.com/contact-support",
                "event_type": "Error - Scheduling Failed",
                "lead_status": "meeting_scheduled_error",
            }

    def get_integration_status(self, user_id: str, platform: str) -> Dict[str, Any]:
        """Get status of a specific integration"""
        try:
            config = self._get_user_integration(user_id, platform)

            if not config:
                return {
                    "platform": platform,
                    "status": "disconnected",
                    "configured": False,
                }

            # Test connection based on platform
            if platform == "calendly":
                return self._test_calendly_connection(config)
            else:
                return {
                    "platform": platform,
                    "status": config.get("status", "unknown"),
                    "configured": True,
                    "last_updated": config.get("updated_at"),
                }

        except Exception as e:
            logger.error(f"Error getting {platform} status for user {user_id}: {e}")
            return {"platform": platform, "status": "error", "error": str(e)}

    def _test_calendly_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test Calendly connection"""
        try:
            from app.agents.tools.calendly import CalendlyClient

            client = CalendlyClient(config.get("access_token"))
            health = client.health_check()

            return {
                "platform": "calendly",
                "status": health["status"],
                "configured": True,
                "user_name": config.get("user_name"),
                "meetings_scheduled": config.get("meetings_scheduled", 0),
                "links_created": config.get("links_created", 0),
                "last_updated": config.get("updated_at"),
                "health_details": health,
            }

        except Exception as e:
            logger.error(f"Error testing Calendly connection: {e}")
            return {
                "platform": "calendly",
                "status": "error",
                "configured": True,
                "error": str(e),
            }

    def get_available_integrations(self, user_id: str) -> Dict[str, Dict[str, Any]]:
        """Get all available integrations and their status"""
        integrations = {}

        platforms = ["calendly", "whatsapp", "instagram", "twitter", "email"]

        for platform in platforms:
            integrations[platform] = self.get_integration_status(user_id, platform)

        return integrations

    def is_meeting_scheduling_available(self, user_id: str) -> bool:
        """Check if meeting scheduling is available for user"""
        calendly_status = self.get_integration_status(user_id, "calendly")
        return calendly_status["status"] in [
            "healthy",
            "disabled",
        ]  # disabled means fallback mode

    def get_meeting_scheduler_capabilities(self, user_id: str) -> Dict[str, Any]:
        """Get meeting scheduler capabilities based on integrations"""
        calendly_config = self.get_calendly_config(user_id)

        if calendly_config:
            return {
                "scheduling_available": True,
                "platform": "calendly",
                "features": [
                    "personalized_links",
                    "event_type_selection",
                    "availability_checking",
                    "automatic_lead_updates",
                ],
                "default_event_type": calendly_config.get(
                    "default_event_type", "Sales Call"
                ),
                "user_name": calendly_config.get("user_name"),
                "timezone": calendly_config.get("timezone", "UTC"),
            }
        else:
            return {
                "scheduling_available": True,
                "platform": "fallback",
                "features": ["basic_links", "simulated_scheduling"],
                "default_event_type": "Sales Call",
                "note": "Using fallback mode - connect Calendly for full features",
            }


# Global instance for easy import
integration_service = IntegrationService()
