"""
Demo script for the Enhanced Coordinator System with Multi-Channel Communication

This script demonstrates:
1. Coordinator as primary contact point
2. Direct communication via email, Instagram, and Twitter
3. Intelligent lead qualification through conversation
4. Smart handoffs to specialists when needed
5. Complete workflow tracking with dual memory system
"""

import asyncio
import logging
import uuid
from typing import Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from app.agents.agents import ModernAgents, IncomingMessage, TenantContext
from app.agents.memory import MemoryManager, InMemoryStore, SupabaseMemoryStore
from app.supabase.supabase_client import SupabaseCRMClient


async def demo_email_conversation():
    """Demonstrate email conversation handling"""
    print("\n" + "=" * 80)
    print("🔥 DEMO 1: EMAIL CONVERSATION WORKFLOW")
    print("=" * 80)

    # Initialize enhanced agent system
    agents = ModernAgents()

    # Simulate incoming email from a prospect
    lead_id = "demo_lead_email_001"
    email_content = """
    Hola,

    Soy Carlos, CEO de TechStartup Solutions. Estamos buscando una solución 
    para automatizar nuestro proceso de seguimiento de leads. Actualmente
    tenemos un equipo de 15 vendedores y estamos perdiendo muchas oportunidades
    por falta de seguimiento sistemático.

    ¿Pueden ayudarnos con esto?

    Saludos,
    Carlos Rodríguez
    CEO, TechStartup Solutions
    carlos@techstartup.com
    """

    print(f"📧 Incoming email from lead {lead_id}:")
    print(f"Content: {email_content}")

    # Process the email with the coordinator
    result = await agents.handle_email_message(
        lead_id=lead_id,
        email_content=email_content,
        sender_email="carlos@techstartup.com",
    )

    print(f"\n✅ Email processed successfully!")
    print(f"Status: {result['status']}")
    print(f"Channel: {result.get('channel', 'unknown')}")
    print(f"Workflow ID: {result['workflow_id']}")


async def demo_instagram_interaction():
    """Demonstrate Instagram DM handling"""
    print("\n" + "=" * 80)
    print("📸 DEMO 2: INSTAGRAM DM INTERACTION")
    print("=" * 80)

    agents = ModernAgents()

    # Simulate Instagram DM from a marketing manager
    lead_id = "demo_lead_ig_002"
    instagram_message = """
    Hola! Vi tu contenido sobre automatización de CRM. 
    Manejo marketing para 3 empresas diferentes y el follow-up 
    manual me está matando 😅 ¿PipeWise podría ayudarme?
    """

    print(f"📱 Incoming Instagram DM from @marketingmaria:")
    print(f"Message: {instagram_message}")

    # Process Instagram message
    result = await agents.handle_instagram_message(
        lead_id=lead_id,
        message_content=instagram_message,
        instagram_user_id="ig_123456789",
        username="marketingmaria",
    )

    print(f"\n✅ Instagram DM processed!")
    print(f"Status: {result['status']}")
    print(f"Channel: {result.get('channel', 'unknown')}")


async def demo_twitter_mention_response():
    """Demonstrate Twitter mention and response"""
    print("\n" + "=" * 80)
    print("🐦 DEMO 3: TWITTER MENTION RESPONSE")
    print("=" * 80)

    agents = ModernAgents()

    # Simulate Twitter mention
    lead_id = "demo_lead_twitter_003"
    twitter_message = """
    @PipeWiseCRM ¿Tienen alguna solución para equipos de ventas remotos? 
    Nuestro CRM actual no se integra bien con herramientas de trabajo remoto.
    """

    print(f"🐦 Incoming Twitter mention from @techleader:")
    print(f"Message: {twitter_message}")

    # Process Twitter mention
    result = await agents.handle_twitter_message(
        lead_id=lead_id,
        message_content=twitter_message,
        twitter_user_id="tw_987654321",
        username="techleader",
        tweet_id="tweet_123456",
    )

    print(f"\n✅ Twitter mention processed!")
    print(f"Status: {result['status']}")
    print(f"Channel: {result.get('channel', 'unknown')}")


async def demo_multi_channel_conversation():
    """Demonstrate a lead communicating across multiple channels"""
    print("\n" + "=" * 80)
    print("🔄 DEMO 4: MULTI-CHANNEL CONVERSATION")
    print("=" * 80)

    agents = ModernAgents()
    lead_id = "demo_lead_multichannel_004"

    # 1. Initial contact via email
    print("📧 Step 1: Initial email contact")
    email_result = await agents.handle_email_message(
        lead_id=lead_id,
        email_content="Hola, ¿pueden enviarme información sobre PipeWise?",
        sender_email="lead@company.com",
    )
    print(f"   Email processed: {email_result['status']}")

    # 2. Follow-up via Instagram
    print("\n📱 Step 2: Follow-up via Instagram DM")
    ig_result = await agents.handle_instagram_message(
        lead_id=lead_id,
        message_content="Vi que me respondieron por email. ¿Pueden mostrarme un demo?",
        instagram_user_id="ig_lead_123",
        username="business_lead",
    )
    print(f"   Instagram DM processed: {ig_result['status']}")

    # 3. Final engagement via Twitter
    print("\n🐦 Step 3: Public engagement via Twitter")
    twitter_result = await agents.handle_twitter_message(
        lead_id=lead_id,
        message_content="@PipeWiseCRM Excelente atención! Ya agendé mi demo 👏",
        twitter_user_id="tw_lead_456",
        username="business_lead",
        tweet_id="tweet_789",
    )
    print(f"   Twitter mention processed: {twitter_result['status']}")

    print(f"\n✅ Multi-channel conversation completed!")
    print(f"   - Channels used: email, instagram, twitter")
    print(f"   - Lead ID: {lead_id}")


async def demo_coordinator_intelligence():
    """Demonstrate intelligent coordinator responses and handoffs"""
    print("\n" + "=" * 80)
    print("🧠 DEMO 5: COORDINATOR INTELLIGENCE & HANDOFFS")
    print("=" * 80)

    agents = ModernAgents()

    # Scenario 1: Simple question - Coordinator handles directly
    print("🔍 Scenario 1: Simple information request")
    simple_result = await agents.handle_email_message(
        lead_id="demo_lead_simple",
        email_content="¿Cuáles son los precios de PipeWise?",
        sender_email="simple@lead.com",
    )
    print(f"   Simple question handled: {simple_result['status']}")

    # Scenario 2: Complex qualification - Handoff to specialist
    print("\n🔍 Scenario 2: Complex lead qualification")
    complex_message = """
    Somos una empresa de 200 empleados en el sector financiero.
    Necesitamos un CRM que cumpla con regulaciones SOX y GDPR,
    con integración a nuestro ERP SAP, capacidad para 50,000 contactos,
    y que soporte workflows complejos de aprobación multinivel.
    ¿PipeWise puede manejar estos requerimientos?
    """

    complex_result = await agents.handle_email_message(
        lead_id="demo_lead_complex",
        email_content=complex_message,
        sender_email="cto@financorp.com",
    )
    print(f"   Complex qualification processed: {complex_result['status']}")

    # Scenario 3: Ready to buy - Meeting scheduling
    print("\n🔍 Scenario 3: Ready for meeting")
    meeting_message = """
    Ya revisé toda la información y estoy convencido.
    ¿Podemos agendar una llamada esta semana para discutir implementación?
    Prefiero martes o miércoles por la tarde.
    """

    meeting_result = await agents.handle_email_message(
        lead_id="demo_lead_meeting",
        email_content=meeting_message,
        sender_email="ready@buyer.com",
    )
    print(f"   Meeting request handled: {meeting_result['status']}")


async def demo_memory_and_context():
    """Demonstrate memory system and context preservation"""
    print("\n" + "=" * 80)
    print("🧠 DEMO 6: MEMORY SYSTEM & CONTEXT PRESERVATION")
    print("=" * 80)

    # Initialize with custom tenant context
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

    agents = ModernAgents(tenant_context)
    lead_id = "demo_lead_memory"

    # First interaction
    print("📝 First interaction - Establishing context")
    first_result = await agents.handle_email_message(
        lead_id=lead_id,
        email_content="Soy María, directora de ventas. Tenemos 25 vendedores y queremos automatizar seguimientos.",
        sender_email="maria@sales.com",
    )
    print(f"   First interaction: {first_result['status']}")

    # Second interaction - Should remember context
    print("\n📝 Second interaction - Using remembered context")
    second_result = await agents.handle_instagram_message(
        lead_id=lead_id,
        message_content="¿Cómo se integra con Salesforce? Es nuestro CRM actual.",
        instagram_user_id="ig_maria_123",
        username="maria_sales",
    )
    print(f"   Second interaction: {second_result['status']}")

    # Third interaction - Cross-channel context
    print("\n📝 Third interaction - Cross-channel context")
    third_result = await agents.handle_twitter_message(
        lead_id=lead_id,
        message_content="@PipeWiseCRM ¿La demo incluye la integración con Salesforce que discutimos?",
        twitter_user_id="tw_maria_456",
        username="maria_sales",
    )
    print(f"   Third interaction: {third_result['status']}")

    # Check memory summary
    print(f"\n🧠 Memory Summary for lead {lead_id}:")
    try:
        # Get a sample workflow ID to check memories
        sample_workflow = first_result.get("workflow_id")
        if sample_workflow:
            context = await memory_manager.get_workflow_context(sample_workflow)
            print(f"   - Volatile memories: {len(context.get('volatile', []))}")
            print(f"   - Persistent memories: {len(context.get('persistent', []))}")
    except Exception as e:
        print(f"   - Memory check error: {e}")


async def main():
    """Run all demonstration scenarios"""
    print("🚀 PipeWise Enhanced Coordinator System Demo")
    print("=" * 80)
    print("This demo showcases the new coordinator capabilities:")
    print("- Multi-channel communication (Email, Instagram, Twitter)")
    print("- Direct prospect interaction (not just coordination)")
    print("- Intelligent response generation")
    print("- Smart handoffs to specialists when needed")
    print("- Complete memory and context preservation")
    print()

    try:
        # Run all demo scenarios
        await demo_email_conversation()
        await demo_instagram_interaction()
        await demo_twitter_mention_response()
        await demo_multi_channel_conversation()
        await demo_coordinator_intelligence()
        await demo_memory_and_context()

        print("\n" + "=" * 80)
        print("🎉 ALL DEMOS COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print()
        print("📊 SUMMARY OF CAPABILITIES DEMONSTRATED:")
        print("✅ Email conversation handling")
        print("✅ Instagram DM processing")
        print("✅ Twitter mention responses")
        print("✅ Multi-channel lead tracking")
        print("✅ Intelligent coordinator decisions")
        print("✅ Memory system with context preservation")
        print("✅ Smart handoffs to specialists")
        print()
        print("🎯 The Enhanced Coordinator System is now the primary contact point")
        print(
            "   for all prospects, providing personalized responses across all channels"
        )
        print("   while intelligently coordinating with specialists when needed.")

    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"\n❌ Demo failed with error: {e}")


if __name__ == "__main__":
    # Run the comprehensive demo
    asyncio.run(main())
