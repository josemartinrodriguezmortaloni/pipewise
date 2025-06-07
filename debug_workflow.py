#!/usr/bin/env python3
"""
Debug script to understand exactly what the Manager Agent is doing
"""

import asyncio
import random
from app.agents.orchestrator import OrchestratorAgent


async def debug_workflow():
    """Debug the workflow step by step"""
    print("🐛 Starting workflow debug...")

    # Crear el orchestrator
    orchestrator = OrchestratorAgent()

    # Datos de prueba para un lead completamente nuevo
    random_id = random.randint(1000, 9999)
    test_lead_data = {
        "name": f"Debug Test Lead",
        "email": f"debug.test{random_id}@testcorp.com",
        "company": "TestCorp Debug",
        "phone": "+1-555-0999",
        "message": "Test message for debugging workflow with automation interest and team scaling needs.",
        "source": "debug",
        "utm_params": {"campaign": "debug_test"},
        "metadata": {"debug": True, "interested_features": ["automation", "scaling"]},
    }

    print("🔍 Debug lead data:")
    print(f"   - Name: {test_lead_data['name']}")
    print(f"   - Email: {test_lead_data['email']}")
    print(f"   - Company: {test_lead_data['company']}")

    # Ejecutar workflow y capturar resultado detallado
    result = await orchestrator.run_workflow(test_lead_data)

    print("\n📋 DETAILED WORKFLOW RESULT:")
    print("=" * 50)

    for key, value in result.items():
        print(f"{key}: {value}")

    print("=" * 50)

    # Análisis específico
    print(f"\n🔍 ANALYSIS:")
    print(f"   - Status: {result.get('status', 'unknown')}")
    print(f"   - Success: {result.get('success', False)}")
    print(f"   - Manager Output: {result.get('manager_output', 'N/A')}")
    print(f"   - Handoffs Used: {result.get('handoffs_used', False)}")
    print(f"   - Steps Completed: {result.get('steps_completed', [])}")

    if "final_lead_status" in result:
        final_status = result["final_lead_status"]
        print(f"\n📊 FINAL LEAD STATUS:")
        print(f"   - Lead ID: {final_status.get('lead_id', 'unknown')}")
        print(f"   - Qualified: {final_status.get('qualified', 'unknown')}")
        print(
            f"   - Meeting Scheduled: {final_status.get('meeting_scheduled', 'unknown')}"
        )
        print(f"   - Contacted: {final_status.get('contacted', 'unknown')}")
        print(f"   - Status: {final_status.get('status', 'unknown')}")

        # Determinar si el workflow funcionó completamente
        workflow_complete = (
            final_status.get("qualified", False)
            and final_status.get("meeting_scheduled", False)
            and final_status.get("contacted", False)
        )
        print(
            f"\n🎯 Complete workflow executed: {'✅ YES' if workflow_complete else '❌ NO'}"
        )

        if not workflow_complete:
            print("\n🚨 WORKFLOW ISSUES DETECTED:")
            if not final_status.get("qualified", False):
                print(
                    "   ❌ Lead was not qualified (handoff to qualifier likely failed)"
                )
            if not final_status.get("meeting_scheduled", False):
                print(
                    "   ❌ Meeting was not scheduled (handoff to scheduler likely failed)"
                )
            if not final_status.get("contacted", False):
                print(
                    "   ❌ Lead was not contacted (handoff to outbound likely failed)"
                )
    else:
        print("   ⚠️ No final lead status available - workflow likely failed early")

    return result


if __name__ == "__main__":
    # Ejecutar debug
    result = asyncio.run(debug_workflow())
