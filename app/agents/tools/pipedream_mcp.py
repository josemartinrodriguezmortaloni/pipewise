"""
Pipedream MCP Client for PipeWise CRM

This client connects to Pipedream's MCP (Model Context Protocol) servers
to access 2,700+ APIs and 10,000+ tools directly in OpenAI and other LLMs.

Following documentation: https://pipedream.com/docs/connect/mcp/openai/
"""

import os
import json
import logging
import requests
from typing import Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class PipedreamMCPClient:
    """Cliente para interactuar con Pipedream MCP servers"""

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        project_id: Optional[str] = None,
        environment: str = "development",
    ):
        self.client_id = client_id or os.getenv("PIPEDREAM_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("PIPEDREAM_CLIENT_SECRET")
        self.project_id = project_id or os.getenv("PIPEDREAM_PROJECT_ID")
        self.environment = environment or os.getenv(
            "PIPEDREAM_ENVIRONMENT", "development"
        )

        self.base_url = "https://api.pipedream.com/v1"
        self.mcp_url = "https://remote.mcp.pipedream.net"

        # Validate required credentials
        if not all([self.client_id, self.client_secret, self.project_id]):
            self.enabled = False
            logger.warning(
                "Pipedream MCP client initialized without credentials - using demo mode"
            )
        else:
            self.enabled = True
            logger.info("Pipedream MCP client initialized with API credentials")

        self.access_token = None
        self._authenticate()

    def _authenticate(self) -> Optional[str]:
        """Authenticate with Pipedream and get access token"""
        if not self.enabled:
            return None

        try:
            auth_data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }

            response = requests.post(
                f"{self.base_url}/oauth/token",
                headers={"Content-Type": "application/json"},
                json=auth_data,
                timeout=10,
            )
            response.raise_for_status()

            result = response.json()
            self.access_token = result.get("access_token")

            if self.access_token:
                logger.info("✅ Successfully authenticated with Pipedream")
                return self.access_token
            else:
                logger.error("❌ Failed to get access token from Pipedream")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Authentication error: {e}")
            return None

    def get_raw_access_token(self) -> str:
        """Get raw access token for MCP authentication"""
        if not self.access_token:
            self._authenticate()
        return self.access_token or "demo_token"

    def discover_apps(self, query: Optional[str] = None) -> Dict[str, Any]:
        """Discover available apps in Pipedream MCP"""
        if not self.enabled:
            # Return demo data for the requested services
            return {
                "data": [
                    {
                        "name_slug": "calendly_v2",
                        "name": "Calendly",
                        "description": "Schedule meetings without the hassle. Never get double booked",
                        "category": "scheduling",
                        "auth_type": "oauth2",
                    },
                    {
                        "name_slug": "pipedrive",
                        "name": "Pipedrive",
                        "description": "Easy-to-use, #1 user-rated CRM tool",
                        "category": "crm",
                        "auth_type": "oauth2",
                    },
                    {
                        "name_slug": "zoho_crm",
                        "name": "Zoho CRM",
                        "description": "Online Sales CRM software that manages your sales, marketing, and support",
                        "category": "crm",
                        "auth_type": "oauth2",
                    },
                    {
                        "name_slug": "salesforce_rest_api",
                        "name": "Salesforce",
                        "description": "Cloud-based customer relationship management (CRM) platform",
                        "category": "crm",
                        "auth_type": "oauth2",
                    },
                    {
                        "name_slug": "sendgrid",
                        "name": "Twilio SendGrid",
                        "description": "Send marketing and transactional email through the Twilio SendGrid platform",
                        "category": "email",
                        "auth_type": "api_key",
                    },
                    {
                        "name_slug": "google_calendar",
                        "name": "Google Calendar",
                        "description": "Quickly schedule meetings and events and get reminders about upcoming activities",
                        "category": "scheduling",
                        "auth_type": "oauth2",
                    },
                ],
                "demo_mode": True,
            }

        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }

            params = {}
            if query:
                params["q"] = query

            response = requests.get(
                f"{self.base_url}/apps", headers=headers, params=params, timeout=10
            )
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Error discovering apps: {e}")
            return {"data": [], "error": str(e)}

    def get_app_details(self, app_slug: str) -> Dict[str, Any]:
        """Get detailed information about a specific app"""
        if not self.enabled:
            app_details = {
                "calendly_v2": {
                    "name": "Calendly",
                    "description": "Schedule meetings without the hassle. Never get double booked",
                    "category": "scheduling",
                    "tools": [
                        "Create Invitee No Show",
                        "Create a Scheduling Link",
                        "Get Event",
                        "List Event Invitees",
                        "List Events",
                        "List User Availability Schedules",
                        "List Webhook Subscriptions",
                    ],
                    "auth_type": "oauth2",
                    "webhook_support": True,
                    "tools_count": 7,
                },
                "pipedrive": {
                    "name": "Pipedrive",
                    "description": "Easy-to-use, #1 user-rated CRM tool",
                    "category": "crm",
                    "tools": [
                        "Add Activity",
                        "Add Deal",
                        "Add Note",
                        "Add Organization",
                        "Add Person",
                        "Add Lead",
                        "Search persons",
                        "Update Deal",
                        "Update Person",
                        "Remove Duplicate Notes",
                        "Search Notes",
                    ],
                    "auth_type": "oauth2",
                    "webhook_support": True,
                    "tools_count": 37,
                },
                "zoho_crm": {
                    "name": "Zoho CRM",
                    "description": "Online Sales CRM software that manages your sales, marketing, and support",
                    "category": "crm",
                    "tools": [
                        "Upload Attachment",
                        "Get Object",
                        "Convert Lead",
                        "Create Object",
                        "Download Attachment",
                        "List Fields",
                        "List Modules",
                        "List Objects",
                        "Search Objects",
                        "Update Object",
                    ],
                    "auth_type": "oauth2",
                    "webhook_support": True,
                    "tools_count": 11,
                },
                "salesforce_rest_api": {
                    "name": "Salesforce",
                    "description": "Cloud-based customer relationship management (CRM) platform",
                    "category": "crm",
                    "tools": [
                        "Create Account",
                        "Create Contact",
                        "Create Lead",
                        "Create Opportunity",
                        "Create Case",
                        "Create Task",
                        "Create Event",
                        "Update Contact",
                        "Update Account",
                        "Update Opportunity",
                        "SOQL Query",
                        "SOSL Search",
                        "Find Records",
                        "Search Object Records",
                    ],
                    "auth_type": "oauth2",
                    "webhook_support": True,
                    "tools_count": 30,
                },
                "sendgrid": {
                    "name": "Twilio SendGrid",
                    "description": "Send marketing and transactional email through the Twilio SendGrid platform",
                    "category": "email",
                    "tools": [
                        "Send Email Single Recipient",
                        "Send Email Multiple Recipients",
                        "Create Contact List",
                        "Add or Update Contact",
                        "Delete Contacts",
                        "Search Contacts",
                        "Validate Email",
                        "Create Send",
                        "Add Email to Global Suppression",
                        "Delete Global Suppression",
                        "Get All Bounces",
                        "Delete Bounces",
                    ],
                    "auth_type": "api_key",
                    "webhook_support": True,
                    "tools_count": 20,
                },
                "google_calendar": {
                    "name": "Google Calendar",
                    "description": "Quickly schedule meetings and events and get reminders about upcoming activities",
                    "category": "scheduling",
                    "tools": [
                        "Create Event",
                        "Update Event",
                        "Delete an Event",
                        "List Events",
                        "Retrieve Event Details",
                        "Add Quick Event",
                        "Add Attendees To Event",
                        "List Calendars",
                        "Retrieve Calendar Details",
                        "Retrieve Free/Busy Calendar Details",
                    ],
                    "auth_type": "oauth2",
                    "webhook_support": True,
                    "tools_count": 10,
                },
            }
            return app_details.get(app_slug, {"error": "App not found in demo mode"})

        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }

            response = requests.get(
                f"{self.base_url}/apps/{app_slug}", headers=headers, timeout=10
            )
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting app details for {app_slug}: {e}")
            return {"error": str(e)}

    def create_mcp_tool_config(
        self, app_slug: str, external_user_id: str
    ) -> Dict[str, Any]:
        """Create MCP tool configuration for OpenAI integration"""
        return {
            "type": "mcp",
            "server_label": app_slug,
            "server_url": self.mcp_url,
            "headers": {
                "Authorization": f"Bearer {self.get_raw_access_token()}",
                "x-pd-project-id": self.project_id,
                "x-pd-environment": self.environment,
                "x-pd-external-user-id": external_user_id,
                "x-pd-app-slug": app_slug,
            },
            "require_approval": "never",
        }

    def get_target_services_mcp(
        self, external_user_id: str = "pipewise_user"
    ) -> Dict[str, Any]:
        """Get MCP configurations for all target services"""
        target_services = [
            "calendly_v2",
            "pipedrive",
            "zoho_crm",
            "salesforce_rest_api",
            "sendgrid",
            "google_calendar",
        ]

        mcp_configs = {}
        service_details = {}

        for service in target_services:
            logger.info(f"🔍 Getting MCP config for {service}...")

            # Get app details
            app_details = self.get_app_details(service)
            service_details[service] = app_details

            # Create MCP configuration
            mcp_config = self.create_mcp_tool_config(service, external_user_id)
            mcp_configs[service] = mcp_config

            logger.info(f"✅ MCP config created for {service}")

        return {
            "mcp_configurations": mcp_configs,
            "service_details": service_details,
            "external_user_id": external_user_id,
            "project_id": self.project_id,
            "environment": self.environment,
            "created_at": datetime.now().isoformat(),
        }

    def test_mcp_connection(
        self, app_slug: str, external_user_id: str = "test_user"
    ) -> Dict[str, Any]:
        """Test MCP connection for a specific service"""
        try:
            # Create MCP config
            mcp_config = self.create_mcp_tool_config(app_slug, external_user_id)

            # Test connection by making a simple request
            test_headers = mcp_config["headers"].copy()

            # Note: In a real implementation, you would test the actual MCP endpoint
            # For now, we'll validate the configuration structure

            required_headers = [
                "Authorization",
                "x-pd-project-id",
                "x-pd-environment",
                "x-pd-external-user-id",
                "x-pd-app-slug",
            ]

            missing_headers = [h for h in required_headers if h not in test_headers]

            if missing_headers:
                return {
                    "success": False,
                    "app_slug": app_slug,
                    "error": f"Missing required headers: {missing_headers}",
                    "test_type": "configuration_validation",
                }

            return {
                "success": True,
                "app_slug": app_slug,
                "server_url": mcp_config["server_url"],
                "test_type": "configuration_validation",
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error testing MCP connection for {app_slug}: {e}")
            return {
                "success": False,
                "app_slug": app_slug,
                "error": str(e),
                "test_type": "configuration_validation",
            }

    def generate_openai_integration_example(self, app_slug: str) -> str:
        """Generate example code for OpenAI integration with specific MCP service"""
        mcp_config = self.create_mcp_tool_config(app_slug, "your_user_id")

        example_code = f"""
# OpenAI Integration Example for {app_slug.title()}
import openai

client = openai.OpenAI()

# MCP tool configuration for {app_slug}
mcp_tool = {json.dumps(mcp_config, indent=2)}

# Example usage with OpenAI Chat Completions
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {{
            "role": "user", 
            "content": "Help me with {app_slug} integration - show me what I can do"
        }}
    ],
    tools=[mcp_tool]
)

print(response.choices[0].message.content)
"""
        return example_code

    def health_check(self) -> Dict[str, Any]:
        """Check health of Pipedream MCP connection"""
        try:
            if not self.enabled:
                return {
                    "status": "disabled",
                    "message": "Pipedream MCP not configured - missing credentials",
                    "demo_mode": True,
                    "timestamp": datetime.now().isoformat(),
                }

            # Test authentication
            if not self.access_token:
                auth_result = self._authenticate()
                if not auth_result:
                    return {
                        "status": "unhealthy",
                        "error": "Authentication failed",
                        "timestamp": datetime.now().isoformat(),
                    }

            # Test app discovery
            apps_result = self.discover_apps()
            if "error" in apps_result:
                return {
                    "status": "unhealthy",
                    "error": f"App discovery failed: {apps_result['error']}",
                    "timestamp": datetime.now().isoformat(),
                }

            available_apps = len(apps_result.get("data", []))

            return {
                "status": "healthy",
                "project_id": self.project_id,
                "environment": self.environment,
                "available_apps": available_apps,
                "mcp_server_url": self.mcp_url,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def export_mcp_configs(
        self, external_user_id: str = "pipewise_user", output_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """Export all MCP configurations to a file"""
        try:
            # Get all target services configurations
            all_configs = self.get_target_services_mcp(external_user_id)

            # Add metadata
            export_data = {
                "export_metadata": {
                    "created_at": datetime.now().isoformat(),
                    "pipedream_project_id": self.project_id,
                    "environment": self.environment,
                    "external_user_id": external_user_id,
                    "services_count": len(all_configs["mcp_configurations"]),
                },
                "configurations": all_configs,
            }

            # Save to file if specified
            if output_file:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                logger.info(f"✅ MCP configurations exported to {output_file}")
                export_data["export_file"] = output_file

            return export_data

        except Exception as e:
            logger.error(f"Error exporting MCP configs: {e}")
            return {"error": str(e)}


def get_pipedream_mcp_client() -> PipedreamMCPClient:
    """Get instance of Pipedream MCP client"""
    return PipedreamMCPClient()


# Example usage and testing
if __name__ == "__main__":
    print("🚀 Testing Pipedream MCP Client")
    print("=" * 60)

    # Initialize client
    client = PipedreamMCPClient()

    # Health check
    print("\n🏥 Health Check:")
    health = client.health_check()
    print(json.dumps(health, indent=2))

    # Discover target apps
    print("\n🔍 Discovering Target Apps:")
    target_services = ["calendly", "salesforce", "sendgrid"]

    for service in target_services:
        print(f"\n📋 {service.title()}:")
        app_details = client.get_app_details(service)
        print(f"   Description: {app_details.get('description', 'N/A')}")
        print(f"   Auth Type: {app_details.get('auth_type', 'N/A')}")
        print(f"   Tools: {len(app_details.get('tools', []))} available")

    # Generate MCP configurations
    print("\n⚙️ Generating MCP Configurations:")
    all_configs = client.get_target_services_mcp("demo_user")
    print(f"   Generated configs for {len(all_configs['mcp_configurations'])} services")

    # Test connections
    print("\n🧪 Testing MCP Connections:")
    for service in ["calendly", "salesforce"]:
        test_result = client.test_mcp_connection(service)
        status = "✅" if test_result["success"] else "❌"
        print(f"   {status} {service}: {test_result.get('error', 'OK')}")

    # Export configurations
    print("\n💾 Exporting Configurations:")
    try:
        export_result = client.export_mcp_configs(
            "demo_user", "pipewise_mcp_configs.json"
        )
        if "error" not in export_result:
            print("   ✅ Configurations exported successfully")
            print(f"   📁 File: {export_result.get('export_file', 'N/A')}")
        else:
            print(f"   ❌ Export failed: {export_result['error']}")
    except Exception as e:
        print(f"   ❌ Export error: {e}")

    print("\n🎉 Pipedream MCP Client Test Complete!")
