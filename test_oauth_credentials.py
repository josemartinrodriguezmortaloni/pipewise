#!/usr/bin/env python3
"""
Test OAuth Credentials

Quick check to see which OAuth integrations are properly configured.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def check_oauth_credentials():
    """Check which OAuth services have credentials configured"""

    services = {
        "Google Calendar": ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"),
        "Calendly": ("CALENDLY_CLIENT_ID", "CALENDLY_CLIENT_SECRET"),
        "Pipedrive": ("PIPEDRIVE_CLIENT_ID", "PIPEDRIVE_CLIENT_SECRET"),
        "Salesforce": ("SALESFORCE_CLIENT_ID", "SALESFORCE_CLIENT_SECRET"),
        "Zoho CRM": ("ZOHO_CRM_CLIENT_ID", "ZOHO_CRM_CLIENT_SECRET"),
        "Twitter": ("TWITTER_CLIENT_ID", "TWITTER_CLIENT_SECRET"),
        "Instagram": ("INSTAGRAM_CLIENT_ID", "INSTAGRAM_CLIENT_SECRET"),
        "SendGrid": ("SENDGRID_CLIENT_ID", "SENDGRID_CLIENT_SECRET"),
    }

    print("🔍 Checking OAuth Credentials...")
    print("=" * 50)

    configured = []
    missing = []

    for service, (client_id_var, client_secret_var) in services.items():
        client_id = os.getenv(client_id_var, "").strip()
        client_secret = os.getenv(client_secret_var, "").strip()

        if client_id and client_secret:
            print(f"✅ {service}: Configured")
            configured.append(service)
        else:
            print(f"❌ {service}: Missing credentials")
            missing.append(service)

    print("=" * 50)
    print(f"✅ Configured: {len(configured)} services")
    print(f"❌ Missing: {len(missing)} services")

    if missing:
        print("\n🚨 To configure missing services:")
        print("1. Copy env.example to .env if you haven't")
        print("2. Get OAuth credentials from each provider")
        print("3. Add them to your .env file")
        print("\nServices still needing setup:")
        for service in missing:
            print(f"   - {service}")

    if configured:
        print(f"\n🎉 Ready to use: {', '.join(configured)}")

    return len(configured) > 0


if __name__ == "__main__":
    check_oauth_credentials()
