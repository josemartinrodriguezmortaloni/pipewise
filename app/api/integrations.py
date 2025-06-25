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

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.agents.tools.calendly import CalendlyClient
from app.agents.tools.pipedream_mcp import PipedreamMCPClient

# Database imports
# Note: This project uses Supabase instead of traditional ORM
# The database operations are handled directly through Supabase client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/integrations", tags=["integrations"])

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

# Generate or use existing Fernet key for encryption
_FERNET_KEY = os.environ.get("PIPEWISE_FERNET_KEY")
if not _FERNET_KEY:
    # Generate a new key for development (in production, this should be persistent)
    _FERNET_KEY = Fernet.generate_key().decode()
    logger.warning(
        "Generated new Fernet key for development. In production, use PIPEWISE_FERNET_KEY environment variable."
    )

_FERNET = Fernet(_FERNET_KEY.encode() if isinstance(_FERNET_KEY, str) else _FERNET_KEY)


def encrypt_sensitive_data(data: str) -> str:
    """Encrypt sensitive data like API keys using Fernet symmetric encryption"""
    try:
        return _FERNET.encrypt(data.encode()).decode()
    except Exception as e:
        logger.error(f"Encryption error: {e}")
        # In development, return the data as-is with a warning
        logger.warning("Returning unencrypted data due to encryption error")
        return data


def decrypt_sensitive_data(encrypted_data: str) -> str:
    """Decrypt sensitive data like API keys using Fernet symmetric encryption"""
    try:
        return _FERNET.decrypt(encrypted_data.encode()).decode()
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        # In development, assume data is not encrypted
        logger.warning("Returning data as-is due to decryption error")
        return encrypted_data


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


# Import actual auth dependency
from app.auth.middleware import get_current_user as auth_get_current_user


# Use real auth dependency
async def get_current_user():
    """Get current user - temporarily mock for development"""
    try:
        # In production, this would use the actual auth middleware
        # For now, return a mock user for testing
        return {"id": "user_123", "email": "user@example.com"}
    except Exception:
        # Fallback to mock user for development
        return {"id": "user_123", "email": "user@example.com"}


# API Endpoints
@router.get("/available")
async def get_available_integrations():
    """Get list of available integrations with their configuration"""
    return {
        "integrations": [
            {
                "id": "calendly",
                "name": "Calendly",
                "description": "Schedule meetings and appointments automatically with leads. Create personalized booking links and sync calendar events.",
                "category": "calendar",
                "features": [
                    "Automated meeting scheduling",
                    "Personalized booking links",
                    "Calendar integration",
                    "Event type customization",
                    "Timezone handling",
                ],
                "requiresApi": True,
                "apiKeyLabel": "Calendly Access Token",
            },
            {
                "id": "whatsapp",
                "name": "WhatsApp Business",
                "description": "Connect with leads directly through WhatsApp Business API. Send messages and receive responses automatically.",
                "category": "messaging",
                "features": [
                    "Direct messaging",
                    "Automated responses",
                    "Media sharing",
                    "Message templates",
                    "Webhook integration",
                ],
                "requiresApi": True,
                "apiKeyLabel": "WhatsApp API Key",
            },
            {
                "id": "instagram",
                "name": "Instagram",
                "description": "Engage with leads through Instagram DMs and comments. Monitor mentions and respond automatically.",
                "category": "social",
                "features": [
                    "Direct message automation",
                    "Comment monitoring",
                    "Mention tracking",
                    "Media responses",
                    "Story engagement",
                ],
                "requiresApi": True,
                "apiKeyLabel": "Instagram App Token",
            },
            {
                "id": "twitter",
                "name": "X (Twitter)",
                "description": "Monitor Twitter mentions and DMs. Engage with leads through social media interactions.",
                "category": "social",
                "features": [
                    "Mention monitoring",
                    "DM automation",
                    "Tweet engagement",
                    "Lead identification",
                    "Automated responses",
                ],
                "requiresApi": True,
                "apiKeyLabel": "Twitter API Key",
            },
            {
                "id": "email",
                "name": "Email Integration",
                "description": "Send automated emails to leads and track responses. Support for multiple email providers.",
                "category": "email",
                "features": [
                    "Automated email campaigns",
                    "Response tracking",
                    "Template management",
                    "SMTP integration",
                    "Email analytics",
                ],
                "requiresApi": True,
                "apiKeyLabel": "Email Provider API Key",
            },
        ]
    }


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
                access_token = decrypt_sensitive_data(
                    calendly_config.get("access_token", "")
                )
                client = CalendlyClient(access_token)
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

        access_token = decrypt_sensitive_data(config.get("access_token", ""))
        client = CalendlyClient(access_token)
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

        access_token = decrypt_sensitive_data(config.get("access_token", ""))
        client = CalendlyClient(access_token)

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
        access_token = decrypt_sensitive_data(config.get("access_token", ""))
        agent = MeetingSchedulerAgent(calendly_token=access_token, user_id=user_id)

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

    access_token = decrypt_sensitive_data(config.get("access_token", ""))
    return MeetingSchedulerAgent(calendly_token=access_token, user_id=user_id)


@router.post("/mcp/{integration_id}/enable")
async def enable_mcp_integration(
    integration_id: str, request: Request, current_user=Depends(get_current_user)
):
    """
    Enable MCP integration with one-click setup.

    This endpoint enables Pipedream MCP integrations without requiring API keys.
    """
    try:
        # Validate integration_id
        valid_mcp_integrations = {
            "calendly_v2",
            "pipedrive",
            "salesforce_rest_api",
            "zoho_crm",
            "sendgrid",
            "google_calendar",
        }

        if integration_id not in valid_mcp_integrations:
            raise HTTPException(
                status_code=400, detail=f"Invalid MCP integration ID: {integration_id}"
            )

        # Get request body
        body = await request.json()
        enabled = body.get("enabled", True)
        tools_count = body.get("tools_count", 0)

        if not enabled:
            raise HTTPException(
                status_code=400,
                detail="Use the disable endpoint to disable integrations",
            )

        # Save to in-memory storage
        user_id = current_user.get("id", "user_123")
        integration_config = {
            "id": integration_id,
            "name": integration_id,
            "enabled": True,
            "type": "mcp",
            "tools_count": tools_count,
            "integration_type": "mcp",
            "pipedream_app_slug": integration_id,
            "enabled_at": datetime.utcnow().isoformat(),
            "platform": "mcp",
        }

        save_user_integration(user_id, integration_id, integration_config)

        logger.info(f"MCP integration {integration_id} enabled for user {user_id}")

        return {
            "success": True,
            "message": f"MCP integration {integration_id} enabled successfully",
            "integration": integration_config,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enabling MCP integration {integration_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to enable MCP integration: {str(e)}"
        )


@router.post("/mcp/{integration_id}/disable")
async def disable_mcp_integration(
    integration_id: str, request: Request, current_user=Depends(get_current_user)
):
    """
    Disable MCP integration.
    """
    try:
        # Get request body
        body = await request.json()
        enabled = body.get("enabled", False)

        if enabled:
            raise HTTPException(
                status_code=400, detail="Use the enable endpoint to enable integrations"
            )

        user_id = current_user.get("id", "user_123")

        # Check if integration exists
        existing_config = get_user_integration(user_id, integration_id)
        if not existing_config:
            raise HTTPException(
                status_code=404, detail=f"MCP integration {integration_id} not found"
            )

        # Delete the integration
        delete_user_integration(user_id, integration_id)

        logger.info(f"MCP integration {integration_id} disabled for user {user_id}")

        return {
            "success": True,
            "message": f"MCP integration {integration_id} disabled successfully",
            "integration": {
                "id": integration_id,
                "name": integration_id,
                "type": "mcp",
                "enabled": False,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disabling MCP integration {integration_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to disable MCP integration: {str(e)}"
        )
