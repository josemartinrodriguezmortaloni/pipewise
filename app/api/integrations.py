"""
Integration Management API for PipeWise

This module handles platform integrations for lead management including:
- Calendly for meeting scheduling
- WhatsApp Business for messaging
- Instagram for social media engagement
- X (Twitter) for social interactions
- Email for communication

Author: AI Assistant
Date: 2025-06-07
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.agents.meeting_scheduler import MeetingSchedulerAgent
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field, EmailStr

from app.agents.tools.calendly import CalendlyClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/integrations", tags=["integrations"])

# Store for user integrations (in production, use database)
user_integrations = {}


# Pydantic Models
class IntegrationConfig(BaseModel):
    """Base configuration for any integration"""

    name: str = Field(..., description="Name of the integration")
    enabled: bool = Field(default=True, description="Whether integration is enabled")
    api_key: Optional[str] = Field(None, description="API key or token")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for callbacks")
    settings: Dict[str, Any] = Field(
        default_factory=dict, description="Additional settings"
    )


class CalendlyConfig(IntegrationConfig):
    """Calendly-specific configuration"""

    access_token: str = Field(..., description="Calendly access token")
    user_uri: Optional[str] = Field(None, description="Calendly user URI")
    default_event_type: Optional[str] = Field(
        default="Sales Call", description="Default event type for meetings"
    )
    timezone: str = Field(default="UTC", description="Default timezone")


class WhatsAppConfig(IntegrationConfig):
    """WhatsApp Business API configuration"""

    phone_number_id: Optional[str] = Field(None, description="WhatsApp phone number ID")
    business_account_id: Optional[str] = Field(
        None, description="WhatsApp business account ID"
    )
    verify_token: Optional[str] = Field(None, description="Webhook verification token")


class SocialMediaConfig(IntegrationConfig):
    """Instagram/Twitter/X configuration"""

    platform: str = Field(..., description="Platform name (instagram, twitter)")
    app_id: Optional[str] = Field(None, description="App ID")
    app_secret: Optional[str] = Field(None, description="App secret")
    access_token: Optional[str] = Field(None, description="Platform access token")
    webhook_secret: Optional[str] = Field(
        None, description="Webhook secret for verification"
    )


class EmailConfig(IntegrationConfig):
    """Email integration configuration"""

    provider: str = Field(..., description="Email provider (smtp, sendgrid, mailgun)")
    smtp_host: Optional[str] = Field(None, description="SMTP host")
    smtp_port: Optional[int] = Field(None, description="SMTP port")
    username: Optional[str] = Field(None, description="Email username")
    password: Optional[str] = Field(None, description="Email password")
    from_email: Optional[EmailStr] = Field(None, description="Default from email")


class IntegrationStatus(BaseModel):
    """Integration status response"""

    id: str
    name: str
    platform: str
    status: str  # connected, disconnected, error, pending
    last_sync: Optional[datetime] = None
    error_message: Optional[str] = None
    stats: Dict[str, Any] = Field(default_factory=dict)
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)


class IntegrationResponse(BaseModel):
    """Standard integration response"""

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    integration_id: Optional[str] = None


class WebhookEvent(BaseModel):
    """Webhook event model"""

    platform: str
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    signature: Optional[str] = None


# Helper functions
from cryptography.fernet import Fernet

_FERNET = Fernet(os.environ["PIPEWISE_FERNET_KEY"])


def encrypt_sensitive_data(data: str) -> str:
    """Encrypt sensitive data like API keys using Fernet symmetric encryption"""
    return _FERNET.encrypt(data.encode()).decode()


def get_user_integration(user_id: str, platform: str) -> Optional[Dict[str, Any]]:
    """Get user integration configuration"""
    return user_integrations.get(f"{user_id}_{platform}")


def save_user_integration(user_id: str, platform: str, config: Dict[str, Any]):
    """Save user integration configuration"""
    user_integrations[f"{user_id}_{platform}"] = {
        **config,
        "updated_at": datetime.utcnow(),
        "user_id": user_id,
        "platform": platform,
    }


def delete_user_integration(user_id: str, platform: str):
    """Delete user integration configuration"""
    key = f"{user_id}_{platform}"
    if key in user_integrations:
        del user_integrations[key]


# Mock user dependency (replace with actual auth)
async def get_current_user():
    return {"id": "user_123", "email": "user@example.com"}


# API Endpoints
@router.get("/", response_model=List[IntegrationStatus])
async def list_integrations(current_user: dict = Depends(get_current_user)):
    """List all available integrations and their status"""
    try:
        user_id = current_user["id"]
        integrations = []

        # Calendly integration
        calendly_config = get_user_integration(user_id, "calendly")
        calendly_status = "disconnected"
        calendly_stats = {"meetings_scheduled": 0, "links_created": 0}
        calendly_error = None

        if calendly_config:
            try:
                # Test Calendly connection
                client = CalendlyClient(calendly_config.get("access_token"))
                health = client.health_check()
                if health["status"] == "healthy":
                    calendly_status = "connected"
                    calendly_stats = {
                        "meetings_scheduled": calendly_config.get(
                            "meetings_scheduled", 0
                        ),
                        "links_created": calendly_config.get("links_created", 0),
                    }
                elif health["status"] == "disabled":
                    calendly_status = "disconnected"
                else:
                    calendly_status = "error"
                    calendly_error = health.get("error", "Connection failed")
            except Exception as e:
                calendly_status = "error"
                calendly_error = str(e)

        integrations.append(
            IntegrationStatus(
                id="calendly",
                name="Calendly",
                platform="calendly",
                status=calendly_status,
                error_message=calendly_error,
                stats=calendly_stats,
                config={"configured": calendly_config is not None},
            )
        )

        # Other integrations
        for platform, name in [
            ("whatsapp", "WhatsApp Business"),
            ("instagram", "Instagram"),
            ("twitter", "X (Twitter)"),
            ("email", "Email Integration"),
        ]:
            config = get_user_integration(user_id, platform)
            integrations.append(
                IntegrationStatus(
                    id=platform,
                    name=name,
                    platform=platform,
                    status="connected" if config else "disconnected",
                    stats={},
                    config={"configured": config is not None},
                )
            )

        return integrations

    except Exception as e:
        logger.error(f"Error listing integrations: {e}")
        raise HTTPException(status_code=500, detail="Failed to list integrations")


@router.post("/calendly/connect", response_model=IntegrationResponse)
async def connect_calendly(
    config: CalendlyConfig, current_user: dict = Depends(get_current_user)
):
    """Connect Calendly integration"""
    try:
        user_id = current_user["id"]

        if not config.access_token:
            raise HTTPException(
                status_code=400, detail="Calendly access token is required"
            )

        # Test connection with the provided token
        client = CalendlyClient(config.access_token)
        health = client.health_check()

        if health["status"] == "unhealthy":
            raise HTTPException(
                status_code=400,
                detail=f"Failed to connect to Calendly: {health.get('error', 'Invalid token')}",
            )

        # Get user info from Calendly
        user_data = client.get_current_user()

        # Save configuration
        integration_config = {
            "access_token": encrypt_sensitive_data(config.access_token),
            "user_uri": user_data["resource"]["uri"],
            "user_name": user_data["resource"]["name"],
            "user_email": user_data["resource"]["email"],
            "default_event_type": config.default_event_type,
            "timezone": config.timezone,
            "settings": config.settings,
            "status": "connected",
            "meetings_scheduled": 0,
            "links_created": 0,
        }

        save_user_integration(user_id, "calendly", integration_config)

        logger.info(f"Calendly integration connected for user {user_id}")

        return IntegrationResponse(
            success=True,
            message=f"Calendly integration connected successfully for {user_data['resource']['name']}",
            integration_id="calendly",
            data={
                "user_name": user_data["resource"]["name"],
                "user_email": user_data["resource"]["email"],
                "timezone": user_data["resource"]["timezone"],
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error connecting Calendly: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to connect Calendly integration"
        )


@router.get("/calendly/status", response_model=IntegrationResponse)
async def get_calendly_status(current_user: dict = Depends(get_current_user)):
    """Get detailed Calendly integration status"""
    try:
        user_id = current_user["id"]
        config = get_user_integration(user_id, "calendly")

        if not config:
            return IntegrationResponse(
                success=False,
                message="Calendly not configured",
                integration_id="calendly",
            )

        client = CalendlyClient(config.get("access_token"))
        health = client.health_check()

        # Get event types
        event_types = []
        try:
            user_data = client.get_current_user()
            events_data = client.get_event_types(user_data["resource"]["uri"])
            event_types = [
                {
                    "name": event["name"],
                    "duration": event["duration"],
                    "active": event["active"],
                }
                for event in events_data["collection"]
            ]
        except:
            pass

        return IntegrationResponse(
            success=True,
            message="Calendly status retrieved",
            integration_id="calendly",
            data={
                "health": health,
                "user_name": config.get("user_name"),
                "user_email": config.get("user_email"),
                "event_types": event_types,
                "stats": {
                    "meetings_scheduled": config.get("meetings_scheduled", 0),
                    "links_created": config.get("links_created", 0),
                },
            },
        )

    except Exception as e:
        logger.error(f"Error getting Calendly status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get Calendly status")


@router.post("/calendly/test", response_model=IntegrationResponse)
async def test_calendly_integration(current_user: dict = Depends(get_current_user)):
    """Test Calendly integration by creating a test link"""
    try:
        user_id = current_user["id"]
        config = get_user_integration(user_id, "calendly")

        if not config:
            raise HTTPException(status_code=404, detail="Calendly not configured")

        client = CalendlyClient(config.get("access_token"))

        # Create a test scheduling link
        result = client.create_personalized_link(
            lead_id="test-lead",
            event_type_name=config.get("default_event_type", "Sales Call"),
        )

        if result.get("success"):
            # Update link counter
            config["links_created"] = config.get("links_created", 0) + 1
            save_user_integration(user_id, "calendly", config)

            return IntegrationResponse(
                success=True,
                message="Test link created successfully",
                integration_id="calendly",
                data={
                    "test_link": result["booking_url"],
                    "event_type": result["event_type"],
                    "fallback": result.get("fallback", False),
                },
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to create test link")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing Calendly: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to test Calendly integration"
        )


@router.post("/whatsapp/connect", response_model=IntegrationResponse)
async def connect_whatsapp(
    config: WhatsAppConfig, current_user: dict = Depends(get_current_user)
):
    """Connect WhatsApp Business integration"""
    try:
        if not config.api_key or not config.phone_number_id:
            raise HTTPException(
                status_code=400,
                detail="WhatsApp API key and phone number ID are required",
            )

        user_id = current_user["id"]

        # Save configuration (implement actual validation)
        integration_config = {
            "api_key": encrypt_sensitive_data(config.api_key),
            "phone_number_id": config.phone_number_id,
            "business_account_id": config.business_account_id,
            "verify_token": config.verify_token,
            "webhook_url": config.webhook_url,
            "settings": config.settings,
            "status": "connected",
        }

        save_user_integration(user_id, "whatsapp", integration_config)

        logger.info(f"WhatsApp integration connected for user {user_id}")

        return IntegrationResponse(
            success=True,
            message="WhatsApp Business integration connected successfully",
            integration_id="whatsapp",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error connecting WhatsApp: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to connect WhatsApp integration"
        )


@router.post("/social/connect", response_model=IntegrationResponse)
async def connect_social_media(
    config: SocialMediaConfig, current_user: dict = Depends(get_current_user)
):
    """Connect social media integration (Instagram, Twitter/X)"""
    try:
        if config.platform not in ["instagram", "twitter"]:
            raise HTTPException(
                status_code=400, detail="Platform must be 'instagram' or 'twitter'"
            )

        user_id = current_user["id"]

        # Save configuration (implement actual validation)
        integration_config = {
            "platform": config.platform,
            "app_id": config.app_id,
            "app_secret": encrypt_sensitive_data(config.app_secret)
            if config.app_secret
            else None,
            "access_token": encrypt_sensitive_data(config.access_token)
            if config.access_token
            else None,
            "webhook_secret": config.webhook_secret,
            "webhook_url": config.webhook_url,
            "settings": config.settings,
            "status": "connected",
        }

        save_user_integration(user_id, config.platform, integration_config)

        logger.info(
            f"{config.platform.title()} integration connected for user {user_id}"
        )

        return IntegrationResponse(
            success=True,
            message=f"{config.platform.title()} integration connected successfully",
            integration_id=config.platform,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error connecting {config.platform}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to connect {config.platform} integration"
        )


@router.post("/email/connect", response_model=IntegrationResponse)
async def connect_email(
    config: EmailConfig, current_user: dict = Depends(get_current_user)
):
    """Connect email integration"""
    try:
        if not config.provider or not config.username or not config.password:
            raise HTTPException(
                status_code=400,
                detail="Email provider, username, and password are required",
            )

        user_id = current_user["id"]

        # Save configuration (implement actual validation)
        integration_config = {
            "provider": config.provider,
            "smtp_host": config.smtp_host,
            "smtp_port": config.smtp_port,
            "username": config.username,
            "password": encrypt_sensitive_data(config.password),
            "from_email": config.from_email,
            "webhook_url": config.webhook_url,
            "settings": config.settings,
            "status": "connected",
        }

        save_user_integration(user_id, "email", integration_config)

        logger.info(f"Email integration connected for user {user_id}")

        return IntegrationResponse(
            success=True,
            message="Email integration connected successfully",
            integration_id="email",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error connecting email: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to connect email integration"
        )


@router.delete("/{integration_id}", response_model=IntegrationResponse)
async def disconnect_integration(
    integration_id: str, current_user: dict = Depends(get_current_user)
):
    """Disconnect an integration"""
    try:
        valid_integrations = ["calendly", "whatsapp", "instagram", "twitter", "email"]
        if integration_id not in valid_integrations:
            raise HTTPException(status_code=404, detail="Integration not found")

        user_id = current_user["id"]

        # Delete integration configuration
        delete_user_integration(user_id, integration_id)

        logger.info(f"Integration {integration_id} disconnected for user {user_id}")

        return IntegrationResponse(
            success=True,
            message=f"{integration_id.title()} integration disconnected successfully",
            integration_id=integration_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting integration {integration_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to disconnect {integration_id} integration"
        )


@router.post("/webhooks/{platform}")
async def handle_webhook(
    platform: str, event: WebhookEvent, background_tasks: BackgroundTasks
):
    """Handle incoming webhooks from integrated platforms"""
    try:
        logger.info(f"Received webhook from {platform}: {event.event_type}")

        valid_platforms = ["calendly", "whatsapp", "instagram", "twitter", "email"]
        if platform not in valid_platforms:
            raise HTTPException(status_code=404, detail="Platform not supported")

        background_tasks.add_task(process_webhook_event, platform, event)

        return {
            "status": "received",
            "platform": platform,
            "event_type": event.event_type,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling webhook from {platform}: {e}")
        raise HTTPException(status_code=500, detail="Failed to process webhook")


async def process_webhook_event(platform: str, event: WebhookEvent):
    """Process webhook event in background"""
    try:
        logger.info(f"Processing {platform} webhook event: {event.event_type}")

        if platform == "calendly" and event.event_type == "invitee.created":
            logger.info("New Calendly meeting scheduled")
            # Update lead status, send notifications, etc.
            # Call meeting_scheduler agent if needed
        elif platform == "whatsapp" and event.event_type == "message":
            logger.info("New WhatsApp message received")
        elif platform == "instagram" and event.event_type == "messages":
            logger.info("New Instagram DM received")
        elif platform == "twitter" and event.event_type == "direct_message_events":
            logger.info("New Twitter DM received")
        elif platform == "email" and event.event_type == "email_received":
            logger.info("New email received")

    except Exception as e:
        logger.error(f"Error processing {platform} webhook: {e}")


# Helper endpoint to get configured Calendly client for meeting scheduler
@router.get("/calendly/client")
async def get_calendly_client_for_agent(current_user: dict = Depends(get_current_user)):
    """Get configured Calendly client for the meeting scheduler agent"""
    try:
        user_id = current_user["id"]
        config = get_user_integration(user_id, "calendly")

        if not config:
            raise HTTPException(status_code=404, detail="Calendly not configured")

        # Return client configuration (not the actual token for security)
        return {
            "configured": True,
            "user_name": config.get("user_name"),
            "default_event_type": config.get("default_event_type"),
            "timezone": config.get("timezone"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Calendly client config: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get Calendly configuration"
        )


@router.post("/calendly/schedule-meeting", response_model=IntegrationResponse)
async def schedule_meeting_with_calendly(
    lead_data: Dict[str, Any], current_user: dict = Depends(get_current_user)
):
    """Schedule a meeting using the meeting scheduler agent with Calendly integration"""
    try:
        user_id = current_user["id"]
        config = get_user_integration(user_id, "calendly")

        if not config:
            raise HTTPException(status_code=404, detail="Calendly not configured")

        # Import here to avoid circular imports
        from app.agents.meeting_scheduler import MeetingSchedulerAgent

        # Create agent with user's Calendly configuration
        agent = MeetingSchedulerAgent(
            calendly_token=config.get("access_token"), user_id=user_id
        )

        # Run the meeting scheduler
        result = await agent.run(lead_data)

        # Update stats if successful
        if result.get("success"):
            config["meetings_scheduled"] = config.get("meetings_scheduled", 0) + 1
            if "meeting_url" in result:
                config["links_created"] = config.get("links_created", 0) + 1
            save_user_integration(user_id, "calendly", config)

        return IntegrationResponse(
            success=result.get("success", False),
            message=result.get("message", "Meeting scheduling completed"),
            integration_id="calendly",
            data={
                "meeting_url": result.get("meeting_url"),
                "event_type": result.get("event_type"),
                "lead_status": result.get("lead_status"),
                "conversation_id": result.get("conversation_id"),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scheduling meeting with Calendly: {e}")
        raise HTTPException(status_code=500, detail="Failed to schedule meeting")


def get_user_calendly_config(user_id: str) -> Optional[Dict[str, Any]]:
    """Helper function to get user's Calendly configuration for other agents"""
    return get_user_integration(user_id, "calendly")


def create_meeting_scheduler_for_user(user_id: str) -> "MeetingSchedulerAgent":
    """Helper function to create a meeting scheduler agent with user's Calendly config"""
    config = get_user_integration(user_id, "calendly")

    if not config:
        # Return agent with no token (will use fallback mode)
        from app.agents.meeting_scheduler import MeetingSchedulerAgent

        return MeetingSchedulerAgent(calendly_token=None, user_id=user_id)

    from app.agents.meeting_scheduler import MeetingSchedulerAgent

    return MeetingSchedulerAgent(
        calendly_token=config.get("access_token"), user_id=user_id
    )
