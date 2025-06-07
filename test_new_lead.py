#!/usr/bin/env python3
"""
Test script with a completely new lead to force creation and full workflow
"""

import asyncio
import random
from app.agents.orchestrator import OrchestratorAgent


async def test_new_lead_workflow():
    """Test the workflow with a completely new lead"""
    print("🚀 Starting workflow test with NEW lead...")

    # Crear el orchestrator
    orchestrator = OrchestratorAgent()

    # Datos de prueba para un lead completamente nuevo
    random_id = random.randint(1000, 9999)
    test_lead_data = {
        "name": f"Maria Gonzalez",
        "email": f"maria.gonzalez{random_id}@innovatech.com",
        "company": "InnovaTech Solutions",
        "phone": "+1-555-0789",
        "message": "Estamos buscando automatizar nuestros procesos de CRM para nuestro equipo de 25 vendedores. Necesitamos una solución escalable que nos permita aumentar las conversiones.",
        "source": "website",
        "utm_params": {"campaign": "crm_automation"},
        "metadata": {"interested_features": ["automation", "scaling", "analytics"]},
    }

    print("📋 Test lead data (NEW):")
    print(f"   - Name: {test_lead_data['name']}")
    print(f"   - Email: {test_lead_data['email']}")
    print(f"   - Company: {test_lead_data['company']}")
    print(f"   - Message: {test_lead_data['message'][:60]}...")

    # Ejecutar workflow
    result = await orchestrator.run_workflow(test_lead_data)

    print("\n🎉 Workflow completed!")
    print("📊 Final result summary:")
    print(f"   - Status: {result.get('status', 'unknown')}")
    print(f"   - Success: {result.get('success', False)}")
    print(f"   - Pattern: {result.get('pattern', 'unknown')}")

    if "final_lead_status" in result:
        final_status = result["final_lead_status"]
        print("📈 Final lead status:")
        print(f"   - Lead ID: {final_status.get('lead_id', 'unknown')}")
        print(f"   - Qualified: {final_status.get('qualified', 'unknown')}")
        print(
            f"   - Meeting Scheduled: {final_status.get('meeting_scheduled', 'unknown')}"
        )
        print(f"   - Contacted: {final_status.get('contacted', 'unknown')}")
        print(f"   - Status: {final_status.get('status', 'unknown')}")

        # Verificar workflow completo
        workflow_complete = (
            final_status.get("qualified", False)
            and final_status.get("meeting_scheduled", False)
            and final_status.get("contacted", False)
        )
        print(
            f"\n🎯 Complete workflow executed: {'✅ YES' if workflow_complete else '❌ NO'}"
        )
    else:
        print("   ⚠️ No final lead status available")

    return result


if __name__ == "__main__":
    # Ejecutar test
    result = asyncio.run(test_new_lead_workflow())
