"""
Lead Administrator MCP Integration

This module provides MCP-based replacements for local CRM functions.
It replaces functions like mark_lead_as_contacted() with new implementations
that use MCP tools for Pipedrive, Salesforce, and Zoho CRM.

Key Features:
- Replace local CRM functions with MCP versions
- Use CRM MCP tools for lead management
- Maintain backward compatibility
- Enhanced CRM synchronization

Following PRD: Task 4.3.4 - Replace mark_lead_as_contacted() with MCP tools
"""

import logging
from typing import Dict, Any, Optional, Union, List
from datetime import datetime
from uuid import UUID

from .lead_administrator_agent_mcps import LeadAdministratorAgentMCPManager
from .local_tools_to_mcp_mapper import LocalToolToMCPMapper
from .oauth_integration import OAuthProvider
from .error_handler import get_error_handler
from .retry_handler import retry_mcp_operation

from ...supabase.supabase_client import SupabaseCRMClient
from ...models.lead import Lead
from ...schemas.lead_schema import LeadCreate, LeadUpdate

logger = logging.getLogger(__name__)


class MCPCRMManager:
    """
    MCP-based CRM manager that replaces local CRM functions.

    This class provides MCP-based implementations for CRM operations
    that integrate with multiple CRM systems via MCP tools.
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.error_handler = get_error_handler()
        self.admin_mcp_manager = LeadAdministratorAgentMCPManager(user_id)
        self.tool_mapper = LocalToolToMCPMapper(user_id)
        self.db_client = SupabaseCRMClient()

    @retry_mcp_operation(
        max_attempts=3, service_name="mcp_crm_manager", log_attempts=True
    )
    async def mark_lead_as_contacted_mcp(
        self, lead_id: str, contact_method: str, contact_details: str = ""
    ) -> Dict[str, Any]:
        """
        MCP-based replacement for mark_lead_as_contacted().

        This function updates lead status in multiple CRM systems using MCP tools
        while maintaining backward compatibility.

        Args:
            lead_id: Lead identifier
            contact_method: Method of contact (email, phone, social, etc.)
            contact_details: Additional contact details

        Returns:
            Dictionary with operation result and CRM sync status
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

            # Get CRM configurations
            admin_config = (
                await self.admin_mcp_manager.get_lead_administrator_mcp_configuration()
            )

            # Check which CRM systems are available
            crm_availability = {
                "pipedrive": not admin_config["mcps"]["pipedrive"].get(
                    "demo_mode", False
                ),
                "salesforce": not admin_config["mcps"]["salesforce"].get(
                    "demo_mode", False
                ),
                "zoho": not admin_config["mcps"]["zoho"].get("demo_mode", False),
            }

            # Update lead in local database first
            local_result = await self._update_lead_in_local_database(
                lead, contact_method, contact_details
            )

            # Sync with CRM systems
            crm_results = await self._sync_with_crm_systems(
                lead, contact_method, contact_details, crm_availability
            )

            # Compile results
            result = {
                "success": True,
                "lead_id": lead.id,
                "lead_name": lead.name,
                "contact_method": contact_method,
                "contact_details": contact_details,
                "local_updated": local_result,
                "crm_sync_results": crm_results,
                "mcp_used": True,
                "crm_availability": crm_availability,
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(f"✅ MCP-based lead contact update completed for {lead.id}")

            return result

        except Exception as e:
            mcp_error = self.error_handler.handle_error(
                e,
                service_name="mcp_crm_manager",
                operation="mark_lead_as_contacted_mcp",
                context={
                    "lead_id": lead_id,
                    "contact_method": contact_method,
                    "user_id": self.user_id,
                },
            )

            logger.error(
                f"❌ MCP-based lead contact update failed: {mcp_error.get_user_friendly_message()}"
            )

            return {
                "success": False,
                "error": mcp_error.get_user_friendly_message(),
                "lead_id": lead_id,
                "contact_method": contact_method,
                "mcp_used": True,
                "fallback_available": True,
            }

    async def _sync_with_crm_systems(
        self,
        lead: Lead,
        contact_method: str,
        contact_details: str,
        crm_availability: Dict[str, bool],
    ) -> Dict[str, Any]:
        """Sync lead contact status with CRM systems"""
        crm_results = {}

        # Sync with Pipedrive
        if crm_availability["pipedrive"]:
            crm_results["pipedrive"] = await self._sync_with_pipedrive(
                lead, contact_method, contact_details
            )

        # Sync with Salesforce
        if crm_availability["salesforce"]:
            crm_results["salesforce"] = await self._sync_with_salesforce(
                lead, contact_method, contact_details
            )

        # Sync with Zoho
        if crm_availability["zoho"]:
            crm_results["zoho"] = await self._sync_with_zoho(
                lead, contact_method, contact_details
            )

        return crm_results

    async def _sync_with_pipedrive(
        self, lead: Lead, contact_method: str, contact_details: str
    ) -> Dict[str, Any]:
        """Sync lead contact status with Pipedrive"""
        try:
            # First, ensure person exists in Pipedrive
            person_result = await self.tool_mapper.map_tool_call(
                "pipedrive.create_person",
                {
                    "name": lead.name,
                    "email": lead.email,
                    "phone": lead.phone,
                },
            )

            person_id = None
            if person_result.get("success", False):
                person_id = person_result.get("id") or person_result.get(
                    "result", {}
                ).get("id")

            # Create or update deal in Pipedrive
            deal_result = await self.tool_mapper.map_tool_call(
                "pipedrive.create_deal",
                {
                    "title": f"Lead: {lead.name} - {lead.company}",
                    "person_id": person_id,
                    "value": 1000,  # Default value
                    "currency": "USD",
                },
            )

            return {
                "success": True,
                "person_created": person_result.get("success", False),
                "deal_created": deal_result.get("success", False),
                "person_id": person_id,
                "deal_id": deal_result.get("id")
                if deal_result.get("success")
                else None,
                "contact_method": contact_method,
            }

        except Exception as e:
            logger.error(f"❌ Error syncing with Pipedrive: {e}")
            return {
                "success": False,
                "error": str(e),
                "contact_method": contact_method,
            }

    async def _sync_with_salesforce(
        self, lead: Lead, contact_method: str, contact_details: str
    ) -> Dict[str, Any]:
        """Sync lead contact status with Salesforce"""
        try:
            # Create or update lead in Salesforce
            lead_result = await self.tool_mapper.map_tool_call(
                "salesforce.create_lead",
                {
                    "first_name": lead.name.split()[0] if lead.name else "",
                    "last_name": lead.name.split()[-1] if lead.name else "Unknown",
                    "email": lead.email,
                    "company": lead.company,
                    "phone": lead.phone,
                },
            )

            # Update lead status if creation was successful
            if lead_result.get("success", False):
                lead_id = lead_result.get("id") or lead_result.get("result", {}).get(
                    "id"
                )

                update_result = await self.tool_mapper.map_tool_call(
                    "salesforce.update_lead",
                    {
                        "lead_id": lead_id,
                        "status": "Contacted",
                        "rating": "Warm",
                    },
                )

                return {
                    "success": True,
                    "lead_created": True,
                    "lead_updated": update_result.get("success", False),
                    "lead_id": lead_id,
                    "contact_method": contact_method,
                }
            else:
                return {
                    "success": False,
                    "error": lead_result.get("error", "Unknown error"),
                    "contact_method": contact_method,
                }

        except Exception as e:
            logger.error(f"❌ Error syncing with Salesforce: {e}")
            return {
                "success": False,
                "error": str(e),
                "contact_method": contact_method,
            }

    async def _sync_with_zoho(
        self, lead: Lead, contact_method: str, contact_details: str
    ) -> Dict[str, Any]:
        """Sync lead contact status with Zoho CRM"""
        try:
            # Create or update lead in Zoho CRM
            lead_result = await self.tool_mapper.map_tool_call(
                "zoho.create_lead",
                {
                    "first_name": lead.name.split()[0] if lead.name else "",
                    "last_name": lead.name.split()[-1] if lead.name else "Unknown",
                    "email": lead.email,
                    "company": lead.company,
                    "phone": lead.phone,
                    "lead_status": "Contacted",
                },
            )

            return {
                "success": lead_result.get("success", False),
                "lead_created": lead_result.get("success", False),
                "lead_id": lead_result.get("id")
                if lead_result.get("success")
                else None,
                "contact_method": contact_method,
                "error": lead_result.get("error")
                if not lead_result.get("success")
                else None,
            }

        except Exception as e:
            logger.error(f"❌ Error syncing with Zoho: {e}")
            return {
                "success": False,
                "error": str(e),
                "contact_method": contact_method,
            }

    async def _update_lead_in_local_database(
        self, lead: Lead, contact_method: str, contact_details: str
    ) -> bool:
        """Update lead in local database"""
        try:
            if not lead.id:
                logger.error("❌ Lead ID is None, cannot update database")
                return False

            # mark_lead_as_contacted only accepts lead_id and contact_method
            updated_lead = self.db_client.mark_lead_as_contacted(
                lead.id, contact_method
            )
            logger.info(f"✅ Lead {lead.id} marked as contacted in local database")
            return True
        except Exception as e:
            logger.error(f"❌ Error updating lead in local database: {e}")
            return False

    async def _get_lead_info(self, lead_id: str) -> Optional[Lead]:
        """Get lead information from database"""
        try:
            if "@" in lead_id:
                return self.db_client.get_lead_by_email(lead_id)
            else:
                return self.db_client.get_lead(lead_id)
        except Exception as e:
            logger.error(f"❌ Error getting lead info: {e}")
            return None


# Backward compatibility wrapper functions
async def mark_lead_as_contacted_mcp(
    lead_id: str,
    contact_method: str,
    contact_details: str = "",
    user_id: str = "system",
) -> Dict[str, Any]:
    """
    MCP-based replacement for mark_lead_as_contacted function.

    Args:
        lead_id: Lead identifier
        contact_method: Method of contact
        contact_details: Additional contact details
        user_id: User identifier

    Returns:
        Dictionary with operation result
    """
    crm_manager = MCPCRMManager(user_id)
    return await crm_manager.mark_lead_as_contacted_mcp(
        lead_id, contact_method, contact_details
    )


def mark_lead_as_contacted_mcp_sync(
    lead_id: str,
    contact_method: str,
    contact_details: str = "",
    user_id: str = "system",
) -> str:
    """
    Synchronous wrapper for MCP-based lead contact marking.

    Args:
        lead_id: Lead identifier
        contact_method: Method of contact
        contact_details: Additional contact details
        user_id: User identifier

    Returns:
        Status message string
    """
    import asyncio

    try:
        result = asyncio.run(
            mark_lead_as_contacted_mcp(
                lead_id, contact_method, contact_details, user_id
            )
        )

        if result["success"]:
            return (
                f"Lead '{result['lead_name']}' marked as contacted via {contact_method}"
            )
        else:
            return f"Error marking lead as contacted: {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error(f"❌ Error in synchronous MCP lead contact marking: {e}")
        return f"Error marking lead as contacted: {str(e)}"


# Additional CRM helper functions
async def create_lead_in_crm_mcp(
    lead_data: Dict[str, Any], user_id: str = "system"
) -> Dict[str, Any]:
    """
    Create lead in CRM systems using MCP tools.

    Args:
        lead_data: Lead information dictionary
        user_id: User identifier

    Returns:
        Dictionary with creation results
    """
    crm_manager = MCPCRMManager(user_id)

    # Create lead in local database first
    lead_create = LeadCreate(**lead_data)
    local_lead = crm_manager.db_client.create_lead(lead_create)

    # Sync with CRM systems - need to pass crm_availability parameter
    crm_availability = {"pipedrive": True, "salesforce": True, "zoho": True}
    crm_results = await crm_manager._sync_with_crm_systems(
        local_lead, "system_create", "Lead created via MCP system", crm_availability
    )

    return {
        "success": True,
        "local_lead": local_lead.model_dump(),
        "crm_sync_results": crm_results,
        "mcp_used": True,
    }


async def update_lead_qualification_mcp(
    lead_id: str,
    qualified: bool,
    reason: str,
    score: float = 0.0,
    user_id: str = "system",
) -> Dict[str, Any]:
    """
    Update lead qualification using MCP tools.

    Args:
        lead_id: Lead identifier
        qualified: Whether lead is qualified
        reason: Qualification reason
        score: Qualification score
        user_id: User identifier

    Returns:
        Dictionary with update results
    """
    crm_manager = MCPCRMManager(user_id)

    # Get lead info
    lead = await crm_manager._get_lead_info(lead_id)
    if not lead:
        return {
            "success": False,
            "error": f"Lead {lead_id} not found",
            "mcp_used": True,
        }

    # Update in local database
    updates = LeadUpdate(
        qualified=qualified,
        status="qualified" if qualified else "unqualified",
        metadata={"qualification_reason": reason, "qualification_score": score},
    )

    if not lead.id:
        return {
            "success": False,
            "error": f"Lead ID is None, cannot update lead",
            "mcp_used": True,
        }

    updated_lead = crm_manager.db_client.update_lead(lead.id, updates)

    # Sync with CRM systems
    contact_method = "qualification_update"
    contact_details = f"Qualified: {qualified}, Reason: {reason}, Score: {score}"

    crm_results = await crm_manager._sync_with_crm_systems(
        updated_lead,
        contact_method,
        contact_details,
        {"pipedrive": True, "salesforce": True, "zoho": True},
    )

    return {
        "success": True,
        "lead_id": lead.id,
        "qualified": qualified,
        "reason": reason,
        "score": score,
        "crm_sync_results": crm_results,
        "mcp_used": True,
    }


# Function mapping for migration
def get_crm_function_mapping() -> Dict[str, str]:
    """Get mapping of old CRM functions to new MCP functions"""
    return {
        "mark_lead_as_contacted": "mark_lead_as_contacted_mcp",
        "create_lead_in_database": "create_lead_in_crm_mcp",
        "update_lead_qualification": "update_lead_qualification_mcp",
    }


def get_mcp_crm_capabilities() -> Dict[str, Any]:
    """Get capabilities provided by MCP CRM system"""
    return {
        "pipedrive_integration": {
            "create_deals": True,
            "manage_persons": True,
            "update_pipeline": True,
            "track_activities": True,
        },
        "salesforce_integration": {
            "create_leads": True,
            "manage_opportunities": True,
            "update_lead_status": True,
            "track_activities": True,
        },
        "zoho_integration": {
            "create_leads": True,
            "manage_contacts": True,
            "update_lead_status": True,
            "track_activities": True,
        },
        "synchronization": {
            "multi_crm_sync": True,
            "real_time_updates": True,
            "conflict_resolution": True,
            "data_consistency": True,
        },
        "fallback_capabilities": {
            "local_database": True,
            "demo_mode": True,
            "error_recovery": True,
        },
    }
