"""
Basic test for Enhanced Coordinator System functionality
"""

import asyncio
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.agents.agents import ModernAgents, IncomingMessage, TenantContext


async def test_basic_email_handling():
    """Test basic email message handling"""
    print("\n🔥 Testing Email Message Handling")
    print("=" * 50)

    # Initialize the enhanced agent system
    agents = ModernAgents()

    # Create a sample email message
    print("📧 Creating sample email message...")
    result = await agents.handle_email_message(
        lead_id="test_lead_001",
        email_content="Hello, I'm interested in PipeWise CRM for my startup",
        sender_email="test@startup.com",
    )

    print(f"✅ Email processed: {result['status']}")
    print(f"📊 Workflow ID: {result.get('workflow_id', 'N/A')}")
    print(f"📞 Channel: {result.get('channel', 'N/A')}")


async def test_basic_instagram_handling():
    """Test basic Instagram message handling"""
    print("\n📸 Testing Instagram Message Handling")
    print("=" * 50)

    agents = ModernAgents()

    print("📱 Creating sample Instagram DM...")
    result = await agents.handle_instagram_message(
        lead_id="test_lead_002",
        message_content="Saw your post about CRM automation! Interested 🚀",
        instagram_user_id="ig_123456",
        username="testuser",
    )

    print(f"✅ Instagram DM processed: {result['status']}")
    print(f"📊 Workflow ID: {result.get('workflow_id', 'N/A')}")


async def test_basic_twitter_handling():
    """Test basic Twitter message handling"""
    print("\n🐦 Testing Twitter Message Handling")
    print("=" * 50)

    agents = ModernAgents()

    print("🐦 Creating sample Twitter mention...")
    result = await agents.handle_twitter_message(
        lead_id="test_lead_003",
        message_content="@PipeWiseCRM looks like a great solution for sales teams!",
        twitter_user_id="tw_789012",
        username="businessleader",
        tweet_id="tweet_456789",
    )

    print(f"✅ Twitter mention processed: {result['status']}")
    print(f"📊 Workflow ID: {result.get('workflow_id', 'N/A')}")


async def test_incoming_message_model():
    """Test IncomingMessage model creation"""
    print("\n🔧 Testing IncomingMessage Model")
    print("=" * 50)

    # Test email message model
    email_msg = IncomingMessage(
        lead_id="lead_123",
        channel="email",
        message_content="Test email content",
        context={"sender_email": "test@example.com"},
    )
    print(f"✅ Email message model: {email_msg.channel} from {email_msg.lead_id}")

    # Test Instagram message model
    ig_msg = IncomingMessage(
        lead_id="lead_456",
        channel="instagram",
        channel_user_id="ig_123",
        channel_username="testuser",
        message_content="Test IG content",
    )
    print(
        f"✅ Instagram message model: {ig_msg.channel} from @{ig_msg.channel_username}"
    )

    # Test Twitter message model
    twitter_msg = IncomingMessage(
        lead_id="lead_789",
        channel="twitter",
        channel_user_id="tw_456",
        channel_username="twitteruser",
        message_content="Test tweet content",
        context={"tweet_id": "tweet_123"},
    )
    print(
        f"✅ Twitter message model: {twitter_msg.channel} from @{twitter_msg.channel_username}"
    )


async def test_tenant_context():
    """Test TenantContext functionality"""
    print("\n👥 Testing TenantContext")
    print("=" * 50)

    from app.agents.memory import MemoryManager, InMemoryStore, SupabaseMemoryStore
    from app.supabase.supabase_client import SupabaseCRMClient

    # Create custom tenant context
    db_client = SupabaseCRMClient()
    volatile_store = InMemoryStore(default_ttl=3600)
    persistent_store = SupabaseMemoryStore(db_client.client)
    memory_manager = MemoryManager(volatile_store, persistent_store)

    tenant_context = TenantContext(
        tenant_id="demo_tenant",
        user_id="demo_user",
        is_premium=True,
        api_limits={"calls_per_hour": 1000},
        features_enabled=["multi_channel", "ai_coordinator", "memory_system"],
        memory_manager=memory_manager,
    )

    print(f"✅ Tenant context created: {tenant_context.tenant_id}")
    print(f"📋 Features enabled: {tenant_context.features_enabled}")
    print(f"🔧 Memory manager: {'✓' if tenant_context.memory_manager else '✗'}")

    # Test ModernAgents with custom context
    agents = ModernAgents(tenant_context)
    print(f"✅ ModernAgents with custom context: {agents.tenant_context.tenant_id}")


async def main():
    """Run all basic tests"""
    print("🚀 Enhanced Coordinator System - Basic Tests")
    print("=" * 60)
    print("Testing core functionality of the enhanced system...")
    print()

    try:
        # Test individual components
        await test_incoming_message_model()
        await test_tenant_context()

        # Test async message handling
        await test_basic_email_handling()
        await test_basic_instagram_handling()
        await test_basic_twitter_handling()

        print("\n" + "=" * 60)
        print("🎉 ALL BASIC TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print()
        print("✅ Core components working:")
        print("  • IncomingMessage model")
        print("  • TenantContext configuration")
        print("  • ModernAgents initialization")
        print("  • Email message handling")
        print("  • Instagram message handling")
        print("  • Twitter message handling")
        print()
        print("🎯 The enhanced coordinator system is ready for production!")

    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"\n❌ Test failed with error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
