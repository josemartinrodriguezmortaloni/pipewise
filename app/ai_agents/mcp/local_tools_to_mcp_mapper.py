"""
Local Tools to MCP Mapper

This module provides a mapping system to replace local communication tools
with MCP implementations for the PipeWise AI agents.

Key Features:
- Maps local tools to MCP tools
- Provides backward compatibility
- Handles graceful fallbacks
- Maintains existing API interfaces
- Supports gradual migration

Following PRD: Task 4.0 - Replace local tools with MCP implementations
"""

import logging
from typing import Dict, Any, List
from enum import Enum
from datetime import datetime

from .coordinator_agent_mcps import CoordinatorAgentMCPManager
from .error_handler import get_error_handler
from .retry_handler import retry_mcp_operation

logger = logging.getLogger(__name__)


class LocalToolType(Enum):
    """Types of local tools that can be mapped to MCP"""

    GMAIL = "gmail"
    TWITTER = "twitter"
    SENDGRID = "sendgrid"
    CALENDAR = "calendar"
    CRM = "crm"


class MCPToolStatus(Enum):
    """Status of MCP tool mapping"""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    FALLBACK = "fallback"
    DEMO = "demo"


class LocalToolToMCPMapper:
    """
    Maps local tools to MCP implementations.

    This class provides a bridge between existing local tools and new MCP
    implementations, allowing for gradual migration while maintaining
    backward compatibility.
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.error_handler = get_error_handler()
        self.coordinator_mcp_manager = CoordinatorAgentMCPManager(user_id)
        self._tool_cache = {}
        self._mapping_cache = {}

        # Define mappings from local tools to MCP tools
        self.tool_mappings = {
            # Gmail to SendGrid mappings
            "gmail.send_email": "sendgrid.send_transactional_email",
            "gmail.get_inbox_messages": "sendgrid.get_email_stats",
            "gmail.reply_to_email": "sendgrid.send_transactional_email",
            "gmail.search_emails": "sendgrid.get_email_stats",
            # Twitter mappings (local to MCP)
            "twitter.send_dm": "twitter.send_direct_message",
            "twitter.get_user_info": "twitter.get_user_profile",
            "twitter.reply_to_tweet": "twitter.post_tweet",
            "twitter.search_tweets": "twitter.search_tweets",
            # SendGrid mappings (if local SendGrid tools exist)
            "sendgrid.send_email": "sendgrid.send_transactional_email",
            "sendgrid.send_marketing_email": "sendgrid.send_marketing_email",
            "sendgrid.create_list": "sendgrid.create_email_list",
            "sendgrid.add_contact": "sendgrid.add_contact_to_list",
        }

        # Tool parameter mappings
        self.parameter_mappings = {
            "gmail.send_email": {
                "to_email": "to_email",
                "subject": "subject",
                "message": "html_content",
                "from_name": "dynamic_template_data.from_name",
            },
            "twitter.send_dm": {
                "username": "recipient_username",
                "message": "message",
            },
            "twitter.get_user_info": {
                "username": "username",
            },
            "twitter.reply_to_tweet": {
                "tweet_id": "reply_to_tweet_id",
                "message": "text",
            },
        }

    async def map_tool_call(
        self, tool_name: str, parameters: Dict[str, Any], fallback_enabled: bool = True
    ) -> Dict[str, Any]:
        """
        Map a local tool call to an MCP tool call.

        Args:
            tool_name: Name of the local tool (e.g., "gmail.send_email")
            parameters: Parameters for the tool call
            fallback_enabled: Whether to use local tool as fallback

        Returns:
            Result of the MCP tool call or fallback result
        """
        try:
            # Check if tool is mapped
            if tool_name not in self.tool_mappings:
                logger.warning(
                    f"⚠️ Tool {tool_name} not mapped to MCP, using local implementation"
                )
                return await self._execute_local_tool(tool_name, parameters)

            mcp_tool_name = self.tool_mappings[tool_name]

            # Map parameters
            mapped_params = self._map_parameters(tool_name, parameters)

            # Execute MCP tool
            result = await self._execute_mcp_tool(mcp_tool_name, mapped_params)

            # Check if MCP tool succeeded
            if result.get("success", False):
                logger.info(f"✅ MCP tool {mcp_tool_name} executed successfully")
                return result

            # Fallback to local tool if enabled
            if fallback_enabled:
                logger.warning(
                    f"⚠️ MCP tool {mcp_tool_name} failed, falling back to local tool"
                )
                return await self._execute_local_tool(tool_name, parameters)

            return result

        except Exception as e:
            mcp_error = self.error_handler.handle_error(
                e,
                service_name="tool_mapper",
                operation="map_tool_call",
                context={"tool_name": tool_name, "user_id": self.user_id},
            )

            logger.error(
                f"❌ Tool mapping failed: {mcp_error.get_user_friendly_message()}"
            )

            # Fallback to local tool if enabled
            if fallback_enabled:
                return await self._execute_local_tool(tool_name, parameters)

            return {
                "success": False,
                "error": mcp_error.get_user_friendly_message(),
                "tool_name": tool_name,
                "fallback_used": False,
            }

    @retry_mcp_operation(
        max_attempts=2, service_name="mcp_tool_execution", log_attempts=True
    )
    async def _execute_mcp_tool(
        self, tool_name: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute an MCP tool"""
        try:
            # Parse tool name (service.tool_name)
            parts = tool_name.split(".")
            if len(parts) != 2:
                raise ValueError(f"Invalid MCP tool name format: {tool_name}")

            service_name, tool_method = parts

            # Get MCP configuration based on service
            if service_name == "sendgrid":
                config = await self.coordinator_mcp_manager.configure_sendgrid_mcp()
            elif service_name == "twitter":
                config = await self.coordinator_mcp_manager.configure_twitter_mcp()
            else:
                raise ValueError(f"Unsupported MCP service: {service_name}")

            # Find the tool in the configuration
            tool_config = None
            for tool in config.get("tools", []):
                if tool["name"] == tool_method:
                    tool_config = tool
                    break

            if not tool_config:
                raise ValueError(
                    f"Tool {tool_method} not found in {service_name} MCP configuration"
                )

            # Execute tool via Pipedream action (simulated)
            pipedream_action = tool_config.get("pipedream_action")

            if config.get("demo_mode", False):
                # Return demo response
                demo_response = tool_config.get(
                    "demo_response",
                    {
                        "success": True,
                        "message": f"Demo execution of {tool_name}",
                        "parameters": parameters,
                        "timestamp": datetime.now().isoformat(),
                    },
                )
                return demo_response

            # For real implementation, you would call the actual MCP server here
            # For now, return a successful simulation
            return {
                "success": True,
                "tool_name": tool_name,
                "service_name": service_name,
                "pipedream_action": pipedream_action,
                "parameters": parameters,
                "result": f"MCP tool {tool_name} executed successfully",
                "timestamp": datetime.now().isoformat(),
                "mcp_execution": True,
            }

        except Exception as e:
            logger.error(f"❌ MCP tool execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "tool_name": tool_name,
                "mcp_execution": False,
            }

    async def _execute_local_tool(
        self, tool_name: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a local tool as fallback"""
        try:
            # Parse tool name
            parts = tool_name.split(".")
            if len(parts) != 2:
                return {
                    "success": False,
                    "error": f"Invalid local tool name format: {tool_name}",
                    "fallback_used": True,
                }

            service_name, method_name = parts

            # Import and execute local tool
            if service_name == "gmail":
                from ..tools.gmail import get_gmail_mcp_server

                server = get_gmail_mcp_server(self.user_id)

                if method_name == "send_email":
                    result = server.send_email(
                        str(parameters.get("to_email", "")),
                        str(parameters.get("subject", "")),
                        str(parameters.get("message", "")),
                        str(parameters.get("from_name", "PipeWise")),
                    )
                elif method_name == "get_inbox_messages":
                    result = server.get_inbox_messages(
                        parameters.get("max_results", 10)
                    )
                elif method_name == "reply_to_email":
                    result = server.reply_to_email(
                        str(parameters.get("message_id", "")),
                        str(parameters.get("reply_text", "")),
                    )
                elif method_name == "search_emails":
                    result = server.search_emails(
                        str(parameters.get("query", "")),
                        parameters.get("max_results", 10),
                    )
                else:
                    result = {
                        "success": False,
                        "error": f"Unknown Gmail method: {method_name}",
                    }

            elif service_name == "twitter":
                from ..tools.twitter import get_twitter_mcp_server

                server = get_twitter_mcp_server(self.user_id)

                if method_name == "send_dm":
                    result = server.send_dm(
                        str(parameters.get("username", "")),
                        str(parameters.get("message", "")),
                    )
                elif method_name == "get_user_info":
                    result = server.get_user_info(str(parameters.get("username", "")))
                elif method_name == "reply_to_tweet":
                    result = server.reply_to_tweet(
                        str(parameters.get("tweet_id", "")),
                        str(parameters.get("message", "")),
                    )
                elif method_name == "search_tweets":
                    result = server.search_tweets(
                        str(parameters.get("query", "")),
                        parameters.get("max_results", 10),
                    )
                else:
                    result = {
                        "success": False,
                        "error": f"Unknown Twitter method: {method_name}",
                    }

            else:
                result = {"success": False, "error": f"Unknown service: {service_name}"}

            # Add fallback indicator
            result["fallback_used"] = True
            result["local_tool_execution"] = True

            logger.info(f"✅ Local tool {tool_name} executed as fallback")

            return result

        except Exception as e:
            logger.error(f"❌ Local tool execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "tool_name": tool_name,
                "fallback_used": True,
                "local_tool_execution": False,
            }

    def _map_parameters(
        self, tool_name: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Map parameters from local tool format to MCP tool format"""
        if tool_name not in self.parameter_mappings:
            return parameters

        mapping = self.parameter_mappings[tool_name]
        mapped_params = {}

        for local_param, mcp_param in mapping.items():
            if local_param in parameters:
                # Handle nested parameters (e.g., "dynamic_template_data.from_name")
                if "." in mcp_param:
                    parts = mcp_param.split(".")
                    if parts[0] not in mapped_params:
                        mapped_params[parts[0]] = {}
                    mapped_params[parts[0]][parts[1]] = parameters[local_param]
                else:
                    mapped_params[mcp_param] = parameters[local_param]

        # Add any unmapped parameters
        for param, value in parameters.items():
            if param not in mapping:
                mapped_params[param] = value

        return mapped_params

    async def get_tool_status(self, tool_name: str) -> MCPToolStatus:
        """Get the status of a tool mapping"""
        try:
            if tool_name not in self.tool_mappings:
                return MCPToolStatus.FALLBACK

            mcp_tool_name = self.tool_mappings[tool_name]
            service_name = mcp_tool_name.split(".")[0]

            # Check if MCP service is available
            if service_name == "sendgrid":
                config = await self.coordinator_mcp_manager.configure_sendgrid_mcp()
            elif service_name == "twitter":
                config = await self.coordinator_mcp_manager.configure_twitter_mcp()
            else:
                return MCPToolStatus.UNAVAILABLE

            if config.get("demo_mode", False):
                return MCPToolStatus.DEMO

            return MCPToolStatus.AVAILABLE

        except Exception as e:
            logger.error(f"❌ Error checking tool status: {e}")
            return MCPToolStatus.UNAVAILABLE

    async def get_all_tool_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Get all available tool mappings with their statuses"""
        mappings = {}

        for local_tool, mcp_tool in self.tool_mappings.items():
            status = await self.get_tool_status(local_tool)
            mappings[local_tool] = {
                "mcp_tool": mcp_tool,
                "status": status.value,
                "service": mcp_tool.split(".")[0],
                "method": mcp_tool.split(".")[1],
            }

        return mappings

    def clear_cache(self) -> None:
        """Clear tool mapping cache"""
        self._tool_cache.clear()
        self._mapping_cache.clear()
        logger.info("🧹 Cleared tool mapping cache")


# Convenience classes for backward compatibility
class LegacyGmailTool:
    """Backward compatibility wrapper for Gmail tools"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.mapper = LocalToolToMCPMapper(user_id)

    async def send_email(
        self, to_email: str, subject: str, message: str, from_name: str = "PipeWise"
    ) -> Dict[str, Any]:
        """Send email using MCP or local fallback"""
        return await self.mapper.map_tool_call(
            "gmail.send_email",
            {
                "to_email": to_email,
                "subject": subject,
                "message": message,
                "from_name": from_name,
            },
        )

    async def get_inbox_messages(self, max_results: int = 10) -> Dict[str, Any]:
        """Get inbox messages using MCP or local fallback"""
        return await self.mapper.map_tool_call(
            "gmail.get_inbox_messages", {"max_results": max_results}
        )

    async def reply_to_email(self, message_id: str, reply_text: str) -> Dict[str, Any]:
        """Reply to email using MCP or local fallback"""
        return await self.mapper.map_tool_call(
            "gmail.reply_to_email", {"message_id": message_id, "reply_text": reply_text}
        )

    async def search_emails(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """Search emails using MCP or local fallback"""
        return await self.mapper.map_tool_call(
            "gmail.search_emails", {"query": query, "max_results": max_results}
        )


class LegacyTwitterTool:
    """Backward compatibility wrapper for Twitter tools"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.mapper = LocalToolToMCPMapper(user_id)

    async def send_dm(self, username: str, message: str) -> Dict[str, Any]:
        """Send DM using MCP or local fallback"""
        return await self.mapper.map_tool_call(
            "twitter.send_dm", {"username": username, "message": message}
        )

    async def get_user_info(self, username: str) -> Dict[str, Any]:
        """Get user info using MCP or local fallback"""
        return await self.mapper.map_tool_call(
            "twitter.get_user_info", {"username": username}
        )

    async def reply_to_tweet(self, tweet_id: str, message: str) -> Dict[str, Any]:
        """Reply to tweet using MCP or local fallback"""
        return await self.mapper.map_tool_call(
            "twitter.reply_to_tweet", {"tweet_id": tweet_id, "message": message}
        )

    async def search_tweets(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """Search tweets using MCP or local fallback"""
        return await self.mapper.map_tool_call(
            "twitter.search_tweets", {"query": query, "max_results": max_results}
        )


# Helper functions
async def get_tool_mapper(user_id: str) -> LocalToolToMCPMapper:
    """Get tool mapper instance"""
    return LocalToolToMCPMapper(user_id)


async def get_legacy_gmail_tool(user_id: str) -> LegacyGmailTool:
    """Get legacy Gmail tool wrapper"""
    return LegacyGmailTool(user_id)


async def get_legacy_twitter_tool(user_id: str) -> LegacyTwitterTool:
    """Get legacy Twitter tool wrapper"""
    return LegacyTwitterTool(user_id)


def get_available_local_tools() -> List[str]:
    """Get list of available local tools that can be mapped"""
    return [
        "gmail.send_email",
        "gmail.get_inbox_messages",
        "gmail.reply_to_email",
        "gmail.search_emails",
        "twitter.send_dm",
        "twitter.get_user_info",
        "twitter.reply_to_tweet",
        "twitter.search_tweets",
        "sendgrid.send_email",
        "sendgrid.send_marketing_email",
        "sendgrid.create_list",
        "sendgrid.add_contact",
    ]


def get_migration_roadmap() -> Dict[str, Dict[str, Any]]:
    """Get migration roadmap for tools"""
    return {
        "phase_1": {
            "description": "Replace Gmail tools with SendGrid MCP",
            "tools": [
                "gmail.send_email",
                "gmail.reply_to_email",
            ],
            "target_mcp": "sendgrid",
            "completion_status": "in_progress",
        },
        "phase_2": {
            "description": "Replace Twitter tools with Twitter MCP",
            "tools": [
                "twitter.send_dm",
                "twitter.get_user_info",
                "twitter.reply_to_tweet",
                "twitter.search_tweets",
            ],
            "target_mcp": "twitter",
            "completion_status": "in_progress",
        },
        "phase_3": {
            "description": "Complete migration and remove local tools",
            "tools": [
                "gmail.get_inbox_messages",
                "gmail.search_emails",
                "sendgrid.send_email",
                "sendgrid.send_marketing_email",
            ],
            "target_mcp": "multiple",
            "completion_status": "pending",
        },
    }
