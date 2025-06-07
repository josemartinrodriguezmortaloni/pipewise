#!/usr/bin/env python3
"""
Test script to test the Lead Qualifier Agent directly
"""

import asyncio
from app.agents.lead_qualifier import LeadAgent


async def test_qualifier_directly():
    """Test the Lead Qualifier Agent directly"""
    print("🧪 Testing Lead Qualifier Agent directly...")

    # Crear el Lead Qualifier Agent
    qualifier = LeadAgent()

    # Datos de prueba
    test_input = {
        "lead": {
            "id": "0efc403b-1706-415e-b50f-ecfa669e55ba",
            "name": "Debug Test Lead",
            "email": "debug.test6380@testcorp.com",
            "company": "TestCorp Debug",
            "message": "Test message for debugging workflow with automation interest and team scaling needs.",
        }
    }

    print("🔍 Testing qualifier with lead:")
    print(f"   - ID: {test_input['lead']['id']}")
    print(f"   - Name: {test_input['lead']['name']}")
    print(f"   - Email: {test_input['lead']['email']}")

    # Ejecutar qualifier
    try:
        result = await qualifier.run(test_input)

        print("\n📊 QUALIFIER RESULT:")
        print("=" * 40)
        for key, value in result.items():
            print(f"{key}: {value}")
        print("=" * 40)

        # Análisis
        print(f"\n🔍 ANALYSIS:")
        print(f"   - Qualified: {result.get('qualified', 'unknown')}")
        print(f"   - Reason: {result.get('reason', 'N/A')}")
        print(f"   - Database Updated: {result.get('database_updated', False)}")
        print(f"   - Lead ID: {result.get('lead_id', 'unknown')}")

        return result

    except Exception as e:
        print(f"\n❌ QUALIFIER ERROR: {e}")
        import traceback

        print(f"❌ TRACEBACK: {traceback.format_exc()}")
        return {"error": str(e)}


if __name__ == "__main__":
    # Ejecutar test
    result = asyncio.run(test_qualifier_directly())
