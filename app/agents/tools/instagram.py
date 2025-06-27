"""
Instagram tools module - Dummy implementation for MCP migration
All Instagram functionality now handled via MCP integrations
"""


def get_instagram_client():
    """Dummy Instagram client for backward compatibility"""

    class DummyInstagramClient:
        def send_dm(self, user_id, message):
            return {"success": True, "message_id": "dummy_ig_message_id"}

        def get_user_info(self, username):
            return {"success": True, "user_id": "dummy_user_id", "username": username}

    return DummyInstagramClient()
