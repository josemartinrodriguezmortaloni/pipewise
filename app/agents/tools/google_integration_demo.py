"""
Google Integration Demo for PipeWise Agents

Demonstrates how agents can use Google Calendar and Gmail tools.
"""

import asyncio
import logging
from typing import Dict, Any
from datetime import datetime, timedelta

from .google_calendar import GoogleCalendarMCPServer
from .gmail import GmailMCPServer

logger = logging.getLogger(__name__)


class GoogleIntegrationDemo:
    """
    Demo class showing how agents can use Google Calendar and Gmail tools
    for lead qualification and meeting scheduling workflow.
    """

    def __init__(self, access_token: str):
        """Initialize with Google OAuth access token."""
        self.access_token = access_token
        self.calendar_server = GoogleCalendarMCPServer(access_token)
        self.gmail_server = GmailMCPServer(access_token)

    async def demo_lead_qualification_workflow(self) -> Dict[str, Any]:
        """
        Demonstrate a complete lead qualification workflow using Google tools.

        Workflow:
        1. Check for new emails from potential leads
        2. Parse lead information
        3. Send qualification email
        4. Check calendar availability
        5. Create meeting if qualified
        6. Send meeting invitation
        """
        try:
            logger.info("🚀 Starting lead qualification workflow demo")

            # Step 1: Check for new emails from leads
            logger.info("📧 Step 1: Checking for new lead emails")
            lead_emails = await self.gmail_server.search_emails(
                query="is:unread subject:inquiry OR subject:interest OR subject:demo",
                max_results=5,
            )

            if not lead_emails.get("success"):
                return {"success": False, "error": "Failed to fetch lead emails"}

            logger.info(f"Found {lead_emails['count']} potential lead emails")

            # Step 2: Process each lead email
            qualified_leads = []
            for email in lead_emails.get("messages", []):
                logger.info(f"📋 Processing email from: {email.get('from', '')}")

                # Simple lead qualification logic
                if self._is_qualified_lead(email):
                    qualified_leads.append(email)
                    logger.info(f"✅ Qualified lead: {email.get('from', '')}")
                else:
                    logger.info(f"❌ Not qualified: {email.get('from', '')}")

            # Step 3: Send qualification emails and schedule meetings
            scheduled_meetings = []
            for lead in qualified_leads:
                meeting_result = await self._schedule_meeting_for_lead(lead)
                if meeting_result.get("success"):
                    scheduled_meetings.append(meeting_result)

            return {
                "success": True,
                "total_emails_checked": lead_emails["count"],
                "qualified_leads": len(qualified_leads),
                "meetings_scheduled": len(scheduled_meetings),
                "meetings": scheduled_meetings,
            }

        except Exception as e:
            logger.error(f"Error in lead qualification workflow: {e}")
            return {"success": False, "error": str(e)}

    def _is_qualified_lead(self, email: Dict[str, Any]) -> bool:
        """
        Simple lead qualification logic based on email content.

        In a real implementation, this would use AI/ML to analyze:
        - Company size
        - Industry
        - Budget indicators
        - Pain points
        - Decision-making authority
        """
        body = email.get("body", "").lower()
        subject = email.get("subject", "").lower()

        # Qualification criteria
        qualification_keywords = [
            "budget",
            "decision maker",
            "enterprise",
            "company",
            "team",
            "solution",
            "implementation",
            "ROI",
        ]

        disqualification_keywords = ["student", "personal", "homework", "free", "trial"]

        # Check for qualification keywords
        qualified_score = sum(
            1
            for keyword in qualification_keywords
            if keyword in body or keyword in subject
        )

        # Check for disqualification keywords
        disqualified_score = sum(
            1
            for keyword in disqualification_keywords
            if keyword in body or keyword in subject
        )

        return qualified_score >= 2 and disqualified_score == 0

    async def _schedule_meeting_for_lead(
        self, lead_email: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Schedule a meeting for a qualified lead.

        Process:
        1. Check calendar availability
        2. Create calendar event
        3. Send meeting invitation email
        """
        try:
            lead_email_address = lead_email.get("from", "")
            lead_name = lead_email_address.split("@")[0].replace(".", " ").title()

            logger.info(f"📅 Scheduling meeting for {lead_name}")

            # Step 1: Find available time slot (next business day, 2 PM)
            tomorrow = datetime.now() + timedelta(days=1)
            # Set to 2 PM tomorrow
            meeting_start = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)
            meeting_end = meeting_start + timedelta(hours=1)

            # Check availability
            availability = await self.calendar_server.check_availability(
                start_time=meeting_start.isoformat(), end_time=meeting_end.isoformat()
            )

            if not availability.get("success"):
                return {
                    "success": False,
                    "error": "Failed to check calendar availability",
                }

            if not availability.get("is_available"):
                # Try next day if tomorrow is busy
                meeting_start = meeting_start + timedelta(days=1)
                meeting_end = meeting_end + timedelta(days=1)
                logger.info("📅 Tomorrow is busy, trying next day")

            # Step 2: Create calendar event
            event_title = f"Lead Qualification Call - {lead_name}"
            event_description = f"""
Lead Qualification Call

Lead Details:
- Email: {lead_email_address}
- Original Subject: {lead_email.get("subject", "")}
- Source: Email inquiry

Meeting Agenda:
- Understand business needs
- Assess fit for PipeWise solution
- Discuss next steps

Meeting generated automatically by PipeWise AI Agent.
            """.strip()

            calendar_event = await self.calendar_server.create_event(
                title=event_title,
                description=event_description,
                start_time=meeting_start.isoformat(),
                end_time=meeting_end.isoformat(),
                attendees=[lead_email_address],
                location="Google Meet (link will be generated automatically)",
            )

            if not calendar_event.get("success"):
                return {"success": False, "error": "Failed to create calendar event"}

            # Step 3: Send meeting invitation email
            invitation_email = await self._send_meeting_invitation(
                lead_email_address,
                lead_name,
                meeting_start,
                calendar_event.get("html_link", ""),
            )

            if not invitation_email.get("success"):
                return {"success": False, "error": "Failed to send meeting invitation"}

            # Step 4: Reply to original email
            await self.gmail_server.reply_to_message(
                message_id=lead_email.get("id", ""),
                reply_body=f"""
Hi {lead_name},

Thank you for your inquiry about PipeWise! I'm excited to learn more about your business needs.

I've scheduled a brief 30-minute call for us to discuss how PipeWise can help streamline your lead qualification process. You should receive a calendar invitation shortly.

Meeting Details:
- Date: {meeting_start.strftime("%A, %B %d, %Y")}
- Time: {meeting_start.strftime("%I:%M %p")}
- Duration: 30 minutes

If this time doesn't work for you, please let me know and we can find a better slot.

Looking forward to our conversation!

Best regards,
PipeWise AI Assistant
                """.strip(),
            )

            return {
                "success": True,
                "lead_email": lead_email_address,
                "lead_name": lead_name,
                "meeting_time": meeting_start.isoformat(),
                "calendar_event_id": calendar_event.get("event_id", ""),
                "calendar_link": calendar_event.get("html_link", ""),
            }

        except Exception as e:
            logger.error(f"Error scheduling meeting for lead: {e}")
            return {"success": False, "error": str(e)}

    async def _send_meeting_invitation(
        self,
        lead_email: str,
        lead_name: str,
        meeting_time: datetime,
        calendar_link: str,
    ) -> Dict[str, Any]:
        """Send a professional meeting invitation email."""

        invitation_body = f"""
Hi {lead_name},

I hope this email finds you well. Thank you for your interest in PipeWise!

I've scheduled a brief 30-minute consultation call to discuss your lead qualification needs and explore how PipeWise can help streamline your sales process.

📅 Meeting Details:
• Date: {meeting_time.strftime("%A, %B %d, %Y")}
• Time: {meeting_time.strftime("%I:%M %p")}
• Duration: 30 minutes
• Location: Google Meet (link in calendar invitation)

During our call, we'll cover:
✓ Your current lead qualification process
✓ Key challenges you're facing
✓ How PipeWise can automate and improve your workflow
✓ Next steps for implementation

Please accept the calendar invitation you'll receive shortly. If you need to reschedule, just let me know!

Best regards,
PipeWise AI Assistant

P.S. This meeting was automatically scheduled by our AI system after analyzing your inquiry. Pretty cool, right? 😊
        """.strip()

        return await self.gmail_server.send_email(
            to=lead_email,
            subject=f"Meeting Scheduled - PipeWise Consultation ({meeting_time.strftime('%m/%d at %I:%M %p')})",
            body=invitation_body,
        )

    async def demo_calendar_features(self) -> Dict[str, Any]:
        """Demonstrate Google Calendar features."""
        try:
            logger.info("📅 Demonstrating Google Calendar features")

            # List calendars
            calendars = await self.calendar_server.list_calendars()
            logger.info(f"Found {calendars.get('count', 0)} calendars")

            # Get upcoming events
            upcoming_events = await self.calendar_server.get_upcoming_events(
                max_results=5
            )
            logger.info(f"Found {upcoming_events.get('count', 0)} upcoming events")

            # Check availability for next hour
            now = datetime.now()
            next_hour = now + timedelta(hours=1)
            availability = await self.calendar_server.check_availability(
                start_time=now.isoformat(), end_time=next_hour.isoformat()
            )

            return {
                "success": True,
                "calendars": calendars.get("count", 0),
                "upcoming_events": upcoming_events.get("count", 0),
                "next_hour_available": availability.get("is_available", False),
                "calendar_details": calendars.get("calendars", [])[
                    :3
                ],  # First 3 calendars
                "event_details": upcoming_events.get("events", [])[
                    :3
                ],  # First 3 events
            }

        except Exception as e:
            logger.error(f"Error demonstrating calendar features: {e}")
            return {"success": False, "error": str(e)}

    async def demo_gmail_features(self) -> Dict[str, Any]:
        """Demonstrate Gmail features."""
        try:
            logger.info("📧 Demonstrating Gmail features")

            # Get recent emails
            recent_emails = await self.gmail_server.get_messages(max_results=5)
            logger.info(f"Found {recent_emails.get('count', 0)} recent emails")

            # Search for specific emails
            business_emails = await self.gmail_server.search_emails(
                query="category:primary -category:social -category:promotions",
                max_results=3,
            )

            # Get Gmail labels
            labels = await self.gmail_server.get_labels()
            logger.info(f"Found {labels.get('count', 0)} Gmail labels")

            return {
                "success": True,
                "recent_emails": recent_emails.get("count", 0),
                "business_emails": business_emails.get("count", 0),
                "labels": labels.get("count", 0),
                "email_samples": [
                    {
                        "subject": email.get("subject", "")[:50] + "...",
                        "from": email.get("from", "")[:30] + "...",
                        "date": email.get("date", ""),
                    }
                    for email in recent_emails.get("messages", [])[:3]
                ],
            }

        except Exception as e:
            logger.error(f"Error demonstrating Gmail features: {e}")
            return {"success": False, "error": str(e)}


async def run_demo(access_token: str):
    """Run a simple demo of Google integrations."""
    print("🚀 Starting Google Integration Demo for PipeWise Agents")
    print("=" * 60)

    # Initialize servers
    calendar_server = GoogleCalendarMCPServer(access_token)
    gmail_server = GmailMCPServer(access_token)

    # Test Calendar
    print("\n📅 Testing Google Calendar:")
    calendars = await calendar_server.list_calendars()
    if calendars.get("success"):
        print(f"✅ Found {calendars['count']} calendars")
    else:
        print(f"❌ Calendar test failed: {calendars.get('error', 'Unknown error')}")

    # Test Gmail
    print("\n📧 Testing Gmail:")
    emails = await gmail_server.get_messages(max_results=3)
    if emails.get("success"):
        print(f"✅ Found {emails['count']} recent emails")
    else:
        print(f"❌ Gmail test failed: {emails.get('error', 'Unknown error')}")

    print("\n�� Demo Complete!")


if __name__ == "__main__":
    access_token = "your_google_oauth_access_token_here"
    asyncio.run(run_demo(access_token))
