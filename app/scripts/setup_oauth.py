#!/usr/bin/env python3
"""
OAuth Setup Script for PipeWise

This script helps you set up OAuth integrations by:
1. Generating encryption keys
2. Validating OAuth configuration
3. Testing encryption/decryption
4. Checking database connectivity
"""

import os
import sys
import json
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from cryptography.fernet import Fernet
except ImportError:
    print("❌ cryptography package not installed. Run: uv add cryptography")
    sys.exit(1)


def generate_encryption_key():
    """Generate a new Fernet encryption key"""
    return Fernet.generate_key().decode()


def generate_encryption_salt():
    """Generate a random salt for key derivation"""
    import secrets

    return secrets.token_urlsafe(32)


def create_env_template():
    """Create a .env template file with OAuth variables"""

    encryption_key = generate_encryption_key()
    encryption_salt = generate_encryption_salt()

    template = f"""# OAuth Configuration for PipeWise
# Generated on {os.popen("date").read().strip()}

# ==============================================
# OAUTH BASE CONFIGURATION
# ==============================================

# Base URL for OAuth callbacks (change to your domain in production)
OAUTH_BASE_URL=http://localhost:8000

# Encryption keys for storing OAuth tokens securely
ENCRYPTION_KEY={encryption_key}
ENCRYPTION_SALT={encryption_salt}

# ==============================================
# CALENDLY OAUTH
# ==============================================

# Get these from: https://developer.calendly.com/
CALENDLY_CLIENT_ID=your_calendly_client_id
CALENDLY_CLIENT_SECRET=your_calendly_client_secret

# ==============================================
# GOOGLE CALENDAR OAUTH
# ==============================================

# Get these from: https://console.cloud.google.com/
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# ==============================================
# PIPEDRIVE OAUTH
# ==============================================

# Get these from: https://developers.pipedrive.com/
PIPEDRIVE_CLIENT_ID=your_pipedrive_client_id
PIPEDRIVE_CLIENT_SECRET=your_pipedrive_client_secret

# ==============================================
# SALESFORCE OAUTH
# ==============================================

# Get these from Salesforce Connected App
SALESFORCE_CLIENT_ID=your_salesforce_client_id
SALESFORCE_CLIENT_SECRET=your_salesforce_client_secret

# ==============================================
# ZOHO CRM OAUTH
# ==============================================

# Get these from: https://api-console.zoho.com/
ZOHO_CLIENT_ID=your_zoho_client_id
ZOHO_CLIENT_SECRET=your_zoho_client_secret

# ==============================================
# TWITTER / X OAUTH
# ==============================================

# Get these from: https://developer.twitter.com/
TWITTER_CLIENT_ID=your_twitter_client_id
TWITTER_CLIENT_SECRET=your_twitter_client_secret
"""

    env_file = project_root / ".env.oauth"

    # Check if file already exists
    if env_file.exists():
        response = input(f"⚠️  {env_file} already exists. Overwrite? (y/N): ")
        if response.lower() != "y":
            print("❌ Cancelled")
            return False

    with open(env_file, "w") as f:
        f.write(template)

    print(f"✅ Created {env_file}")
    print(f"🔑 Generated encryption key: {encryption_key}")
    print(f"🧂 Generated encryption salt: {encryption_salt}")
    print()
    print("📝 Next steps:")
    print("1. Copy .env.oauth to .env")
    print("2. Fill in your OAuth credentials")
    print("3. Run this script again with --validate to test configuration")

    return True


def test_encryption():
    """Test encryption/decryption functionality"""
    print("🔐 Testing encryption...")

    try:
        from app.core.security import encrypt_oauth_tokens, decrypt_oauth_tokens

        # Test data
        test_tokens = {
            "access_token": "test_access_token_12345",
            "refresh_token": "test_refresh_token_67890",
            "expires_in": 3600,
            "scope": "read write",
        }

        # Test encryption
        encrypted = encrypt_oauth_tokens(test_tokens)
        print(f"  ✅ Encryption successful (length: {len(encrypted)})")

        # Test decryption
        decrypted = decrypt_oauth_tokens(encrypted)
        print(f"  ✅ Decryption successful")

        # Verify data integrity
        if decrypted == test_tokens:
            print("  ✅ Data integrity verified")
            return True
        else:
            print("  ❌ Data integrity check failed")
            print(f"    Original: {test_tokens}")
            print(f"    Decrypted: {decrypted}")
            return False

    except Exception as e:
        print(f"  ❌ Encryption test failed: {e}")
        return False


def validate_oauth_config():
    """Validate OAuth configuration for all services"""
    print("🔍 Validating OAuth configuration...")

    try:
        from app.core.oauth_config import get_oauth_config, build_redirect_uri

        services = [
            "calendly",
            "google_calendar",
            "pipedrive",
            "salesforce_rest_api",
            "zoho_crm",
            "twitter_account",
        ]

        configured_services = []
        missing_services = []

        for service in services:
            config = get_oauth_config(service)
            if config:
                redirect_uri = build_redirect_uri(service)
                print(f"  ✅ {service}")
                print(f"    Redirect URI: {redirect_uri}")
                configured_services.append(service)
            else:
                print(f"  ❌ {service} - Missing configuration")
                missing_services.append(service)

        print()
        print(
            f"📊 Summary: {len(configured_services)}/{len(services)} services configured"
        )

        if missing_services:
            print("⚠️  Missing services:")
            for service in missing_services:
                env_vars = [
                    f"{service.upper().replace('_', '_')}_CLIENT_ID",
                    f"{service.upper().replace('_', '_')}_CLIENT_SECRET",
                ]
                print(f"   - {service}: Need {', '.join(env_vars)}")

        return len(missing_services) == 0

    except Exception as e:
        print(f"  ❌ Configuration validation failed: {e}")
        return False


def check_database_connectivity():
    """Check if Supabase database is accessible"""
    print("🗄️  Testing database connectivity...")

    try:
        from app.supabase.supabase_client import get_supabase_client

        client = get_supabase_client()

        # Try to query the user_accounts table
        result = client.client.table("user_accounts").select("*").limit(1).execute()

        print("  ✅ Database connection successful")
        print(f"  📊 user_accounts table accessible")

        return True

    except Exception as e:
        print(f"  ❌ Database connection failed: {e}")
        print("  💡 Make sure Supabase credentials are configured")
        return False


def run_all_tests():
    """Run all validation tests"""
    print("🚀 Running OAuth setup validation...\n")

    tests = [
        ("Encryption", test_encryption),
        ("OAuth Config", validate_oauth_config),
        ("Database", check_database_connectivity),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"{'=' * 50}")
        print(f"Testing {test_name}")
        print(f"{'=' * 50}")

        if test_func():
            passed += 1
            print(f"✅ {test_name} test passed\n")
        else:
            print(f"❌ {test_name} test failed\n")

    print(f"{'=' * 50}")
    print(f"SUMMARY: {passed}/{total} tests passed")
    print(f"{'=' * 50}")

    if passed == total:
        print("🎉 All tests passed! OAuth integration is ready!")
    else:
        print("⚠️  Some tests failed. Check configuration and try again.")

    return passed == total


def main():
    """Main script function"""
    import argparse

    parser = argparse.ArgumentParser(description="OAuth Setup Script for PipeWise")
    parser.add_argument(
        "--generate-env", action="store_true", help="Generate .env.oauth template file"
    )
    parser.add_argument(
        "--validate", action="store_true", help="Validate OAuth configuration"
    )
    parser.add_argument(
        "--test-encryption", action="store_true", help="Test encryption functionality"
    )
    parser.add_argument(
        "--test-database", action="store_true", help="Test database connectivity"
    )
    parser.add_argument("--all", action="store_true", help="Run all validation tests")

    args = parser.parse_args()

    print("🔧 PipeWise OAuth Setup Script")
    print("=" * 50)

    if args.generate_env:
        create_env_template()
    elif args.test_encryption:
        test_encryption()
    elif args.test_database:
        check_database_connectivity()
    elif args.validate:
        validate_oauth_config()
    elif args.all:
        run_all_tests()
    else:
        # Interactive mode
        print("What would you like to do?")
        print("1. Generate .env template")
        print("2. Validate configuration")
        print("3. Test encryption")
        print("4. Test database")
        print("5. Run all tests")
        print("0. Exit")

        choice = input("\nEnter your choice (0-5): ").strip()

        if choice == "1":
            create_env_template()
        elif choice == "2":
            validate_oauth_config()
        elif choice == "3":
            test_encryption()
        elif choice == "4":
            check_database_connectivity()
        elif choice == "5":
            run_all_tests()
        elif choice == "0":
            print("👋 Goodbye!")
        else:
            print("❌ Invalid choice")


if __name__ == "__main__":
    main()
