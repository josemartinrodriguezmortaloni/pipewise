#!/usr/bin/env python3
"""
Diagnostic script for RLS policies on user_accounts table
"""

import os
import asyncio
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()


async def test_rls_policies():
    """Test RLS policies on user_accounts table"""

    print("🔍 Testing RLS policies for user_accounts table...")

    try:
        # Get environment variables
        supabase_url = os.getenv("SUPABASE_URL")
        anon_key = os.getenv("SUPABASE_ANON_KEY")
        service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not all([supabase_url, anon_key, service_key]):
            print("❌ Missing environment variables")
            return

        # Create clients - we already checked that these are not None
        admin_client = create_client(supabase_url, service_key)  # type: ignore
        regular_client = create_client(supabase_url, anon_key)  # type: ignore

        print("✅ Clients created successfully")

        # Test data
        test_user_id = "test-user-123"
        test_service = "google_calendar"

        # Test account data
        account_data = {
            "user_id": test_user_id,
            "service": test_service,
            "account_data": {"test": "data"},
            "connected": True,
            "connected_at": "2025-01-01T00:00:00.000Z",
            "profile_data": {"name": "Test User"},
        }

        print(f"\n🧪 Testing with data: {account_data}")

        # Test 1: Try with admin client (should work)
        print("\n📝 Test 1: Insert with admin client")
        try:
            result = (
                admin_client.table("user_accounts")
                .upsert(account_data, on_conflict="user_id,service")
                .execute()
            )

            if result.data:
                print(f"✅ Admin insert successful: {len(result.data)} records")
                print(f"   Data: {result.data[0]}")
            else:
                print("❌ Admin insert failed: No data returned")

        except Exception as e:
            print(f"❌ Admin insert failed: {e}")

        # Test 2: Try with regular client (likely to fail)
        print("\n📝 Test 2: Insert with regular client")
        try:
            result = (
                regular_client.table("user_accounts")
                .upsert(account_data, on_conflict="user_id,service")
                .execute()
            )

            if result.data:
                print(f"✅ Regular insert successful: {len(result.data)} records")
            else:
                print("❌ Regular insert failed: No data returned")

        except Exception as e:
            print(f"❌ Regular insert failed: {e}")

        # Test 3: Check table structure
        print("\n📝 Test 3: Check table structure")
        try:
            result = admin_client.table("user_accounts").select("*").limit(1).execute()
            print(f"✅ Table accessible. Sample data: {result.data}")

        except Exception as e:
            print(f"❌ Table not accessible: {e}")

        # Test 4: Environment variables check
        print("\n📝 Test 4: Environment variables")
        env_vars = {
            "SUPABASE_URL": supabase_url,
            "SUPABASE_ANON_KEY": anon_key,
            "SUPABASE_SERVICE_ROLE_KEY": service_key,
        }

        for key, value in env_vars.items():
            if value:
                print(f"✅ {key}: {'*' * 10}...{value[-4:]}")
            else:
                print(f"❌ {key}: Not set")

        # Clean up - remove test data
        print("\n🧹 Cleaning up test data")
        try:
            admin_client.table("user_accounts").delete().eq(
                "user_id", test_user_id
            ).execute()
            print("✅ Test data cleaned up")
        except Exception as e:
            print(f"⚠️ Could not clean up: {e}")

    except Exception as e:
        print(f"❌ Fatal error: {e}")


if __name__ == "__main__":
    asyncio.run(test_rls_policies())
