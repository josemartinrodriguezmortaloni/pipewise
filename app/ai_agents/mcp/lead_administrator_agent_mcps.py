"""
Lead Administrator Agent MCP Configurations

This module provides MCP configurations for the Lead Administrator Agent.
Handles Pipedrive, Salesforce, and Zoho CRM integrations.

Key Features:
- Pipedrive MCP for pipeline management
- Salesforce MCP for enterprise CRM
- Zoho CRM MCP for alternative CRM
- Lead tracking and management
- CRM synchronization

Following PRD: Task 4.0 - Implementar MCPs Específicos por Agente
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum

from .oauth_integration import (
    OAuthTokens,
    MCPCredentials,
    OAuthProvider,
    get_mcp_credentials_for_service,
)
from .oauth_analytics_logger import get_oauth_analytics_logger
from .error_handler import get_error_handler
from .retry_handler import retry_mcp_operation

logger = logging.getLogger(__name__)


class CRMType(Enum):
    """Types of CRM systems supported"""

    PIPEDRIVE = "pipedrive"
    SALESFORCE = "salesforce"
    ZOHO = "zoho"


class LeadAdministratorAgentMCPManager:
    """MCP Manager for Lead Administrator Agent"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.error_handler = get_error_handler()
        self.analytics_logger = get_oauth_analytics_logger()
        self._mcp_cache = {}

    @retry_mcp_operation(
        max_attempts=3, service_name="admin_pipedrive", log_attempts=True
    )
    async def configure_pipedrive_mcp(self) -> Dict[str, Any]:
        """Configure Pipedrive MCP for CRM operations"""
        try:
            pipedrive_tokens = await self._get_oauth_tokens("pipedrive")

            if not pipedrive_tokens:
                logger.warning(
                    f"⚠️ No Pipedrive OAuth tokens for user {self.user_id}, using demo mode"
                )
                return self._get_demo_pipedrive_config()

            mcp_credentials = get_mcp_credentials_for_service(
                pipedrive_tokens, "pipedrive", self.user_id
            )

            pipedrive_config = {
                "service_name": "pipedrive",
                "service_type": "crm",
                "credentials": mcp_credentials.to_dict(),
                "tools": [
                    {
                        "name": "create_deal",
                        "description": "Create new deal in Pipedrive",
                        "parameters": {
                            "title": {"type": "string"},
                            "value": {"type": "number", "required": False},
                            "currency": {"type": "string", "default": "USD"},
                            "org_id": {"type": "integer", "required": False},
                            "person_id": {"type": "integer", "required": False},
                            "stage_id": {"type": "integer", "required": False},
                        },
                        "pipedream_action": "pipedrive_create_deal",
                    },
                    {
                        "name": "update_deal",
                        "description": "Update existing deal in Pipedrive",
                        "parameters": {
                            "deal_id": {"type": "integer"},
                            "title": {"type": "string", "required": False},
                            "stage_id": {"type": "integer", "required": False},
                            "status": {"type": "string", "required": False},
                            "value": {"type": "number", "required": False},
                        },
                        "pipedream_action": "pipedrive_update_deal",
                    },
                    {
                        "name": "create_person",
                        "description": "Create person in Pipedrive",
                        "parameters": {
                            "name": {"type": "string"},
                            "email": {"type": "string", "required": False},
                            "phone": {"type": "string", "required": False},
                            "org_id": {"type": "integer", "required": False},
                        },
                        "pipedream_action": "pipedrive_create_person",
                    },
                    {
                        "name": "get_deals",
                        "description": "Get deals from Pipedrive",
                        "parameters": {
                            "status": {
                                "type": "string",
                                "enum": ["open", "won", "lost"],
                                "default": "open",
                            },
                            "limit": {"type": "integer", "default": 50},
                        },
                        "pipedream_action": "pipedrive_get_deals",
                    },
                ],
                "configuration": {
                    "api_version": "v1",
                    "default_currency": "USD",
                    "sync_enabled": True,
                },
                "rate_limits": {
                    "api_calls_per_minute": 100,
                    "deals_per_hour": 200,
                },
            }

            self._mcp_cache["pipedrive"] = pipedrive_config

            self.analytics_logger.log_mcp_creation(
                user_id=self.user_id,
                service_name="pipedrive",
                oauth_provider=OAuthProvider.PIPEDRIVE,
                success=True,
                context={
                    "agent_type": "lead_administrator",
                    "tools_count": len(pipedrive_config["tools"]),
                },
            )

            logger.info(
                f"✅ Pipedrive MCP configured for Lead Administrator Agent (user: {self.user_id})"
            )
            return pipedrive_config

        except Exception as e:
            mcp_error = self.error_handler.handle_error(
                e, service_name="pipedrive", operation="configure_pipedrive_mcp"
            )
            logger.error(
                f"❌ Failed to configure Pipedrive MCP: {mcp_error.get_user_friendly_message()}"
            )
            raise mcp_error

    @retry_mcp_operation(
        max_attempts=3, service_name="admin_salesforce", log_attempts=True
    )
    async def configure_salesforce_mcp(self) -> Dict[str, Any]:
        """Configure Salesforce MCP for enterprise CRM"""
        try:
            salesforce_tokens = await self._get_oauth_tokens("salesforce")

            if not salesforce_tokens:
                logger.warning(
                    f"⚠️ No Salesforce OAuth tokens for user {self.user_id}, using demo mode"
                )
                return self._get_demo_salesforce_config()

            mcp_credentials = get_mcp_credentials_for_service(
                salesforce_tokens, "salesforce", self.user_id
            )

            salesforce_config = {
                "service_name": "salesforce",
                "service_type": "crm",
                "credentials": mcp_credentials.to_dict(),
                "tools": [
                    {
                        "name": "create_opportunity",
                        "description": "Create opportunity in Salesforce",
                        "parameters": {
                            "name": {"type": "string"},
                            "stage_name": {"type": "string"},
                            "close_date": {"type": "string", "format": "date"},
                            "amount": {"type": "number", "required": False},
                            "account_id": {"type": "string", "required": False},
                        },
                        "pipedream_action": "salesforce_create_opportunity",
                    },
                    {
                        "name": "create_lead",
                        "description": "Create lead in Salesforce",
                        "parameters": {
                            "first_name": {"type": "string", "required": False},
                            "last_name": {"type": "string"},
                            "email": {"type": "string", "required": False},
                            "company": {"type": "string"},
                            "phone": {"type": "string", "required": False},
                        },
                        "pipedream_action": "salesforce_create_lead",
                    },
                    {
                        "name": "update_lead",
                        "description": "Update lead in Salesforce",
                        "parameters": {
                            "lead_id": {"type": "string"},
                            "status": {"type": "string", "required": False},
                            "rating": {"type": "string", "required": False},
                        },
                        "pipedream_action": "salesforce_update_lead",
                    },
                    {
                        "name": "get_leads",
                        "description": "Get leads from Salesforce",
                        "parameters": {
                            "status": {"type": "string", "required": False},
                            "limit": {"type": "integer", "default": 50},
                        },
                        "pipedream_action": "salesforce_get_leads",
                    },
                ],
                "configuration": {
                    "api_version": "v61.0",
                    "instance_url": "https://login.salesforce.com",
                    "sync_enabled": True,
                },
                "rate_limits": {
                    "api_calls_per_minute": 100,
                    "leads_per_hour": 300,
                },
            }

            self._mcp_cache["salesforce"] = salesforce_config

            self.analytics_logger.log_mcp_creation(
                user_id=self.user_id,
                service_name="salesforce",
                oauth_provider=OAuthProvider.SALESFORCE,
                success=True,
                context={
                    "agent_type": "lead_administrator",
                    "tools_count": len(salesforce_config["tools"]),
                },
            )

            logger.info(
                f"✅ Salesforce MCP configured for Lead Administrator Agent (user: {self.user_id})"
            )
            return salesforce_config

        except Exception as e:
            mcp_error = self.error_handler.handle_error(
                e, service_name="salesforce", operation="configure_salesforce_mcp"
            )
            logger.error(
                f"❌ Failed to configure Salesforce MCP: {mcp_error.get_user_friendly_message()}"
            )
            raise mcp_error

    @retry_mcp_operation(max_attempts=3, service_name="admin_zoho", log_attempts=True)
    async def configure_zoho_mcp(self) -> Dict[str, Any]:
        """Configure Zoho CRM MCP for alternative CRM"""
        try:
            zoho_tokens = await self._get_oauth_tokens("zoho")

            if not zoho_tokens:
                logger.warning(
                    f"⚠️ No Zoho OAuth tokens for user {self.user_id}, using demo mode"
                )
                return self._get_demo_zoho_config()

            mcp_credentials = get_mcp_credentials_for_service(
                zoho_tokens, "zoho", self.user_id
            )

            zoho_config = {
                "service_name": "zoho",
                "service_type": "crm",
                "credentials": mcp_credentials.to_dict(),
                "tools": [
                    {
                        "name": "create_lead",
                        "description": "Create lead in Zoho CRM",
                        "parameters": {
                            "last_name": {"type": "string"},
                            "first_name": {"type": "string", "required": False},
                            "email": {"type": "string", "required": False},
                            "company": {"type": "string", "required": False},
                            "phone": {"type": "string", "required": False},
                            "lead_status": {"type": "string", "required": False},
                        },
                        "pipedream_action": "zoho_create_lead",
                    },
                    {
                        "name": "update_lead",
                        "description": "Update lead in Zoho CRM",
                        "parameters": {
                            "lead_id": {"type": "string"},
                            "lead_status": {"type": "string", "required": False},
                            "rating": {"type": "string", "required": False},
                        },
                        "pipedream_action": "zoho_update_lead",
                    },
                    {
                        "name": "get_leads",
                        "description": "Get leads from Zoho CRM",
                        "parameters": {
                            "criteria": {"type": "string", "required": False},
                            "page": {"type": "integer", "default": 1},
                            "per_page": {"type": "integer", "default": 50},
                        },
                        "pipedream_action": "zoho_get_leads",
                    },
                ],
                "configuration": {
                    "api_version": "v2",
                    "domain": "zohoapis.com",
                    "sync_enabled": True,
                },
                "rate_limits": {
                    "api_calls_per_minute": 100,
                    "leads_per_hour": 250,
                },
            }

            self._mcp_cache["zoho"] = zoho_config

            self.analytics_logger.log_mcp_creation(
                user_id=self.user_id,
                service_name="zoho",
                oauth_provider=OAuthProvider.ZOHO,
                success=True,
                context={
                    "agent_type": "lead_administrator",
                    "tools_count": len(zoho_config["tools"]),
                },
            )

            logger.info(
                f"✅ Zoho MCP configured for Lead Administrator Agent (user: {self.user_id})"
            )
            return zoho_config

        except Exception as e:
            mcp_error = self.error_handler.handle_error(
                e, service_name="zoho", operation="configure_zoho_mcp"
            )
            logger.error(
                f"❌ Failed to configure Zoho MCP: {mcp_error.get_user_friendly_message()}"
            )
            raise mcp_error

    async def get_lead_administrator_mcp_configuration(self) -> Dict[str, Any]:
        """Get complete MCP configuration for Lead Administrator Agent"""
        try:
            pipedrive_config = await self.configure_pipedrive_mcp()
            salesforce_config = await self.configure_salesforce_mcp()
            zoho_config = await self.configure_zoho_mcp()

            administrator_config = {
                "agent_type": "lead_administrator",
                "agent_name": "PipeWise Lead Administrator",
                "description": "Handles CRM operations and lead management",
                "user_id": self.user_id,
                "mcps": {
                    "pipedrive": pipedrive_config,
                    "salesforce": salesforce_config,
                    "zoho": zoho_config,
                },
                "capabilities": [
                    "lead_management",
                    "crm_synchronization",
                    "deal_tracking",
                    "pipeline_management",
                    "lead_qualification",
                    "opportunity_management",
                ],
                "workflows": {
                    "create_lead_workflow": {
                        "steps": [
                            {"tool": "create_lead", "service": "primary_crm"},
                            {"tool": "create_person", "service": "pipedrive"},
                            {"tool": "create_deal", "service": "pipedrive"},
                        ],
                    },
                    "update_lead_status": {
                        "steps": [
                            {"tool": "update_lead", "service": "all_crms"},
                            {"tool": "update_deal", "service": "pipedrive"},
                        ],
                    },
                },
                "configuration": {
                    "crm_channels": ["pipedrive", "salesforce", "zoho"],
                    "sync_enabled": True,
                    "automation_enabled": True,
                    "analytics_tracking": True,
                },
                "created_at": datetime.now().isoformat(),
            }

            logger.info(
                f"✅ Complete Lead Administrator MCP configuration ready for user {self.user_id}"
            )
            return administrator_config

        except Exception as e:
            logger.error(
                f"❌ Failed to get complete Lead Administrator MCP configuration: {e}"
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

            provider_map = {
                "pipedrive": OAuthProvider.PIPEDRIVE,
                "salesforce": OAuthProvider.SALESFORCE,
                "zoho": OAuthProvider.ZOHO,
            }

            return OAuthTokens(
                access_token=f"admin_demo_token_{service_name}",
                provider=provider_map.get(service_name, OAuthProvider.PIPEDRIVE),
                user_id=self.user_id,
            )

        except Exception as e:
            logger.debug(f"⚪ Could not get OAuth tokens for {service_name}: {e}")
            return None

    def _get_demo_pipedrive_config(self) -> Dict[str, Any]:
        """Get demo Pipedrive configuration"""
        return {
            "service_name": "pipedrive",
            "service_type": "crm",
            "demo_mode": True,
            "credentials": {
                "service_name": "pipedrive",
                "headers": {
                    "Authorization": f"Bearer demo_pipedrive_token_{self.user_id}",
                    "Content-Type": "application/json",
                },
                "auth_type": "demo",
            },
            "tools": [
                {
                    "name": "create_deal",
                    "description": "Create new deal in Pipedrive (DEMO MODE)",
                    "demo_response": {"deal_id": "demo_deal_123", "title": "Demo Deal"},
                },
            ],
        }

    def _get_demo_salesforce_config(self) -> Dict[str, Any]:
        """Get demo Salesforce configuration"""
        return {
            "service_name": "salesforce",
            "service_type": "crm",
            "demo_mode": True,
            "credentials": {
                "service_name": "salesforce",
                "headers": {
                    "Authorization": f"Bearer demo_salesforce_token_{self.user_id}",
                    "Content-Type": "application/json",
                },
                "auth_type": "demo",
            },
            "tools": [
                {
                    "name": "create_lead",
                    "description": "Create lead in Salesforce (DEMO MODE)",
                    "demo_response": {"lead_id": "demo_lead_456", "name": "Demo Lead"},
                },
            ],
        }

    def _get_demo_zoho_config(self) -> Dict[str, Any]:
        """Get demo Zoho configuration"""
        return {
            "service_name": "zoho",
            "service_type": "crm",
            "demo_mode": True,
            "credentials": {
                "service_name": "zoho",
                "headers": {
                    "Authorization": f"Bearer demo_zoho_token_{self.user_id}",
                    "Content-Type": "application/json",
                },
                "auth_type": "demo",
            },
            "tools": [
                {
                    "name": "create_lead",
                    "description": "Create lead in Zoho CRM (DEMO MODE)",
                    "demo_response": {
                        "lead_id": "demo_lead_789",
                        "name": "Demo Zoho Lead",
                    },
                },
            ],
        }

    def clear_cache(self) -> None:
        """Clear MCP configuration cache"""
        self._mcp_cache.clear()
        logger.info("🧹 Cleared Lead Administrator MCP cache")


# Helper functions
async def get_lead_administrator_mcp_configuration(user_id: str) -> Dict[str, Any]:
    """Get MCP configuration for Lead Administrator Agent"""
    manager = LeadAdministratorAgentMCPManager(user_id)
    return await manager.get_lead_administrator_mcp_configuration()


async def configure_administrator_pipedrive(user_id: str) -> Dict[str, Any]:
    """Configure Pipedrive MCP for Lead Administrator Agent"""
    manager = LeadAdministratorAgentMCPManager(user_id)
    return await manager.configure_pipedrive_mcp()


async def configure_administrator_salesforce(user_id: str) -> Dict[str, Any]:
    """Configure Salesforce MCP for Lead Administrator Agent"""
    manager = LeadAdministratorAgentMCPManager(user_id)
    return await manager.configure_salesforce_mcp()


async def configure_administrator_zoho(user_id: str) -> Dict[str, Any]:
    """Configure Zoho CRM MCP for Lead Administrator Agent"""
    manager = LeadAdministratorAgentMCPManager(user_id)
    return await manager.configure_zoho_mcp()


def get_administrator_supported_tools() -> List[str]:
    """Get list of tools supported by Lead Administrator Agent MCPs"""
    return [
        # Pipedrive tools
        "create_deal",
        "update_deal",
        "create_person",
        "get_deals",
        # Salesforce tools
        "create_opportunity",
        "create_lead",
        "update_lead",
        "get_leads",
        # Zoho tools
        "create_lead",
        "update_lead",
        "get_leads",
    ]
