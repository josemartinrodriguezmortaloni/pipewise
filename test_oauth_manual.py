#!/usr/bin/env python3
"""
Test OAuth Manual Flow

Generates an authorization URL to be used manually in the browser.
This helps bypass localhost restrictions during development.
"""

import os
import asyncio
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Asegurarse de que el path del proyecto esté en el sys.path
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.api.oauth_handler import OAuthHandler
from app.auth.middleware import get_current_user as auth_get_current_user


# Mock a user for testing purposes
class MockUser:
    def __init__(self, user_id):
        self.id = user_id


async def get_mock_user():
    """Mock user dependency"""
    return MockUser(user_id="test-user-123")


async def main():
    """Main function to generate authorization URL"""

    # 1. Choose the service to test
    service = "google_calendar"  # Cambia a 'twitter_account', 'calendly', etc.

    # 2. Mock user ID
    user_id = "test-user-123"

    # 3. Frontend redirect URL (opcional, pero recomendado)
    frontend_redirect = "http://localhost:3000/integrations"

    print(f"🔧 Generating OAuth URL for service: {service}")

    try:
        oauth_handler = OAuthHandler()

        # Generar URL de autorización
        auth_url = await oauth_handler.generate_authorization_url(
            service=service, user_id=user_id, redirect_url=frontend_redirect
        )

        print("\n✅ Authorization URL generated successfully!")
        print("-" * 50)
        print("ACTION REQUIRED:")
        print("1. Copy the URL below.")
        print("2. Paste it into your browser.")
        print("3. Authorize the application.")
        print(
            "4. You will be redirected back. If it shows an error, copy the URL from the browser's address bar."
        )
        print("5. Look for the 'code=' parameter in the redirected URL.")
        print("-" * 50)
        print("\nAuthorization URL:")
        print(auth_url)
        print("\n")

    except Exception as e:
        print(f"\n❌ Error generating URL: {e}")


if __name__ == "__main__":
    asyncio.run(main())
