"""
Coordinator Agent MCP Configurations

This module provides MCP configurations specifically for the Coordinator Agent.
The Coordinator Agent handles:
- SendGrid MCP for email marketing and transactional emails
- Twitter MCP for social media outreach and engagement

Key Features:
- Email marketing campaigns via SendGrid
- Transactional email sending
- Twitter posting and engagement
- Social media scheduling
- Lead communication workflows
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


class CoordinatorMCPType(Enum):
    """Types of MCPs used by Coordinator Agent"""

    SENDGRID = "sendgrid"
    TWITTER = "twitter"


class EmailType(Enum):
    """Types of emails supported by SendGrid MCP"""

    MARKETING = "marketing"
    TRANSACTIONAL = "transactional"
    WELCOME = "welcome"
    FOLLOW_UP = "follow_up"
    NEWSLETTER = "newsletter"


class TwitterActionType(Enum):
    """Types of Twitter actions supported by Twitter MCP"""

    TWEET = "tweet"
    REPLY = "reply"
    RETWEET = "retweet"
    DIRECT_MESSAGE = "direct_message"
    LIKE = "like"
    FOLLOW = "follow"


class CoordinatorAgentMCPManager:
    """
    MCP Manager for Coordinator Agent.

    Manages SendGrid and Twitter MCP configurations and operations
    specifically for the Coordinator Agent's communication workflows.
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.error_handler = get_error_handler()
        self.analytics_logger = get_oauth_analytics_logger()
        self._mcp_cache = {}

    @retry_mcp_operation(
        max_attempts=3, service_name="coordinator_sendgrid", log_attempts=True
    )
    async def configure_sendgrid_mcp(self) -> Dict[str, Any]:
        """
        Configure SendGrid MCP for email marketing and transactional emails.

        Returns:
            SendGrid MCP configuration with tools and credentials

        Raises:
            MCPConfigurationError: If configuration fails
            MCPAuthenticationError: If OAuth authentication fails
        """
        try:
            # Get OAuth tokens for SendGrid
            sendgrid_tokens = await self._get_oauth_tokens("sendgrid")

            if not sendgrid_tokens:
                logger.warning(
                    f"⚠️ No SendGrid OAuth tokens for user {self.user_id}, using demo mode"
                )
                return self._get_demo_sendgrid_config()

            # Get MCP credentials
            mcp_credentials = get_mcp_credentials_for_service(
                sendgrid_tokens, "sendgrid", self.user_id
            )

            # Configure SendGrid MCP with specific tools
            sendgrid_config = {
                "service_name": "sendgrid",
                "service_type": "email_marketing",
                "credentials": mcp_credentials.to_dict(),
                "tools": [
                    {
                        "name": "send_marketing_email",
                        "description": "Send marketing emails to lead lists",
                        "parameters": {
                            "to_emails": {"type": "array", "items": {"type": "string"}},
                            "subject": {"type": "string"},
                            "html_content": {"type": "string"},
                            "template_id": {"type": "string", "required": False},
                            "list_id": {"type": "string", "required": False},
                            "campaign_id": {"type": "string", "required": False},
                        },
                        "pipedream_action": "sendgrid_send_marketing_email",
                    },
                    {
                        "name": "send_transactional_email",
                        "description": "Send transactional emails (welcome, follow-up, etc.)",
                        "parameters": {
                            "to_email": {"type": "string"},
                            "subject": {"type": "string"},
                            "html_content": {"type": "string"},
                            "template_id": {"type": "string", "required": False},
                            "dynamic_template_data": {
                                "type": "object",
                                "required": False,
                            },
                            "email_type": {
                                "type": "string",
                                "enum": ["welcome", "follow_up", "thank_you"],
                            },
                        },
                        "pipedream_action": "sendgrid_send_transactional_email",
                    },
                    {
                        "name": "create_email_list",
                        "description": "Create email list for lead segmentation",
                        "parameters": {
                            "name": {"type": "string"},
                            "description": {"type": "string", "required": False},
                        },
                        "pipedream_action": "sendgrid_create_list",
                    },
                    {
                        "name": "add_contact_to_list",
                        "description": "Add contact to email list",
                        "parameters": {
                            "email": {"type": "string"},
                            "first_name": {"type": "string", "required": False},
                            "last_name": {"type": "string", "required": False},
                            "list_id": {"type": "string"},
                            "custom_fields": {"type": "object", "required": False},
                        },
                        "pipedream_action": "sendgrid_add_contact_to_list",
                    },
                    {
                        "name": "get_email_stats",
                        "description": "Get email campaign statistics",
                        "parameters": {
                            "start_date": {"type": "string", "format": "date"},
                            "end_date": {"type": "string", "format": "date"},
                            "campaign_id": {"type": "string", "required": False},
                        },
                        "pipedream_action": "sendgrid_get_stats",
                    },
                    {
                        "name": "create_email_template",
                        "description": "Create reusable email template",
                        "parameters": {
                            "name": {"type": "string"},
                            "subject": {"type": "string"},
                            "html_content": {"type": "string"},
                            "template_type": {
                                "type": "string",
                                "enum": ["marketing", "transactional"],
                            },
                        },
                        "pipedream_action": "sendgrid_create_template",
                    },
                ],
                "configuration": {
                    "sender_verification": True,
                    "tracking_enabled": True,
                    "click_tracking": True,
                    "open_tracking": True,
                    "subscription_tracking": True,
                    "default_from_email": f"coordinator@pipewise.com",
                    "default_from_name": "PipeWise Coordinator",
                    "api_version": "v3",
                },
                "rate_limits": {
                    "marketing_emails_per_hour": 100,
                    "transactional_emails_per_hour": 500,
                    "api_calls_per_minute": 600,
                },
            }

            # Cache configuration
            self._mcp_cache["sendgrid"] = sendgrid_config

            # Log successful configuration
            self.analytics_logger.log_mcp_creation(
                user_id=self.user_id,
                service_name="sendgrid",
                oauth_provider=OAuthProvider.SENDGRID,
                success=True,
                context={
                    "agent_type": "coordinator",
                    "tools_count": len(sendgrid_config["tools"]),
                },
            )

            logger.info(
                f"✅ SendGrid MCP configured for Coordinator Agent (user: {self.user_id})"
            )

            return sendgrid_config

        except Exception as e:
            mcp_error = self.error_handler.handle_error(
                e,
                service_name="sendgrid",
                operation="configure_sendgrid_mcp",
                context={"user_id": self.user_id, "agent_type": "coordinator"},
            )

            # Log failed configuration
            self.analytics_logger.log_mcp_creation(
                user_id=self.user_id,
                service_name="sendgrid",
                oauth_provider=OAuthProvider.SENDGRID,
                success=False,
                error_message=mcp_error.get_user_friendly_message(),
                context={"agent_type": "coordinator"},
            )

            logger.error(
                f"❌ Failed to configure SendGrid MCP: {mcp_error.get_user_friendly_message()}"
            )
            raise mcp_error

    @retry_mcp_operation(
        max_attempts=3, service_name="coordinator_twitter", log_attempts=True
    )
    async def configure_twitter_mcp(self) -> Dict[str, Any]:
        """
        Configure Twitter MCP for social media outreach and engagement.

        Returns:
            Twitter MCP configuration with tools and credentials

        Raises:
            MCPConfigurationError: If configuration fails
            MCPAuthenticationError: If OAuth authentication fails
        """
        try:
            # Get OAuth tokens for Twitter
            twitter_tokens = await self._get_oauth_tokens("twitter")

            if not twitter_tokens:
                logger.warning(
                    f"⚠️ No Twitter OAuth tokens for user {self.user_id}, using demo mode"
                )
                return self._get_demo_twitter_config()

            # Get MCP credentials
            mcp_credentials = get_mcp_credentials_for_service(
                twitter_tokens, "twitter", self.user_id
            )

            # Configure Twitter MCP with specific tools
            twitter_config = {
                "service_name": "twitter",
                "service_type": "social_media",
                "credentials": mcp_credentials.to_dict(),
                "tools": [
                    {
                        "name": "post_tweet",
                        "description": "Post tweet for lead engagement and company updates",
                        "parameters": {
                            "text": {"type": "string", "maxLength": 280},
                            "media_urls": {
                                "type": "array",
                                "items": {"type": "string"},
                                "required": False,
                            },
                            "reply_to_tweet_id": {"type": "string", "required": False},
                            "quote_tweet_id": {"type": "string", "required": False},
                        },
                        "pipedream_action": "twitter_post_tweet",
                    },
                    {
                        "name": "send_direct_message",
                        "description": "Send direct message to prospects or leads",
                        "parameters": {
                            "recipient_username": {"type": "string"},
                            "message": {"type": "string", "maxLength": 10000},
                            "media_url": {"type": "string", "required": False},
                        },
                        "pipedream_action": "twitter_send_dm",
                    },
                    {
                        "name": "search_tweets",
                        "description": "Search tweets for lead generation and engagement opportunities",
                        "parameters": {
                            "query": {"type": "string"},
                            "max_results": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 100,
                            },
                            "tweet_fields": {
                                "type": "array",
                                "items": {"type": "string"},
                                "required": False,
                            },
                        },
                        "pipedream_action": "twitter_search_tweets",
                    },
                    {
                        "name": "get_user_profile",
                        "description": "Get user profile information for lead qualification",
                        "parameters": {
                            "username": {"type": "string"},
                            "user_fields": {
                                "type": "array",
                                "items": {"type": "string"},
                                "required": False,
                            },
                        },
                        "pipedream_action": "twitter_get_user_profile",
                    },
                    {
                        "name": "follow_user",
                        "description": "Follow potential leads or industry influencers",
                        "parameters": {
                            "username": {"type": "string"},
                        },
                        "pipedream_action": "twitter_follow_user",
                    },
                    {
                        "name": "like_tweet",
                        "description": "Like tweets for engagement and relationship building",
                        "parameters": {
                            "tweet_id": {"type": "string"},
                        },
                        "pipedream_action": "twitter_like_tweet",
                    },
                    {
                        "name": "retweet",
                        "description": "Retweet content for thought leadership and engagement",
                        "parameters": {
                            "tweet_id": {"type": "string"},
                            "comment": {"type": "string", "required": False},
                        },
                        "pipedream_action": "twitter_retweet",
                    },
                    {
                        "name": "get_tweet_analytics",
                        "description": "Get analytics for posted tweets",
                        "parameters": {
                            "tweet_ids": {"type": "array", "items": {"type": "string"}},
                            "metrics": {
                                "type": "array",
                                "items": {"type": "string"},
                                "required": False,
                            },
                        },
                        "pipedream_action": "twitter_get_tweet_analytics",
                    },
                ],
                "configuration": {
                    "api_version": "2.0",
                    "user_context": True,
                    "max_requests_per_window": 300,
                    "rate_limit_window": 900,  # 15 minutes
                    "default_tweet_fields": [
                        "id",
                        "text",
                        "author_id",
                        "created_at",
                        "public_metrics",
                    ],
                    "default_user_fields": [
                        "id",
                        "name",
                        "username",
                        "description",
                        "public_metrics",
                    ],
                },
                "rate_limits": {
                    "tweets_per_hour": 50,
                    "dms_per_hour": 100,
                    "follows_per_hour": 20,
                    "api_calls_per_minute": 100,
                },
            }

            # Cache configuration
            self._mcp_cache["twitter"] = twitter_config

            # Log successful configuration
            self.analytics_logger.log_mcp_creation(
                user_id=self.user_id,
                service_name="twitter",
                oauth_provider=OAuthProvider.TWITTER,
                success=True,
                context={
                    "agent_type": "coordinator",
                    "tools_count": len(twitter_config["tools"]),
                },
            )

            logger.info(
                f"✅ Twitter MCP configured for Coordinator Agent (user: {self.user_id})"
            )

            return twitter_config

        except Exception as e:
            mcp_error = self.error_handler.handle_error(
                e,
                service_name="twitter",
                operation="configure_twitter_mcp",
                context={"user_id": self.user_id, "agent_type": "coordinator"},
            )

            # Log failed configuration
            self.analytics_logger.log_mcp_creation(
                user_id=self.user_id,
                service_name="twitter",
                oauth_provider=OAuthProvider.TWITTER,
                success=False,
                error_message=mcp_error.get_user_friendly_message(),
                context={"agent_type": "coordinator"},
            )

            logger.error(
                f"❌ Failed to configure Twitter MCP: {mcp_error.get_user_friendly_message()}"
            )
            raise mcp_error

    async def get_coordinator_mcp_configuration(self) -> Dict[str, Any]:
        """
        Get complete MCP configuration for Coordinator Agent.

        Returns:
            Dictionary with SendGrid and Twitter MCP configurations
        """
        try:
            # Configure both MCPs
            sendgrid_config = await self.configure_sendgrid_mcp()
            twitter_config = await self.configure_twitter_mcp()

            coordinator_config = {
                "agent_type": "coordinator",
                "agent_name": "PipeWise Coordinator",
                "description": "Handles email marketing and social media outreach",
                "user_id": self.user_id,
                "mcps": {
                    "sendgrid": sendgrid_config,
                    "twitter": twitter_config,
                },
                "capabilities": [
                    "email_marketing",
                    "transactional_emails",
                    "social_media_posting",
                    "lead_engagement",
                    "campaign_management",
                    "analytics_tracking",
                ],
                "workflows": {
                    "lead_welcome": {
                        "steps": [
                            {"tool": "send_transactional_email", "template": "welcome"},
                            {"tool": "add_contact_to_list", "list": "new_leads"},
                            {"tool": "post_tweet", "content": "engagement_post"},
                        ],
                    },
                    "follow_up_sequence": {
                        "steps": [
                            {
                                "tool": "send_transactional_email",
                                "template": "follow_up_day_1",
                            },
                            {"tool": "send_direct_message", "platform": "twitter"},
                            {
                                "tool": "send_transactional_email",
                                "template": "follow_up_day_7",
                            },
                        ],
                    },
                    "social_engagement": {
                        "steps": [
                            {"tool": "search_tweets", "query": "industry_keywords"},
                            {"tool": "like_tweet", "target": "relevant_tweets"},
                            {"tool": "follow_user", "target": "potential_leads"},
                        ],
                    },
                },
                "configuration": {
                    "communication_channels": ["email", "twitter"],
                    "automation_enabled": True,
                    "analytics_tracking": True,
                    "rate_limiting": True,
                },
                "created_at": datetime.now().isoformat(),
            }

            logger.info(
                f"✅ Complete Coordinator MCP configuration ready for user {self.user_id}"
            )

            return coordinator_config

        except Exception as e:
            logger.error(
                f"❌ Failed to get complete Coordinator MCP configuration: {e}"
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
            return OAuthTokens(
                access_token="coordinator_demo_token",
                provider=OAuthProvider.SENDGRID
                if service_name == "sendgrid"
                else OAuthProvider.TWITTER,
                user_id=self.user_id,
            )

        except Exception as e:
            logger.debug(f"⚪ Could not get OAuth tokens for {service_name}: {e}")
            return None

    def _get_demo_sendgrid_config(self) -> Dict[str, Any]:
        """Get demo SendGrid configuration for development"""
        return {
            "service_name": "sendgrid",
            "service_type": "email_marketing",
            "demo_mode": True,
            "credentials": {
                "service_name": "sendgrid",
                "headers": {
                    "Authorization": f"Bearer demo_sendgrid_token_{self.user_id}",
                    "Content-Type": "application/json",
                },
                "auth_type": "demo",
            },
            "tools": [
                {
                    "name": "send_marketing_email",
                    "description": "Send marketing emails to lead lists (DEMO MODE)",
                    "demo_response": {
                        "message": "Demo email sent successfully",
                        "email_id": "demo_12345",
                    },
                },
                {
                    "name": "send_transactional_email",
                    "description": "Send transactional emails (DEMO MODE)",
                    "demo_response": {
                        "message": "Demo transactional email sent",
                        "email_id": "demo_67890",
                    },
                },
            ],
            "configuration": {
                "demo_mode": True,
                "sender_verification": False,
                "tracking_enabled": False,
            },
        }

    def _get_demo_twitter_config(self) -> Dict[str, Any]:
        """Get demo Twitter configuration for development"""
        return {
            "service_name": "twitter",
            "service_type": "social_media",
            "demo_mode": True,
            "credentials": {
                "service_name": "twitter",
                "headers": {
                    "Authorization": f"Bearer demo_twitter_token_{self.user_id}",
                    "Content-Type": "application/json",
                },
                "auth_type": "demo",
            },
            "tools": [
                {
                    "name": "post_tweet",
                    "description": "Post tweet for lead engagement (DEMO MODE)",
                    "demo_response": {
                        "message": "Demo tweet posted",
                        "tweet_id": "demo_tweet_123",
                    },
                },
                {
                    "name": "send_direct_message",
                    "description": "Send direct message to prospects (DEMO MODE)",
                    "demo_response": {
                        "message": "Demo DM sent",
                        "dm_id": "demo_dm_456",
                    },
                },
            ],
            "configuration": {
                "demo_mode": True,
                "api_version": "2.0",
                "user_context": False,
            },
        }

    def clear_cache(self) -> None:
        """Clear MCP configuration cache"""
        self._mcp_cache.clear()
        logger.info("🧹 Cleared Coordinator MCP cache")


# Helper functions
async def get_coordinator_mcp_configuration(user_id: str) -> Dict[str, Any]:
    """
    Get MCP configuration for Coordinator Agent.

    Args:
        user_id: User identifier

    Returns:
        Complete MCP configuration for Coordinator Agent
    """
    manager = CoordinatorAgentMCPManager(user_id)
    return await manager.get_coordinator_mcp_configuration()


async def configure_coordinator_sendgrid(user_id: str) -> Dict[str, Any]:
    """
    Configure SendGrid MCP for Coordinator Agent.

    Args:
        user_id: User identifier

    Returns:
        SendGrid MCP configuration
    """
    manager = CoordinatorAgentMCPManager(user_id)
    return await manager.configure_sendgrid_mcp()


async def configure_coordinator_twitter(user_id: str) -> Dict[str, Any]:
    """
    Configure Twitter MCP for Coordinator Agent.

    Args:
        user_id: User identifier

    Returns:
        Twitter MCP configuration
    """
    manager = CoordinatorAgentMCPManager(user_id)
    return await manager.configure_twitter_mcp()


def get_coordinator_supported_tools() -> List[str]:
    """
    Get list of tools supported by Coordinator Agent MCPs.

    Returns:
        List of supported tool names
    """
    return [
        # SendGrid tools
        "send_marketing_email",
        "send_transactional_email",
        "create_email_list",
        "add_contact_to_list",
        "get_email_stats",
        "create_email_template",
        # Twitter tools
        "post_tweet",
        "send_direct_message",
        "search_tweets",
        "get_user_profile",
        "follow_user",
        "like_tweet",
        "retweet",
        "get_tweet_analytics",
    ]


def get_coordinator_workflow_templates() -> Dict[str, Dict[str, Any]]:
    """
    Get workflow templates for Coordinator Agent.

    Returns:
        Dictionary of workflow templates
    """
    return {
        "lead_welcome": {
            "name": "Lead Welcome Sequence",
            "description": "Welcome new leads with email and social media engagement",
            "steps": [
                {
                    "step": 1,
                    "tool": "send_transactional_email",
                    "template": "welcome",
                    "description": "Send welcome email to new lead",
                },
                {
                    "step": 2,
                    "tool": "add_contact_to_list",
                    "list": "new_leads",
                    "description": "Add lead to new leads email list",
                },
                {
                    "step": 3,
                    "tool": "post_tweet",
                    "content": "engagement_post",
                    "description": "Post engagement tweet about new connection",
                },
            ],
        },
        "follow_up_sequence": {
            "name": "Lead Follow-up Sequence",
            "description": "Multi-channel follow-up sequence for leads",
            "steps": [
                {
                    "step": 1,
                    "tool": "send_transactional_email",
                    "template": "follow_up_day_1",
                    "description": "Send day 1 follow-up email",
                },
                {
                    "step": 2,
                    "tool": "send_direct_message",
                    "platform": "twitter",
                    "description": "Send Twitter DM for personal touch",
                },
                {
                    "step": 3,
                    "tool": "send_transactional_email",
                    "template": "follow_up_day_7",
                    "description": "Send day 7 follow-up email",
                },
            ],
        },
        "social_engagement": {
            "name": "Social Media Engagement",
            "description": "Automated social media engagement for lead generation",
            "steps": [
                {
                    "step": 1,
                    "tool": "search_tweets",
                    "query": "industry_keywords",
                    "description": "Search for relevant industry tweets",
                },
                {
                    "step": 2,
                    "tool": "like_tweet",
                    "target": "relevant_tweets",
                    "description": "Like relevant tweets for engagement",
                },
                {
                    "step": 3,
                    "tool": "follow_user",
                    "target": "potential_leads",
                    "description": "Follow potential leads identified",
                },
            ],
        },
    }
