#!/usr/bin/env python3
"""
Test script for Twitter MCP server integration with PipeWise orchestrator.

This script tests:
1. Twitter MCP server initialization
2. Integration with the agent orchestrator
3. Agent workflow with Twitter tools
4. Message processing through Twitter channel
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.agents.agents import (
    ModernAgents,
    TenantContext,
    IncomingMessage,
    create_all_mcp_servers,
    create_twitter_mcp_server,
)

# from app.agents.tools.twitter import TwitterMCPServer  # TEMPORARILY DISABLED - Use MCP instead


# Temporary mock TwitterMCPServer
class TwitterMCPServer:
    """Temporary mock for TwitterMCPServer"""

    def __init__(self, *args, **kwargs):
        pass


from app.agents.memory import MemoryManager, InMemoryStore, SupabaseMemoryStore
from app.supabase.supabase_client import SupabaseCRMClient

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_twitter_mcp_server():
    """Test basic Twitter MCP server functionality"""
    logger.info("🧪 Testing Twitter MCP Server...")

    try:
        # Initialize Twitter MCP server
        twitter_server = TwitterMCPServer()
        logger.info("✅ Twitter MCP server initialized successfully")

        # Test basic Twitter functions
        test_username = "testuser"
        test_message = "Hello from PipeWise CRM!"

        # Test get user info
        user_info = twitter_server.get_user_by_username(test_username)
        logger.info(f"📱 User info result: {user_info}")

        # Test send DM
        dm_result = twitter_server.send_dm("mock_user_id", test_message)
        logger.info(f"💬 Send DM result: {dm_result}")

        return True

    except Exception as e:
        logger.error(f"❌ Twitter MCP server test failed: {e}")
        return False


async def test_mcp_servers_integration():
    """Test MCP servers integration with user filtering"""
    logger.info("🧪 Testing MCP servers integration...")

    try:
        # Test creating all MCP servers for a test user
        test_user_id = "test_user_123"
        mcp_servers = create_all_mcp_servers(test_user_id)

        logger.info(f"✅ Created {len(mcp_servers)} MCP servers")
        for server_name, server in mcp_servers.items():
            logger.info(f"   📡 {server_name}: {type(server).__name__}")

        # Test Twitter-specific server
        twitter_server = create_twitter_mcp_server(test_user_id)
        if twitter_server:
            logger.info("✅ Twitter MCP server created successfully")
        else:
            logger.warning("⚠️ Twitter MCP server not created")

        return True

    except Exception as e:
        logger.error(f"❌ MCP servers integration test failed: {e}")
        return False


async def test_agents_with_twitter():
    """Test agents integration with Twitter MCP tools"""
    logger.info("🧪 Testing agents with Twitter integration...")

    try:
        # Create tenant context for testing
        tenant_context = TenantContext(
            tenant_id="test_tenant",
            user_id="test_user_123",
            is_premium=True,
            api_limits={"twitter_dms": 100, "api_calls": 1000},
            features_enabled=["twitter", "calendly", "sendgrid"],
        )

        # Initialize ModernAgents
        agents_system = ModernAgents(tenant_context)
        logger.info("✅ ModernAgents system initialized with Twitter support")

        # Test incoming Twitter message processing
        twitter_message = IncomingMessage(
            lead_id="test_lead_001",
            channel="twitter",
            channel_user_id="twitter_user_123",
            channel_username="prospective_client",
            message_content="Hi! I'm interested in your CRM solution. Can we schedule a demo?",
            context={"tweet_id": "1234567890", "is_dm": True, "follower_count": 1500},
        )

        # Process the Twitter message
        result = await agents_system.handle_incoming_message(twitter_message)
        logger.info(f"📨 Twitter message processing result: {result}")

        return True

    except Exception as e:
        logger.error(f"❌ Agents with Twitter test failed: {e}")
        return False


async def test_twitter_workflow():
    """Test complete Twitter lead workflow"""
    logger.info("🧪 Testing complete Twitter lead workflow...")

    try:
        # Create test lead data with Twitter context
        lead_data = {
            "lead_id": "twitter_lead_001",
            "name": "Alex Johnson",
            "company": "TechStart Inc.",
            "email": "alex@techstart.com",
            "phone": "+1-555-0123",
            "source": "twitter",
            "channel_data": {
                "twitter_username": "alex_techstart",
                "twitter_id": "123456789",
                "tweet_id": "987654321",
                "follower_count": 2500,
                "verified": False,
            },
            "message": "Looking for a CRM that integrates with our Twitter campaigns. What can you offer?",
            "metadata": {
                "company_size": "startup",
                "industry": "technology",
                "budget_indicator": True,
                "urgency": "medium",
            },
        }

        # Initialize agents system
        tenant_context = TenantContext(
            tenant_id="test_tenant",
            user_id="test_user_123",
            is_premium=True,
            api_limits={"twitter_dms": 100},
            features_enabled=["twitter", "calendly"],
        )

        agents_system = ModernAgents(tenant_context)

        # Run the complete workflow
        result = await agents_system.run_workflow(lead_data)
        logger.info(f"🚀 Complete Twitter workflow result: {result}")

        return True

    except Exception as e:
        logger.error(f"❌ Twitter workflow test failed: {e}")
        return False


async def main():
    """Run all Twitter MCP integration tests"""
    logger.info("🚀 Starting Twitter MCP integration tests...")

    tests = [
        ("Twitter MCP Server", test_twitter_mcp_server),
        ("MCP Servers Integration", test_mcp_servers_integration),
        ("Agents with Twitter", test_agents_with_twitter),
        ("Twitter Workflow", test_twitter_workflow),
    ]

    results = []

    for test_name, test_func in tests:
        logger.info(f"\n{'=' * 50}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'=' * 50}")

        try:
            result = await test_func()
            results.append((test_name, result))
            if result:
                logger.info(f"✅ {test_name} PASSED")
            else:
                logger.error(f"❌ {test_name} FAILED")
        except Exception as e:
            logger.error(f"💥 {test_name} CRASHED: {e}")
            results.append((test_name, False))

    # Summary
    logger.info(f"\n{'=' * 50}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'=' * 50}")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} {test_name}")

    logger.info(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        logger.info("🎉 All Twitter MCP integration tests passed!")
        return True
    else:
        logger.error(f"💥 {total - passed} tests failed!")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
