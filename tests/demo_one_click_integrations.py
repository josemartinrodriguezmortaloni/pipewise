#!/usr/bin/env python3
"""
Demo: One-Click MCP Integrations

This script demonstrates the new one-click integration functionality for Pipedream MCP services.
Users can now enable powerful business tools with a single click without needing API keys.

Features demonstrated:
- One-click MCP integration enabling/disabling
- Frontend integration with modern UI
- Seamless agent integration with 115+ tools
- Real-time status updates

MCP Integrations Available:
- Calendly v2 (7 tools) - Meeting scheduling
- Pipedrive (37 tools) - CRM operations
- Salesforce REST API (30 tools) - Enterprise CRM
- Zoho CRM (11 tools) - Small business CRM
- SendGrid (20 tools) - Email automation
- Google Calendar (10 tools) - Calendar management

Total: 115+ tools across 6 major business platforms
"""

import json
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def print_header():
    """Print demo header"""
    print("\n" + "=" * 80)
    print("🚀 PipeWise: One-Click MCP Integrations Demo")
    print("=" * 80)
    print("This demo shows the new one-click integration system for MCP services.")
    print("Users can enable powerful business tools instantly without API keys!\n")


def print_mcp_integrations():
    """Display available MCP integrations"""
    integrations = [
        {
            "name": "Calendly v2",
            "tools": 7,
            "description": "Meeting scheduling and calendar management",
            "category": "Calendar",
            "popular": True,
        },
        {
            "name": "Pipedrive",
            "tools": 37,
            "description": "CRM operations and pipeline management",
            "category": "CRM",
            "popular": True,
        },
        {
            "name": "Salesforce REST API",
            "tools": 30,
            "description": "Enterprise CRM and opportunity management",
            "category": "CRM",
            "premium": True,
        },
        {
            "name": "Zoho CRM",
            "tools": 11,
            "description": "Small business CRM solution",
            "category": "CRM",
        },
        {
            "name": "SendGrid",
            "tools": 20,
            "description": "Email automation and delivery",
            "category": "Email",
            "popular": True,
        },
        {
            "name": "Google Calendar",
            "tools": 10,
            "description": "Calendar synchronization and event management",
            "category": "Calendar",
            "popular": True,
        },
    ]

    print("📋 Available MCP Integrations:")
    print("-" * 80)

    total_tools = 0
    for integration in integrations:
        status_badges = []
        if integration.get("popular"):
            status_badges.append("🔥 Popular")
        if integration.get("premium"):
            status_badges.append("⭐ Premium")

        badges = " " + " ".join(status_badges) if status_badges else ""

        print(f"🔧 {integration['name']} ({integration['tools']} tools){badges}")
        print(f"   📂 {integration['category']} | 📝 {integration['description']}")
        print()

        total_tools += integration["tools"]

    print(
        f"📊 Total: {len(integrations)} integrations with {total_tools}+ tools available"
    )
    print()


def simulate_frontend_interaction():
    """Simulate frontend user interaction"""
    print("🖥️  Frontend User Experience:")
    print("-" * 50)
    print("1. User opens Integrations page")
    print("2. User sees MCP and Legacy API tabs")
    print("3. User clicks on MCP Integrations tab")
    print("4. User sees beautiful cards with one-click setup")
    print("5. User clicks 'Connect Now' button on Pipedrive")
    print("6. System instantly enables Pipedrive MCP integration")
    print("7. Card shows 'Successfully Connected' with green checkmark")
    print("8. AI agents now have access to 37 Pipedrive tools")
    print()


def demonstrate_backend_api():
    """Show backend API demonstration"""
    print("🔧 Backend API Integration:")
    print("-" * 50)

    print("📡 API Endpoints Created:")
    print("   POST /api/integrations/mcp/{integration_id}/enable")
    print("   POST /api/integrations/mcp/{integration_id}/disable")
    print()

    print("🔄 Integration Flow:")
    print("   1. Frontend sends POST to /api/integrations/mcp/pipedrive/enable")
    print("   2. Backend validates integration_id against allowed MCPs")
    print("   3. Backend saves integration config to memory store")
    print("   4. Backend returns success response with integration details")
    print("   5. Frontend updates UI to show connected status")
    print()

    print("💾 Sample API Response:")
    sample_response = {
        "success": True,
        "message": "MCP integration pipedrive enabled successfully",
        "integration": {
            "id": "pipedrive",
            "name": "pipedrive",
            "enabled": True,
            "type": "mcp",
            "tools_count": 37,
            "integration_type": "mcp",
            "pipedream_app_slug": "pipedrive",
        },
    }
    print(json.dumps(sample_response, indent=2))
    print()


def show_agent_integration():
    """Show how agents integrate with MCPs"""
    print("🤖 AI Agent Integration:")
    print("-" * 50)
    print("• Coordinator Agent gets access to CRM tools (Pipedrive, Salesforce, Zoho)")
    print(
        "• Meeting Scheduler Agent gets access to Calendar tools (Calendly, Google Calendar)"
    )
    print("• All agents can use Email tools (SendGrid) for communication")
    print()
    print("🔧 MCP Server Creation:")
    print(
        "   1. create_pipedream_mcp_servers() function creates MCPServerSse instances"
    )
    print("   2. Each MCP server connects to Pipedream infrastructure")
    print("   3. Agents receive mcp_servers parameter in create_agents_with_memory()")
    print("   4. OpenAI Agent SDK automatically loads MCP tools")
    print()
    print("⚡ Real-time Tool Access:")
    print(
        "   • Coordinator can create Pipedrive deals, update contacts, manage pipeline"
    )
    print("   • Meeting Scheduler can check availability, book meetings, send invites")
    print("   • All agents can send emails, manage templates, track delivery")
    print()


def show_benefits():
    """Show key benefits of the new system"""
    print("✨ Key Benefits:")
    print("-" * 30)
    print("🚀 One-Click Setup - No API keys or complex configuration needed")
    print("🔒 Secure - Uses Pipedream's secure MCP infrastructure")
    print("⚡ Instant - Integrations are enabled immediately")
    print("🧠 AI-Ready - Tools automatically available to AI agents")
    print("📈 Scalable - Easy to add new MCP services")
    print("🎨 User-Friendly - Beautiful, modern UI with clear status")
    print("🔄 Reliable - Robust error handling and status management")
    print()


def demonstrate_ui_features():
    """Show UI features"""
    print("🎨 Frontend UI Features:")
    print("-" * 40)
    print("📑 Tabbed Interface:")
    print("   • MCP Integrations tab (6 services, one-click)")
    print("   • API Integrations tab (3 legacy services, manual setup)")
    print()
    print("🎯 Smart Cards:")
    print("   • Popular badge for recommended integrations")
    print("   • Premium badge for enterprise services")
    print("   • Tool count display (e.g., '37 tools')")
    print("   • MCP badge to distinguish from legacy APIs")
    print()
    print("📊 Real-time Stats:")
    print("   • MCP Integrations: X / 6 active")
    print("   • Legacy APIs: X / 3 active")
    print("   • Total Connected: X integrations")
    print("   • Security: Secure (encrypted)")
    print()
    print("🔄 Interactive Elements:")
    print("   • 'Connect Now' button for one-click setup")
    print("   • External link to Pipedream MCP documentation")
    print("   • Loading states with spinners")
    print("   • Success/error state management")
    print()


def run_demo():
    """Run the complete demo"""
    try:
        print_header()
        print_mcp_integrations()
        simulate_frontend_interaction()
        demonstrate_backend_api()
        show_agent_integration()
        demonstrate_ui_features()
        show_benefits()

        print("🎉 Demo completed successfully!")
        print("\nNext steps to test the implementation:")
        print("1. Start the FastAPI backend server")
        print("2. Start the Next.js frontend server")
        print("3. Navigate to /integrations page")
        print("4. Try enabling MCP integrations with one click")
        print("5. Check the console logs to see the integration flow")
        print("\n" + "=" * 80)

    except Exception as e:
        logger.error(f"Demo error: {e}")
        print(f"❌ Demo failed with error: {e}")


if __name__ == "__main__":
    print("Starting One-Click MCP Integrations Demo...")
    run_demo()
