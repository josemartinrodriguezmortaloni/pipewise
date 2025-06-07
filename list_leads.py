#!/usr/bin/env python3
"""
List recent leads and their status
"""

from app.supabase.supabase_client import SupabaseCRMClient


def list_recent_leads():
    """List recent leads and their workflow status"""
    client = SupabaseCRMClient()

    try:
        leads = client.list_leads()
        print(f"📊 Total leads in database: {len(leads)}")

        if leads:
            print("\n🔍 Recent leads (last 5):")
            for lead in leads[-5:]:
                print(f"   - ID: {lead.id}")
                print(f"     Name: {lead.name}")
                print(f"     Email: {lead.email}")
                print(f"     Company: {lead.company}")
                print(f"     Qualified: {lead.qualified}")
                print(f"     Meeting Scheduled: {lead.meeting_scheduled}")
                print(f"     Contacted: {lead.contacted}")
                print(f"     Status: {lead.status}")
                print(f"     Created: {lead.created_at}")
                if lead.metadata:
                    print(f"     Metadata: {lead.metadata}")
                print("     ---")
        else:
            print("   No leads found")

    except Exception as e:
        print(f"❌ Error listing leads: {e}")


if __name__ == "__main__":
    list_recent_leads()
