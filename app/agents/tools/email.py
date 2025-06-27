"""
Email tools module - Dummy implementation for MCP migration
All email functionality now handled via MCP integrations
"""


def get_email_client():
    """Dummy email client for backward compatibility"""

    class DummyEmailClient:
        def send_email(self, to_email, subject, content, content_type="html"):
            return {"success": True, "message_id": "dummy_message_id"}

        def send_template_email(self, to_email, template_name, variables):
            return {"success": True, "message_id": "dummy_template_message_id"}

    return DummyEmailClient()
