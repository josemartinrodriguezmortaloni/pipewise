#!/usr/bin/env python3
"""
Demo: Pipedream MCP Integration with PipeWise Agents

This script demonstrates the integration of Pipedream MCP servers directly with the coordinator
and meeting scheduler agents, following the OpenAI Agents SDK documentation.

The agents now have access to:
- Calendly v2 (7 tools) for meeting scheduling
- Pipedrive (37 tools) for CRM operations
- Zoho CRM (11 tools) for CRM operations
- Salesforce REST API (30 tools) for enterprise CRM
- SendGrid (20 tools) for email automation
- Google Calendar (10 tools) for calendar management

Total: 115+ tools across 6 major business platforms
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.agents.agents import (
    ModernAgents,
    TenantContext,
    IncomingMessage,
    create_pipedream_mcp_servers,
    MemoryManager,
    InMemoryStore,
    SupabaseMemoryStore,
)
from app.supabase.supabase_client import SupabaseCRMClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demo_mcp_integration():
    """
    Demonstrate Pipedream MCP integration with PipeWise agents
    """
    logger.info("🚀 Starting Pipedream MCP Integration Demo")

    # Check for required environment variables
    pipedream_token = os.getenv("PIPEDREAM_TOKEN")
    if not pipedream_token:
        logger.warning("⚠️ PIPEDREAM_TOKEN not set. Demo will run without MCP servers.")
        logger.info("To enable MCP integration, set these environment variables:")
        logger.info("  - PIPEDREAM_TOKEN=your_pipedream_token")
        logger.info("  - PIPEDREAM_PROJECT_ID=your_project_id (optional)")
        logger.info("  - PIPEDREAM_ENVIRONMENT=production (optional)")
    else:
        logger.info("✅ Pipedream token found. MCP servers will be created.")

    # Test 1: Create MCP servers
    logger.info("\n=== Test 1: Creating Pipedream MCP Servers ===")
    try:
        mcp_servers = create_pipedream_mcp_servers()
        logger.info(f"✅ Created {len(mcp_servers)} MCP servers:")
        for name, server in mcp_servers.items():
            logger.info(f"  - {name}: {server.name}")
    except Exception as e:
        logger.error(f"❌ Error creating MCP servers: {e}")
        mcp_servers = {}

    # Test 2: Initialize ModernAgents with MCP integration
    logger.info("\n=== Test 2: Initializing ModernAgents System ===")
    try:
        # Create tenant context with memory
        db_client = SupabaseCRMClient()
        volatile_store = InMemoryStore(default_ttl=3600)
        persistent_store = SupabaseMemoryStore(db_client.client)
        memory_manager = MemoryManager(volatile_store, persistent_store)

        tenant_context = TenantContext(
            tenant_id="demo_tenant",
            user_id="demo_user",
            is_premium=True,
            api_limits={"calls_per_hour": 1000},
            features_enabled=["mcp_integration", "advanced_scheduling", "multi_crm"],
            memory_manager=memory_manager,
        )

        agents = ModernAgents(tenant_context)
        logger.info("✅ ModernAgents system initialized with MCP integration")

    except Exception as e:
        logger.error(f"❌ Error initializing ModernAgents: {e}")
        return

    # Test 3: Demo email message processing with MCP
    logger.info("\n=== Test 3: Email Message Processing with MCP Tools ===")
    try:
        email_message = IncomingMessage(
            lead_id="lead_001",
            channel="email",
            message_content="Hi, I'm interested in your service. Can we schedule a demo call for next week? I'm the CEO of TechCorp.",
            context={"sender_email": "ceo@techcorp.com"},
        )

        logger.info(f"Processing email message: {email_message.message_content}")
        result = await agents.handle_incoming_message(email_message)

        logger.info("✅ Email message processed with MCP integration:")
        logger.info(f"  Status: {result['status']}")
        logger.info(f"  Workflow ID: {result['workflow_id']}")
        logger.info(f"  Message processed: {result['message_processed']}")

        if result["status"] == "completed" and "result" in result:
            logger.info(f"  Coordinator response: {result['result']}")

    except Exception as e:
        logger.error(f"❌ Error processing email message: {e}")

    # Test 4: Demo Instagram message processing
    logger.info("\n=== Test 4: Instagram Message Processing with MCP Tools ===")
    try:
        instagram_message = IncomingMessage(
            lead_id="lead_002",
            channel="instagram",
            channel_user_id="instagram_123456",
            channel_username="business_owner",
            message_content="Your product looks amazing! Do you have enterprise plans? We're a 500+ employee company looking for a solution.",
        )

        logger.info(
            f"Processing Instagram message: {instagram_message.message_content}"
        )
        result = await agents.handle_incoming_message(instagram_message)

        logger.info("✅ Instagram message processed with MCP integration:")
        logger.info(f"  Status: {result['status']}")
        logger.info(f"  Workflow ID: {result['workflow_id']}")

    except Exception as e:
        logger.error(f"❌ Error processing Instagram message: {e}")

    # Test 5: Demo lead workflow with MCP tools
    logger.info("\n=== Test 5: Complete Lead Workflow with MCP Tools ===")
    try:
        lead_data = {
            "id": "lead_003",
            "name": "Sarah Johnson",
            "email": "sarah@example.com",
            "company": "Innovation Labs",
            "message": "We need a scalable solution for our growing team. Looking to schedule a technical demo.",
            "metadata": {
                "company_size": "200+",
                "industry": "SaaS",
                "budget_mentioned": True,
            },
        }

        logger.info(
            f"Processing lead workflow for: {lead_data['name']} from {lead_data['company']}"
        )
        result = await agents.run_workflow(lead_data)

        logger.info("✅ Lead workflow completed with MCP integration:")
        logger.info(f"  Status: {result['status']}")
        logger.info(f"  Workflow ID: {result['workflow_id']}")
        logger.info(f"  Lead ID: {result['lead_id']}")

        if "memory_summary" in result:
            memory_summary = result["memory_summary"]
            logger.info(f"  Memory Summary:")
            logger.info(
                f"    - Volatile memories: {memory_summary['volatile_memories']}"
            )
            logger.info(
                f"    - Persistent memories: {memory_summary['persistent_memories']}"
            )
            logger.info(
                f"    - Handoffs recorded: {memory_summary['handoffs_recorded']}"
            )

    except Exception as e:
        logger.error(f"❌ Error processing lead workflow: {e}")

    # Test 6: MCP Server Status Summary
    logger.info("\n=== Test 6: MCP Integration Summary ===")

    mcp_status = {
        "calendly": "Meeting scheduling tools available"
        if "calendly" in mcp_servers
        else "Not available",
        "pipedrive": "CRM tools available"
        if "pipedrive" in mcp_servers
        else "Not available",
        "salesforce": "Enterprise CRM tools available"
        if "salesforce" in mcp_servers
        else "Not available",
        "zoho_crm": "Zoho CRM tools available"
        if "zoho_crm" in mcp_servers
        else "Not available",
        "sendgrid": "Email automation tools available"
        if "sendgrid" in mcp_servers
        else "Not available",
        "google_calendar": "Calendar management tools available"
        if "google_calendar" in mcp_servers
        else "Not available",
    }

    logger.info("MCP Server Integration Status:")
    for service, status in mcp_status.items():
        icon = "✅" if "available" in status else "❌"
        logger.info(f"  {icon} {service.title()}: {status}")

    total_servers = len(mcp_servers)
    estimated_tools = {
        "calendly": 7,
        "pipedrive": 37,
        "salesforce": 30,
        "zoho_crm": 11,
        "sendgrid": 20,
        "google_calendar": 10,
    }

    total_tools = sum(estimated_tools[name] for name in mcp_servers.keys())
    logger.info(f"\n📊 Integration Summary:")
    logger.info(f"  - Active MCP servers: {total_servers}/6")
    logger.info(f"  - Estimated available tools: {total_tools}")
    logger.info(f"  - Coordinator MCP access: CRM & Email servers")
    logger.info(f"  - Meeting Scheduler MCP access: Calendly & Google Calendar")

    if total_servers > 0:
        logger.info("\n🎉 Pipedream MCP integration is working!")
        logger.info(
            "Agents now have access to external business tools via MCP protocol."
        )
    else:
        logger.info(
            "\n⚠️ No MCP servers active. Set PIPEDREAM_TOKEN to enable integration."
        )

    logger.info("\n✅ Demo completed!")


if __name__ == "__main__":
    asyncio.run(demo_mcp_integration())
