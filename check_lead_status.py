#!/usr/bin/env python3
"""
Check lead status after workflow execution
"""

from app.supabase.supabase_client import SupabaseCRMClient


def check_lead_status():
    """Check the status of the lead after workflow"""
    client = SupabaseCRMClient()

    # ID del lead que se procesó en la prueba anterior
    lead_id = "b56a4947-fd9a-4e90-8ac3-1011f3fc3c38"

    try:
        lead = client.get_lead(lead_id)

        if lead:
            print(f"📊 Lead Status Report for ID: {lead_id}")
            print(f"   - Name: {lead.name}")
            print(f"   - Email: {lead.email}")
            print(f"   - Company: {lead.company}")
            print(f"   - Status: {lead.status}")
            print(f"   - Qualified: {lead.qualified}")
            print(f"   - Meeting Scheduled: {lead.meeting_scheduled}")
            print(f"   - Contacted: {lead.contacted}")
            print(f"   - Created: {lead.created_at}")
            print(f"   - Updated: {lead.updated_at}")

            if lead.metadata:
                print(f"   - Metadata: {lead.metadata}")
            else:
                print(f"   - Metadata: None")

            # Análisis del estado
            print("\n🔍 Workflow Analysis:")
            if lead.qualified:
                print("   ✅ Lead was qualified")
                if lead.meeting_scheduled:
                    print("   ✅ Meeting was scheduled")
                else:
                    print("   ❌ Meeting was NOT scheduled")

                if lead.contacted:
                    print("   ✅ Lead was contacted")
                else:
                    print("   ❌ Lead was NOT contacted")
            else:
                print("   ❌ Lead was NOT qualified")

            # Determinar si el workflow se completó totalmente
            complete_workflow = (
                lead.qualified and lead.meeting_scheduled and lead.contacted
            )
            print(
                f"\n🎯 Complete Workflow: {'✅ YES' if complete_workflow else '❌ NO'}"
            )

        else:
            print(f"❌ Lead not found with ID: {lead_id}")

    except Exception as e:
        print(f"❌ Error checking lead status: {e}")


if __name__ == "__main__":
    check_lead_status()
