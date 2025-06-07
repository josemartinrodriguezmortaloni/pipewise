#!/usr/bin/env python3
"""
Test script for the corrected workflow with handoffs verification
"""

import asyncio
from app.agents.orchestrator import OrchestratorAgent


async def test_corrected_workflow():
    """Test the corrected workflow with explicit handoff verification"""
    print("🚀 Starting corrected workflow test...")

    # Crear el orchestrator
    orchestrator = OrchestratorAgent()

    # Datos de prueba para un lead que debería calificar
    test_lead_data = {
        "name": "Carlos Rodriguez",
        "email": "carlos.rodriguez@techcorp.com",
        "company": "TechCorp Solutions",
        "phone": "+1-555-0123",
        "message": "Necesitamos automatizar nuestro proceso de ventas para un equipo de 15 personas. Buscamos una solución escalable.",
        "source": "website",
        "utm_params": {},
        "metadata": {"interested_features": ["automation", "scaling"]},
    }

    print("📋 Test lead data:")
    print(f"   - Name: {test_lead_data['name']}")
    print(f"   - Email: {test_lead_data['email']}")
    print(f"   - Company: {test_lead_data['company']}")
    print(f"   - Message: {test_lead_data['message'][:50]}...")

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

    return result


if __name__ == "__main__":
    # Ejecutar test
    result = asyncio.run(test_corrected_workflow())
