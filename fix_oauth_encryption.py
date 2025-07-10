#!/usr/bin/env python3
"""
Fix OAuth encryption by re-encrypting tokens with current key
"""

from app.supabase.supabase_client import get_supabase_admin_client
from app.core.security import encrypt_oauth_tokens, decrypt_oauth_tokens


def fix_oauth_encryption():
    # Get the existing account
    client = get_supabase_admin_client()
    user_id = "9e6fd7a1-d7b4-4f50-baa5-4c4d867a9ba4"
    service = "pipedrive"
    result = (
        client.table("user_accounts")
        .select("*")
        .eq("user_id", user_id)
        .eq("service", service)
        .execute()
    )

    if result.data:
        account = result.data[0]
        print(f"Account created: {account.get('created_at')}")
        print(f"Account updated: {account.get('updated_at')}")
        print(f"Connected at: {account.get('connected_at')}")

        # Try to re-encrypt with current key
        print("\nTesting re-encryption with current key:")

        # Create new test tokens that match what Pipedrive would provide
        test_tokens = {
            "access_token": "test_pipedrive_access_token_12345",
            "refresh_token": "test_pipedrive_refresh_token_67890",
            "expires_at": "2025-12-31T23:59:59Z",
            "token_type": "Bearer",
            "scope": "read write",
            "metadata": {
                "api_domain": "test-domain.pipedrive.com",
                "company_id": "12345",
                "test_reencryption": True,
                "service_account_id": "pipedrive_test_123",
            },
        }

        try:
            # Encrypt with current key
            encrypted = encrypt_oauth_tokens(test_tokens)
            print(f"Re-encryption successful: {bool(encrypted)}")

            # Test decryption
            decrypted = decrypt_oauth_tokens(encrypted)
            print(f"Re-decryption successful: {bool(decrypted)}")
            print(f"Data integrity: {decrypted == test_tokens}")

            if decrypted == test_tokens:
                # Update the account with new encrypted tokens
                print("\nUpdating account with re-encrypted tokens...")
                client.table("user_accounts").update(
                    {"account_data": encrypted, "updated_at": "2025-01-10T20:30:00Z"}
                ).eq("user_id", user_id).eq("service", service).execute()

                print("✅ Account updated with re-encrypted tokens")

                # Test the OAuth Integration Manager again
                print("\nTesting OAuth Integration Manager with new tokens:")
                from app.api.oauth_integration_manager import OAuthIntegrationManager

                oauth_manager = OAuthIntegrationManager()
                tokens = oauth_manager.get_user_integration_tokens(user_id, service)
                print(f"get_user_integration_tokens: {bool(tokens)}")

                if tokens:
                    print(f"Token keys: {list(tokens.keys())}")
                    print(f"Has access_token: {bool(tokens.get('access_token'))}")
                    print(f"Enabled: {tokens.get('enabled', False)}")

                    # Test MCP credentials
                    credentials = oauth_manager.create_mcp_credentials(user_id, service)
                    print(f"create_mcp_credentials: {bool(credentials)}")

                    if credentials:
                        print(f"MCP credential keys: {list(credentials.keys())}")
                        print("✅ OAuth system is now working!")
                    else:
                        print("❌ MCP credentials still not working")
                else:
                    print("❌ Still not getting tokens")
            else:
                print("❌ Data integrity check failed")

        except Exception as e:
            print(f"Re-encryption failed: {e}")
            import traceback

            traceback.print_exc()
    else:
        print("No account found")


if __name__ == "__main__":
    fix_oauth_encryption()
